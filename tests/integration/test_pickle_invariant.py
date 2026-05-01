"""Pickle round-trip invariant test for every Exception subclass in lyw_core.

Arq stores job results (including raised exceptions) in Redis using pickle.
The API endpoint deserializes them to build the status="failed" response.
Any exception that cannot survive pickle.loads(pickle.dumps(e)) will crash
the API endpoint with an unhandled error instead of returning status="failed".

This test:
  1. Discovers every Exception subclass defined under src/lyw_core/ via
     import-walk so new exceptions are automatically covered.
  2. Asserts each discovered class is registered in _REGISTRY with a
     factory function — the registration check fails CI when a new exception
     is added without a corresponding pickle test instance.
  3. Asserts pickle.loads(pickle.dumps(e)) preserves all custom attributes
     (those in __dict__) for each registered instance.
"""

from __future__ import annotations

import contextlib
import importlib
import pickle
import pkgutil
from collections.abc import Callable

import pytest

import lyw_core
from lyw_core.chunker.llm_refiner import LLMRefinerError
from lyw_core.clients.ollama import OllamaError
from lyw_core.personalization.replace import ReplaceSourceTooThinError
from lyw_core.validators.base import ValidationError

# Registry: maps each known lyw_core exception class to a factory that
# produces a representative instance for pickle testing.
_REGISTRY: dict[type[Exception], Callable[[], Exception]] = {
    ValidationError: lambda: ValidationError(["reason one", "reason two"]),
    ReplaceSourceTooThinError: lambda: ReplaceSourceTooThinError("concept-1", 50, 8),
    LLMRefinerError: lambda: LLMRefinerError("model returned invalid JSON"),
    OllamaError: lambda: OllamaError(503, "service unavailable"),
}


def _discover_lyw_core_exceptions() -> set[type[Exception]]:
    """Import every module under lyw_core and collect Exception subclasses."""
    for mod_info in pkgutil.walk_packages(lyw_core.__path__, prefix="lyw_core."):
        with contextlib.suppress(Exception):
            importlib.import_module(mod_info.name)

    found: set[type[Exception]] = set()

    def _walk(cls: type) -> None:
        for sub in cls.__subclasses__():
            if sub.__module__.startswith("lyw_core.") and sub not in found:
                found.add(sub)
                _walk(sub)

    _walk(Exception)
    return found


@pytest.mark.integration
def test_all_lyw_core_exceptions_are_registered() -> None:
    """Every Exception subclass under src/lyw_core/ must appear in _REGISTRY.

    When a new exception class is added without a corresponding _REGISTRY
    entry, this test fails on the integration job before the PR merges —
    preventing an accidental pickle bomb from reaching production.
    """
    discovered = _discover_lyw_core_exceptions()
    unregistered = discovered - set(_REGISTRY)
    assert not unregistered, (
        "New lyw_core exceptions require a pickle test instance in _REGISTRY "
        "(tests/integration/test_pickle_invariant.py): "
        + ", ".join(sorted(cls.__qualname__ for cls in unregistered))
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "exc_class,factory",
    list(_REGISTRY.items()),
    ids=[cls.__name__ for cls in _REGISTRY],
)
def test_exception_pickle_round_trip(
    exc_class: type[Exception],
    factory: Callable[[], Exception],
) -> None:
    """pickle.loads(pickle.dumps(exc)) preserves type and all custom attributes."""
    exc = factory()
    restored = pickle.loads(pickle.dumps(exc))

    assert type(restored) is exc_class

    custom_attrs = {k: v for k, v in vars(exc).items() if not k.startswith("_")}
    for attr, expected in custom_attrs.items():
        actual = getattr(restored, attr)
        assert actual == expected, (
            f"{exc_class.__name__}.{attr}: "
            f"expected {expected!r}, got {actual!r} after pickle round-trip"
        )
