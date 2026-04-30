# ADR-0009 — PersonalizationProfile as a Pydantic model

## Status

Accepted (2026-04-30)

## Context

`DerivedAsset.personalization_profile` was a `dict[str, Any]` placeholder
added in phase 1 with a `TODO(phase-2)` comment. Phase 2 personalization
generators (re-leveling T5, example replacement T7) need to record every
change they make to source content so diffs remain auditable. The field
must carry structured replacement records, not an opaque dictionary.

`docs/02-data-model.md` mentioned "replace with a `TypedDict`" as the
intended approach. The spec (`specs/phase-2-personalization.md`) requires
a non-empty `justification` on every `ReplacementRecord`. A plain
`TypedDict` cannot enforce this invariant — it has no validator hooks.

## Decision

Replace `personalization_profile: dict[str, Any]` with
`personalization_profile: PersonalizationProfile` where:

- `PersonalizationProfile` is a Pydantic `BaseModel` with `grade_level:
  str`, `interests: list[str]`, and `replacements: list[ReplacementRecord]`.
- `ReplacementRecord` is a Pydantic `BaseModel` with `original_span:
  SourceSpan`, `replacement_text: str`, and `justification: str`.
  A `@field_validator` on `justification` rejects empty or
  whitespace-only strings.

The doc comment "replace with a TypedDict" is superseded by this ADR.

## Consequences

- Every personalization generator must construct a `PersonalizationProfile`
  instance; passing a raw dict is a type error caught at mypy time.
- Every replacement is auditable: the original span, new text, and
  reason are all stored together.
- `justification` is enforced non-empty at construction time, preventing
  silent audit gaps.
- Existing test fixtures that passed `personalization_profile={}` must
  be updated to use `PersonalizationProfile(grade_level=..., interests=[])`.

## Alternatives considered

**TypedDict**: Cannot enforce field invariants (e.g. non-empty justification).
Rejected because the spec explicitly requires the justification invariant.

**Plain dataclass**: No JSON round-trip support, no field validators.
Rejected in favour of Pydantic which is already the project's model layer.
