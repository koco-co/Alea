from __future__ import annotations

import sys
from collections.abc import Iterator
from types import ModuleType

import pytest

from app.workers.executor_bootstrap import (
    reset_phase_executor_for_tests,
    resolve_phase_executor,
)


@pytest.fixture(autouse=True)
def reset_executor() -> Iterator[None]:
    reset_phase_executor_for_tests()
    yield
    reset_phase_executor_for_tests()


def test_factory_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALEA_PHASE_EXECUTOR_FACTORY", raising=False)

    with pytest.raises(RuntimeError, match="ALEA_PHASE_EXECUTOR_FACTORY is required"):
        resolve_phase_executor()


def test_factory_must_be_inside_app_package(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALEA_PHASE_EXECUTOR_FACTORY", "os:getcwd")

    with pytest.raises(RuntimeError, match="invalid ALEA_PHASE_EXECUTOR_FACTORY"):
        resolve_phase_executor()


def test_executor_is_created_once(monkeypatch: pytest.MonkeyPatch) -> None:
    module = ModuleType("app.tests.fake_phase_factory")
    calls = 0

    class Executor:
        async def execute(self, command: object, *, celery_task_id: str | None) -> dict[str, str]:
            del command, celery_task_id
            return {"status": "ok"}

    def create() -> Executor:
        nonlocal calls
        calls += 1
        return Executor()

    module.create = create  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setenv("ALEA_PHASE_EXECUTOR_FACTORY", "app.tests.fake_phase_factory:create")

    first = resolve_phase_executor()
    second = resolve_phase_executor()

    assert first is second
    assert calls == 1
