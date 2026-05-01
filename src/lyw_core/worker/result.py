"""Typed worker result envelope for the Arq job boundary.

Workers return Success | Failure instead of raising exceptions across the
pickle boundary. The job catches domain exceptions at its outermost try/except
block and converts them into Failure before returning. The API route reads
info.result as a discriminated union on the ``status`` field.

Pydantic models pickle cleanly; this eliminates the class of defects where
a custom __init__ signature differed from the base Exception's positional
args, causing Arq's reconstructor to raise TypeError on deserialise.

See docs/adr/0011-validator-framework.md (amendment) and
docs/adr/0017-worker-result-contract.md.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Success[T](BaseModel):
    """Worker job completed successfully; payload carries the result."""

    status: Literal["success"] = "success"
    payload: T


class Failure(BaseModel):
    """Worker job completed with a typed domain failure.

    Not an unexpected exception — those still surface via info.success=False.
    code is a machine-readable slug; message is human-readable; details carries
    structured context (char_counts, reasons, etc.).
    """

    status: Literal["failure"] = "failure"
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
