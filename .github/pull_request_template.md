<!--
Thanks for contributing to OpsMind! Fill out the sections below so the
maintainer doesn't have to ask. If your PR is a one-line docs fix, feel
free to delete sections that don't apply.
-->

## What changed

<!-- One or two sentences explaining the *why*, not just the *what*. -->

## Related issue

<!-- "Closes #123" or "Relates to #123". If there is no issue, say so and
     explain why the change is safe to land without one. -->

## How was this tested

- [ ] `make test` — unit + per-module tests pass locally
- [ ] `make eval-library` — library-path eval green (no LLM needed)
- [ ] `make lint` — ruff clean
- [ ] `make typecheck` or `make typecheck-ty`

## Contributor checklist

- [ ] One logical change per commit, conventional commit style (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `test:`, `style:`)
- [ ] Tests added or updated for any behaviour change
- [ ] `CHANGELOG.md` entry under `[Unreleased]` if user-facing
- [ ] Docstrings updated on any public function whose signature changed
- [ ] No real factory data, PII, or secrets in fixtures or screenshots

## Anything else reviewers should know

<!-- Known limitations, follow-up work you'd like to do, questions that
     need the maintainer's judgement before merge. -->
