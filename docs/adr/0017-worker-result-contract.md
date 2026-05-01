# ADR-0017 — Worker Result Contract

## Status

Accepted (2026-05-01)

## Context

Arq serialises job results through pickle. Any exception whose `__init__`
signature differs from `BaseException.__init__(msg)` fails to reconstruct:
Arq calls `__init__(*self.args)` where `self.args` is the formatted string,
not the original positional arguments. The result is a `TypeError` wrapped
as `DeserializationError`, which FastAPI surfaces as a 500.

Issues #82, #83, #84 landed point-fixes (`__reduce__` overrides) for three
specific exceptions (`ValidationError`, `ReplaceSourceTooThinError`,
`OllamaError`). This is a perpetual leak: every new exception with a custom
`__init__` is a fresh opportunity to forget `__reduce__`.

## Decision

Workers must **never raise** domain exceptions across the Arq job boundary.
Every domain failure is returned as a `Failure` (see below); only unexpected
infrastructure exceptions (DB down, OOM, etc.) may propagate as exceptions
and surface via `info.success = False`.

Define a typed result envelope in `src/lyw_core/worker/result.py`:

```python
class Success(BaseModel, Generic[T]):
    status: Literal["success"] = "success"
    payload: T

class Failure(BaseModel):
    status: Literal["failure"] = "failure"
    code: str       # machine-readable slug: "thin_source", "ollama_error", …
    message: str    # human-readable summary
    details: dict[str, Any] = {}  # structured context
```

Pydantic models pickle cleanly without any `__reduce__` override.

The `personalize_concept` job catches `ReplaceSourceTooThinError`,
`OllamaError`, and `lyw_core.validators.base.ValidationError` at the
outermost try/except and converts each to the appropriate `Failure`.
Structural errors (lesson not found, concept not found, invalid kind,
profile not found) are also returned as `Failure`, so no exception of any
kind crosses the boundary.

The `GET /lessons/{id}/generate/{job_id}` endpoint reads `info.result` as
`Success | Failure` (discriminated on `status`). `Failure` maps to HTTP
`status="failed"`; `Success` maps to `status="complete"`. The `info.success
= False` path remains as a fallback for unexpected infrastructure errors.

The `__reduce__` overrides from AND-21, AND-22, AND-23 are decommissioned
now that the exceptions no longer cross the pickle boundary.

## Consequences

- No new generator exception needs a `__reduce__` override — the contract
  prohibits exceptions from crossing the boundary.
- The `code` field on `Failure` is the machine-readable failure reason;
  consumers can branch on it. Current codes: `invalid_kind`,
  `lesson_not_found`, `concept_not_found`, `profile_not_found`,
  `thin_source`, `ollama_error`, `validation_failed`.
- `Success[T]` is generic; the surviving `personalize_concept` job
  instantiates it as `Success[dict[str, Any]]` with `asset_id` and
  `file_path` keys.
- `details` on `Failure` carries structured context (char counts, reasons,
  HTTP status code) for logging and debugging; it is also forwarded to the
  API response so clients can surface structured error information.

## Alternatives considered

**Keep `__reduce__` on every custom exception**: Requires discipline at every
new exception definition. Works but is invisible and easily forgotten.
Rejected as a permanent solution; retained only as a bridge during the
migration.

**Return a plain `dict` with a `"status"` key**: Simpler but untyped.
Mypy cannot narrow on it; tests would check string keys rather than
attributes. Rejected in favour of Pydantic models.

**`run_validators` returns a result instead of raising**: Would eliminate
`ValidationError` entirely from the generator layer. Rejected (see
ADR-0011 amendment) — "raise internally, convert at the boundary" keeps
generators simple.
