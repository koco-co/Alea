"""Lazy, explicit bootstrap for Celery roundtable phase execution.

The worker process must not silently accept provider jobs without a configured
executor.  The factory is deliberately supplied through an environment
variable so API and CLI provider runtimes can share the same PhaseExecutor
contract without importing the FastAPI application or leaking secrets into the
broker payload.
"""

from __future__ import annotations

import importlib
import os
import threading
from typing import Any, Protocol, cast

_FACTORY_ENV = "ALEA_PHASE_EXECUTOR_FACTORY"
_ALLOWED_MODULE_PREFIX = "app."


class PhaseExecutorLike(Protocol):
    async def execute(self, command: Any, *, celery_task_id: str | None) -> dict[str, Any]: ...


_lock = threading.Lock()
_cached_executor: PhaseExecutorLike | None = None


def resolve_phase_executor() -> PhaseExecutorLike:
    """Resolve and cache the configured executor.

    ``ALEA_PHASE_EXECUTOR_FACTORY`` must use ``module.path:factory`` syntax.
    The module is restricted to the Alea application package to prevent an
    accidentally user-controlled environment value from importing arbitrary
    third-party modules.  The factory is synchronous; it may construct an
    executor whose ``execute`` method is asynchronous.
    """

    global _cached_executor
    if _cached_executor is not None:
        return _cached_executor

    with _lock:
        if _cached_executor is not None:
            return _cached_executor

        specification = os.getenv(_FACTORY_ENV, "").strip()
        if not specification:
            raise RuntimeError(f"{_FACTORY_ENV} is required; expected app.module:factory")

        module_name, separator, attribute_name = specification.partition(":")
        if (
            not separator
            or not module_name.startswith(_ALLOWED_MODULE_PREFIX)
            or not attribute_name
            or "." in attribute_name
        ):
            raise RuntimeError(f"invalid {_FACTORY_ENV}; expected app.module:factory")

        module = importlib.import_module(module_name)
        factory = getattr(module, attribute_name, None)
        if not callable(factory):
            raise RuntimeError(f"phase executor factory is not callable: {specification}")

        executor = factory()
        execute = getattr(executor, "execute", None)
        if not callable(execute):
            raise RuntimeError("phase executor factory must return an object with execute()")

        _cached_executor = cast(PhaseExecutorLike, executor)
        return _cached_executor


def reset_phase_executor_for_tests() -> None:
    """Clear the process cache.  Intended only for isolated unit tests."""

    global _cached_executor
    with _lock:
        _cached_executor = None
