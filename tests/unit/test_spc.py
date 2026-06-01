"""Tests for modules.spc — statistical process control / control charts.

Locks the control-chart contract: a point is only a signal when it
breaches its own historical variation, the warning/out-of-control zones
are the classic 2-sigma/3-sigma bands, and the degenerate cases
(too little data, zero variance) fail safe rather than raise or emit a
false signal.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from modules import spc  # noqa: E402

# A steady baseline: mean ~90, small spread. stdev ~1.6.
_STEADY = [90.0, 91.0, 89.0, 90.0, 92.0, 88.0, 90.0, 91.0, 89.0, 90.0]


# ---------------------------------------------------------------------------
# control_limits
# ---------------------------------------------------------------------------

class TestControlLimits:
    def test_returns_mean_sigma_and_3sigma_band(self) -> None:
        mean, sigma, ucl, lcl = spc.control_limits([10.0, 12.0, 14.0])
        assert mean == pytest.approx(12.0)
        assert sigma == pytest.approx(2.0)
        assert ucl == pytest.approx(18.0)  # 12 + 3*2
        assert lcl == pytest.approx(6.0)   # 12 - 3*2

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError):
            spc.control_limits([5.0])


# ---------------------------------------------------------------------------
# classify — the core decision
# ---------------------------------------------------------------------------

class TestClassify:
    def test_value_at_mean_is_in_control(self) -> None:
        r = spc.classify(90.0, _STEADY)
        assert r.verdict == "in_control"
        assert r.is_signal is False
        assert r.direction is None

    def test_small_wobble_within_2sigma_is_in_control(self) -> None:
        # ~1 sigma above the mean — normal common-cause variation.
        r = spc.classify(91.5, _STEADY)
        assert r.verdict == "in_control"

    def test_drop_beyond_3sigma_is_out_of_control(self) -> None:
        # mean ~90, sigma ~1.6 → 3-sigma LCL ~85. A yield of 80 is way out.
        r = spc.classify(80.0, _STEADY)
        assert r.verdict == "out_of_control"
        assert r.is_signal is True
        assert r.direction == "below"
        assert r.sigma_distance < -3

    def test_warning_zone_between_2_and_3_sigma(self) -> None:
        # Construct a baseline with mean 100, sigma exactly 2.
        baseline = [98.0, 102.0] * 5  # mean 100, stdev ~2.1
        mean, sigma, _, _ = spc.control_limits(baseline)
        # A value ~2.5 sigma above the mean lands in the warning band.
        value = mean + 2.5 * sigma
        r = spc.classify(value, baseline)
        assert r.verdict == "warning"
        assert r.is_signal is True
        assert r.direction == "above"

    def test_spike_above_is_flagged_above(self) -> None:
        r = spc.classify(100.0, _STEADY)
        assert r.verdict == "out_of_control"
        assert r.direction == "above"
        assert r.sigma_distance > 3


# ---------------------------------------------------------------------------
# Degenerate cases — fail safe, never raise or false-signal
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_insufficient_data_below_min_points(self) -> None:
        r = spc.classify(50.0, [90.0, 91.0, 89.0])  # only 3 < MIN_BASELINE_POINTS
        assert r.verdict == "insufficient_data"
        assert r.is_signal is False

    def test_empty_baseline_is_insufficient_not_crash(self) -> None:
        r = spc.classify(50.0, [])
        assert r.verdict == "insufficient_data"
        assert r.value == 50.0

    def test_zero_variance_exact_match_is_in_control(self) -> None:
        flat = [90.0] * 10
        r = spc.classify(90.0, flat)
        assert r.verdict == "in_control"

    def test_zero_variance_any_deviation_is_out_of_control(self) -> None:
        flat = [90.0] * 10
        r = spc.classify(89.0, flat)
        assert r.verdict == "out_of_control"
        assert r.direction == "below"

    def test_min_points_boundary_is_inclusive(self) -> None:
        # Exactly MIN_BASELINE_POINTS should be enough to classify.
        baseline = [90.0, 91.0, 89.0, 90.0, 92.0, 88.0, 90.0, 91.0]
        assert len(baseline) == spc.MIN_BASELINE_POINTS
        r = spc.classify(90.0, baseline)
        assert r.verdict != "insufficient_data"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
