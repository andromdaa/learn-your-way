# Systemic Cleanup — Active Initiative

One structural change remains to close a recurring defect class surfaced by the 2026-05-01 pipeline audit. Initiatives 1 and 2 (CI integration and typed worker-result protocol) have shipped as of 2026-05-01. Initiative 3 (chunker contract redefinition) remains open.

See `archive/` for the completed planning documents from Initiatives 1 and 2.

## Why this exists

| Closed by | What it fixed | What recurred |
|---|---|---|
| #66 → API | `dict(<exc>)` 500 turned into `status="failed"` envelope | #82/#83/#84 — pickle-deserialization layer never landed |
| #64 → fences | Strip ` ```json ` wrapper before `json.loads` | #77 — different silent-empty path (thin source, not bad JSON) |
| #76 → scaffolding | Deny-list + 120-char body floor | #75 (mid-word titles), #77 (thin-source flourishes) still escaped |
| #75 → titles | Word-boundary truncation | Body-fallback fired at all because chunker still emits chrome |
| #77 → guard | Raise `ReplaceSourceTooThinError` pre-flight | #82 — that very exception round-trips wrong through Arq pickle |

Each fix was narrowly scoped, each explicitly said so, and each held. Three structural changes would close the class — two have shipped, one remains.

## Active Initiative

| Initiative | File | Effort | Status |
|---|---|---|---|
| Chunker contract redefinition | [chunker-contract-redefinition.md](chunker-contract-redefinition.md) | Large (4+ PRs, multi-week) | Open |

## Sequencing (completed)

**Initiative 1 (CI integration coverage)** shipped in AND-32 (2026-05-01). The integration job in `.github/workflows/ci.yml` now runs end-to-end tests on every PR, catching chunker false-positives and worker-boundary exceptions before merge.

**Initiative 2 (typed worker-result protocol)** shipped in AND-33 (2026-05-01). Generators now return `Success | Failure` typed envelopes rather than raising across the worker→Redis→API boundary, eliminating pickle-bomb deserialization failures.

**Initiative 3 (chunker contract redefinition)** proceeds independently. The chunker redesign benefits from the CI infrastructure and typed-result foundation that Initiatives 1 and 2 provided.

## Whole-effort exclusions

- Phase 3 modality work (ships per `specs/phase-3-modalities.md`; this work is structural cleanup, not Phase 3 displacement).
- Web UI / CLI / docs touches.
- Immediate `__reduce__` point fixes for #82/#83/#84 (shipping in their own narrow PRs; Initiative 2 supersedes them structurally).

## Excluded point-fixes (file or fold separately — not tracked here)

- **Threshold drift** — `src/lyw_core/chunker/heuristic.py:36` defines `_MIN_BODY_CHARS = 120`; `src/lyw_core/personalization/replace.py:41` defines `_MIN_BODY_CHARS = 200`. Same name, different values, no shared constant — the chunker accepts a 120-char section the replacer immediately rejects. Point-fix or absorbed into Initiative 3 (the threshold should disappear in the redesign). Initiative 3's smoke test should catch a regression if deferred.
- **Empty-asset write** — `src/lyw_core/worker/jobs/personalize.py:181-183`: when `records` is empty, `"\n\n".join([])` produces `""` and the next line writes a 0-byte file. Fold into the #82 PR or file separately. Initiative 1's end-to-end smoke test should catch the regression (a 0-byte concept asset should fail the non-empty assertion).

## Initiative 3 note

Initiative 3 is independent of Phase 3 work. Per ADR-0016 (2026-05-01), Phase 3 modality generators are cancelled; the chunker redesign targets the core personalization flow (re-level and replace jobs) that remains in scope.

## Update — 2026-05-01: ADR-0016 scope cut and Initiative completion

[ADR-0016](../../../adr/0016-phase-2-3-scope-reduction.md) drops Phase 3
modality generators entirely and most of the Phase 2 assessment surface,
keeping only re-leveling, interest-based example replacement, and the
learner profile.

**Initiatives 1 and 2 have shipped** (AND-32 and AND-33, 2026-05-01):

- **Initiative 1 (CI integration coverage)** — Delivered as part of AND-32.
  The `pytest -m integration` job in `.github/workflows/ci.yml` now verifies
  end-to-end behavior on every PR, catching chunker false-positives and
  worker-boundary exceptions before merge. See `archive/ci-integration-coverage.md`.
- **Initiative 2 (typed worker-result protocol / `JobOutcome[T]`)** — Delivered
  as part of AND-33. The protocol covers `relevel` and `replace` job kinds
  (modality kinds were deleted with Phase 3). Generators return `Success | Failure`
  envelopes; see `archive/typed-worker-result-protocol.md` and ADR-0017.

**Initiative 3 (chunker contract redefinition)** — remains open and independent.
The chunker still feeds relevel and replace, and the `_MIN_BODY_CHARS` divergence
remains relevant.
