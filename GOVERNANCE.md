# OpsMind governance

This document describes how OpsMind is run: who decides what, how contributors
earn responsibility, and what a contributor can expect in return. It is
deliberately short — the project is small, so the governance should be too.

## Roles

### Maintainer

Currently: **[@Pawansingh3889](https://github.com/Pawansingh3889)**.

The maintainer is the final decision-maker on:

- merges to `main`
- releases and PyPI publishes (none today — OpsMind is a deployable app,
  not a PyPI package)
- granting the **triage collaborator** role
- changing this governance document

The maintainer commits to:

- replying to new issues and PRs within **7 calendar days**
- giving first-time contributors an explicit "go ahead" before they invest
  serious time
- merging PRs that pass CI and fit the project scope within **14 calendar
  days** of the last review comment being addressed

### Triage collaborator

A community member the maintainer has invited after a track record of
merged PRs. Today there are none; the first external contributor with
three merged, in-scope PRs is the natural candidate.

A triage collaborator can:

- apply and remove labels
- assign themselves or another contributor to an issue
- close duplicate, stale, or off-topic issues (with a polite comment)
- comment on PRs with informal reviews — the maintainer still does the
  final merge

A triage collaborator **cannot**:

- merge PRs
- force-push to `main`
- change repository settings or this document
- speak for the project in public statements (CFP proposals, security
  disclosures, licensing questions)

### Contributor

Anyone who opens an issue, comments on one, or submits a PR. No paperwork,
no gatekeeping — the default welcome is "please send a PR".

## Decisions

Small changes (docs, tests, single-file refactors, bug fixes) are decided
by one maintainer approval on the PR.

Larger changes — new modules, dependency additions, API shape changes,
deployment targets — start as an **issue with a proposal**, not a PR.
The proposal should cover:

1. the problem in one sentence
2. the change in bullet form
3. the alternatives considered
4. who benefits and who has to adapt

Discussion happens in the issue until the maintainer gives an explicit
"proceed to PR". This avoids the "big PR arrives, maintainer says no,
everyone loses a weekend" failure mode.

## Issue assignment (first-PR-wins)

OpsMind uses a **first-PR-wins soft-assignment policy**, borrowed from
drt (<https://github.com/drt-hub/drt>):

1. Commenting "I'd like to work on this" on an issue earns a soft claim.
2. The soft claim lasts **7 days**. If no PR is open by then, another
   contributor may take it.
3. If two contributors open PRs against the same issue, the **first PR to
   pass CI and request review** wins. The other is welcome to review and
   improve.
4. The maintainer will not hold a soft claim open indefinitely; a
   contributor who disappears for weeks doesn't block others.

Exceptions: if the first PR is clearly lower quality, the maintainer
may merge the second one instead. Quality is judged on test coverage,
docstrings, and scope discipline — not on code style preferences.

## Scope discipline

OpsMind's scope is "an AI query tool for manufacturing, running on the
user's machine". Four hard lines that won't move in this project:

- **No paid APIs.** Local Ollama only. Pull requests that add OpenAI,
  Anthropic, Gemini, or any other paid cloud inference will be closed,
  politely, with a pointer to fork.
- **No data leaves the machine by default.** Telemetry is opt-in via
  Sentry `SENTRY_DSN`; nothing else phones home.
- **Read-only to source databases.** The validator (`modules/sql_validator`)
  and the `SELECT`-only constraint in `run_query` are the project's
  trust story; any PR that weakens them needs a long conversation first.
- **No PII in the demo data.** Anonymised synthetic data only. See
  `CONTRIBUTING.md` for the checklist.

## Release cadence

OpsMind is deployed, not published. There are no release notes or PyPI
uploads today. When that changes:

- releases will follow **SemVer** starting at 0.x while the API shape
  is still moving
- breaking changes get one minor version of deprecation notice
- a `CHANGELOG.md` will be added before the first non-zero release

## Security

See `SECURITY.md` for how to report vulnerabilities. Security fixes get
priority over all other work.

## Changes to this document

Governance changes via PR from the maintainer, announced in the PR
description. Triage collaborators and contributors are welcome to
propose changes via issue — the maintainer makes the call.
