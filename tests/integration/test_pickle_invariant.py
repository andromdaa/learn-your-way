"""Pickle round-trip invariant test for Exception subclasses that cross the Arq boundary.

Arq stores job results (including raised exceptions) in Redis using pickle.
The API endpoint deserializes them to build the status="failed" response.
Any exception that cannot survive pickle.loads(pickle.dumps(e)) will crash
the API endpoint with an unhandled error instead of returning status="failed".

After the typed-worker-result-protocol migration (AND-33), the personalize_concept
job converts all domain exceptions to a Failure before returning, so those
exceptions never cross the boundary and are therefore BOUNDARY_EXEMPT.

This test:
  1. Discovers every Exception subclass defined under src/lyw_core/ via
     import-walk so new exceptions are automatically covered.
  2. Asserts each discovered class is either registered in _REGISTRY (will be
     pickle-tested) or listed in _BOUNDARY_EXEMPT (documented as not needing
     to survive the pickle round-trip because they never reach Redis).
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

# Registry: maps each known lyw_core exception that CAN cross the Arq pickle
# boundary to a factory that produces a representative instance for pickle testing.
#
# After AND-33, personalize_concept converts ReplaceSourceTooThinError,
# OllamaError, and ValidationError to Failure at the job boundary.
# Only LLMRefinerError (from the ingest path) remains potentially boundary-crossing.
_REGISTRY: dict[type[Exception], Callable[[], Exception]] = {
    LLMRefinerError: lambda: LLMRefinerError("model returned invalid JSON"),
}

# Exceptions documented as NOT needing to cross the Arq pickle boundary.
# personalize_concept catches each of these and converts them to a typed Failure,
# so they never reach Redis and do not need a __reduce__ override.
_BOUNDARY_EXEMPT: set[type[Exception]] = {
    ValidationError,
    ReplaceSourceTooThinError,
    OllamaError,
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
    """Every Exception subclass under src/lyw_core/ must be in _REGISTRY or _BOUNDARY_EXEMPT.

    When a new exception class is added without a corresponding _REGISTRY
    entry (or _BOUNDARY_EXEMPT justification), this test fails on the
    integration job before the PR merges — preventing an accidental pickle
    bomb from reaching production.

    _BOUNDARY_EXEMPT is for exceptions whose callers are guaranteed to catch
    them before returning from the Arq job. Add to _BOUNDARY_EXEMPT when the
    exception is proven to never cross the pickle boundary; add to _REGISTRY
    when it can still reach Redis.
    """
    discovered = _discover_lyw_core_exceptions()
    unregistered = discovered - set(_REGISTRY) - _BOUNDARY_EXEMPT
    assert not unregistered, (
        "New lyw_core exceptions require either a pickle test instance in _REGISTRY "
        "or a documented entry in _BOUNDARY_EXEMPT "
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
