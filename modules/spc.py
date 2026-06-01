"""Statistical process control (SPC) — control-chart logic for OpsMind.

This is the Six Sigma "Control" phase made concrete: instead of a single
fixed threshold ("alert if yield drops more than 5%"), each metric is
judged against *its own* historical variation. A process that normally
swings 8% week to week shouldn't fire on a 6% move; a rock-steady one
should fire on a 3% move. Control limits adapt to the process.

The classic individuals control chart:

    centre line (CL) = mean of the baseline window
    upper/lower control limits (UCL/LCL) = mean +/- 3 * sigma
    warning limits = mean +/- 2 * sigma

A point beyond +/-3 sigma is an *out-of-control* signal — a special
cause worth investigating. A point in the 2-3 sigma zone is an early
warning. Everything inside +/-2 sigma is normal common-cause variation
and should be left alone (over-reacting to noise is itself a defect,
the "tampering" Deming warned about).

Pure functions, no database or I/O — unit-testable in isolation. Uses
only the standard library.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Literal, Optional

# Minimum baseline points for a meaningful sigma estimate. Below this,
# the control limits are too unstable to trust — we report
# insufficient-data rather than a false signal.
MIN_BASELINE_POINTS = 8

Verdict = Literal["in_control", "warning", "out_of_control", "insufficient_data"]


@dataclass
class ControlResult:
    """Outcome of testing the latest value against its control limits."""

    verdict: Verdict
    value: float
    mean: float
    sigma: float
    ucl: float  # mean + 3*sigma
    lcl: float  # mean - 3*sigma
    # Signed distance of the value from the mean, in sigma units. Negative
    # = below mean. The headline number a human reads: "3.4 sigma below".
    sigma_distance: float
    # Which direction broke, if any — useful for "yield dropped" vs "spiked".
    direction: Optional[Literal["above", "below"]] = None

    @property
    def is_signal(self) -> bool:
        """True for warning or out_of_control — i.e. worth a human's look."""
        return self.verdict in ("warning", "out_of_control")


def control_limits(baseline: list[float]) -> tuple[float, float, float, float]:
    """Return (mean, sigma, ucl, lcl) for a baseline series.

    sigma is the sample standard deviation. Raises ValueError if the
    baseline is too short to estimate it.
    """
    if len(baseline) < 2:
        raise ValueError("Need at least 2 points to estimate sigma.")
    mean = statistics.fmean(baseline)
    sigma = statistics.stdev(baseline)
    return mean, sigma, mean + 3 * sigma, mean - 3 * sigma


def classify(value: float, baseline: list[float]) -> ControlResult:
    """Classify ``value`` against control limits derived from ``baseline``.

    ``baseline`` should be the recent history *excluding* the value being
    tested (e.g. the prior N weeks of yield, with ``value`` the latest
    week). Returns a ControlResult; verdict is ``insufficient_data`` when
    the baseline is too short or has zero variation.
    """
    if len(baseline) < MIN_BASELINE_POINTS:
        return ControlResult(
            verdict="insufficient_data",
            value=value,
            mean=statistics.fmean(baseline) if baseline else value,
            sigma=0.0,
            ucl=0.0,
            lcl=0.0,
            sigma_distance=0.0,
        )

    mean, sigma, ucl, lcl = control_limits(baseline)

    # Zero variance: every baseline point identical. Any deviation is, in
    # principle, infinitely many sigmas — but reporting inf is unhelpful.
    # Treat an exact match as in-control and any difference as a signal,
    # without dividing by zero.
    if sigma == 0.0:
        if value == mean:
            return ControlResult("in_control", value, mean, 0.0, ucl, lcl, 0.0)
        direction = "above" if value > mean else "below"
        return ControlResult(
            "out_of_control", value, mean, 0.0, ucl, lcl,
            sigma_distance=float("inf") if value > mean else float("-inf"),
            direction=direction,
        )

    sigma_distance = (value - mean) / sigma
    abs_dist = abs(sigma_distance)
    direction = "above" if sigma_distance > 0 else "below" if sigma_distance < 0 else None

    if abs_dist >= 3:
        verdict: Verdict = "out_of_control"
    elif abs_dist >= 2:
        verdict = "warning"
    else:
        verdict = "in_control"
        direction = None  # not a signal, direction is noise

    return ControlResult(
        verdict=verdict,
        value=value,
        mean=mean,
        sigma=sigma,
        ucl=ucl,
        lcl=lcl,
        sigma_distance=sigma_distance,
        direction=direction,
    )
