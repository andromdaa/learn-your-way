# Systemic Cleanup — Initiative Index

Three structural changes address a recurring defect class surfaced by the 2026-05-01 pipeline audit. Every narrow fix shipped in the past held for the failure mode it addressed — but the *class* has not been engaged. This directory is the working surface for that engagement.

## Why this exists

| Closed by | What it fixed | What recurred |
|---|---|---|
| #66 → API | `dict(<exc>)` 500 turned into `status="failed"` envelope | #82/#83/#84 — pickle-deserialization layer never landed |
| #64 → fences | Strip ` ```json ` wrapper before `json.loads` | #77 — different silent-empty path (thin source, not bad JSON) |
| #76 → scaffolding | Deny-list + 120-char body floor | #75 (mid-word titles), #77 (thin-source flourishes) still escaped |
| #75 → titles | Word-boundary truncation | Body-fallback fired at all because chunker still emits chrome |
| #77 → guard | Raise `ReplaceSourceTooThinError` pre-flight | #82 — that very exception round-trips wrong through Arq pickle |

Each fix was narrowly scoped, each explicitly said so, and each held. Three structural changes would close the class.

## Initiatives

| Initiative | File | Effort |
|---|---|---|
| CI integration coverage | [ci-integration-coverage.md](ci-integration-coverage.md) | Small–medium (2 PRs, ~2 weeks) |
| Typed worker-result protocol | [typed-worker-result-protocol.md](typed-worker-result-protocol.md) | Medium (2–4 PRs, ~2 weeks) |
| Chunker contract redefinition | [chunker-contract-redefinition.md](chunker-contract-redefinition.md) | Large (4+ PRs, multi-week) |

## Recommended sequencing

**Initiative 1 first.** CI integration coverage is a force multiplier — once landed, every change in Initiatives 2 and 3 is verified end-to-end before merge, eliminating the by-hand-on-a-real-chapter feedback loop that is the root cause of the recurrence cycle. Smallest and most reversible.

**Then Initiative 2**, because it unblocks Phase 3 generators from re-introducing the same pickle-bomb exception class. It touches the same files Phase 3 generators are landing in; earlier is better.

**Initiative 3 last.** Largest, most likely to compete with Phase 3 work, most deserving of the safety net the others provide.

## Whole-effort exclusions

- Phase 3 modality work (ships per `specs/phase-3-modalities.md`; this work is structural cleanup, not Phase 3 displacement).
- Web UI / CLI / docs touches.
- Immediate `__reduce__` point fixes for #82/#83/#84 (shipping in their own narrow PRs; Initiative 2 supersedes them structurally).

## Excluded point-fixes (file or fold separately — not tracked here)

- **Threshold drift** — `src/lyw_core/chunker/heuristic.py:36` defines `_MIN_BODY_CHARS = 120`; `src/lyw_core/personalization/replace.py:41` defines `_MIN_BODY_CHARS = 200`. Same name, different values, no shared constant — the chunker accepts a 120-char section the replacer immediately rejects. Point-fix or absorbed into Initiative 3 (the threshold should disappear in the redesign). Initiative 3's smoke test should catch a regression if deferred.
- **Empty-asset write** — `src/lyw_core/worker/jobs/personalize.py:181-183`: when `records` is empty, `"\n\n".join([])` produces `""` and the next line writes a 0-byte file. Fold into the #82 PR or file separately. Initiative 1's end-to-end smoke test should catch the regression (a 0-byte concept asset should fail the non-empty assertion).

## Cross-cutting open question

**Phase 3 sequencing: interrupt it, run in parallel, or wait until Phase 3 closes?** Initiative 2 in particular touches the same files Phase 3 generators are being added to. Recommendation: run Initiative 1 in parallel with Phase 3 (CI wiring is additive, non-conflicting), then land Initiative 2 between Phase 3 task batches where branch divergence is smallest.

## Update — 2026-05-01: ADR-0016 scope cut

[ADR-0016](../../../adr/0016-phase-2-3-scope-reduction.md) drops Phase 3
modality generators entirely and most of the Phase 2 assessment surface,
keeping only re-leveling, interest-based example replacement, and the
learner profile. Several recurrence sites tracked here — slides direct
raises, modality validators, mind-map / timeline call sites, and the
`MCQGenerator` batch-with-discards pattern — are being **deleted** in
strip-in-place steps 2 and 3 rather than fixed structurally.

Effect on the initiatives:

- **Initiative 1 (CI integration coverage)** — priority unchanged. Lands
  on the trimmed surface in step 4 of the strip-in-place sequence; smaller
  surface means fewer integration scenarios to wire up, but the rationale
  (force-multiplier, pre-merge end-to-end verification) is unchanged.
- **Initiative 2 (typed worker-result protocol / `JobOutcome[T]`)** —
  scope shrinks. The protocol now only needs to cover the `relevel` and
  `replace` job kinds; modality kinds are gone. Lands as step 5 of the
  strip-in-place sequence. The cross-cutting Phase 3 sequencing question
  above is resolved: there is no Phase 3 to coordinate with.
- **Initiative 3 (chunker contract redefinition)** — priority unchanged.
  The chunker still feeds relevel and replace, and the
  `_MIN_BODY_CHARS` divergence point-fix flagged below remains relevant.
