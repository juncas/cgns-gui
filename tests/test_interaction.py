"""Tests for the InteractionController."""

from __future__ import annotations

import pytest

from cgns_gui.interaction import InteractionController


class _FakeInteractor:
    def __init__(self) -> None:
        self._callback = None
        self._key = ""

    def AddObserver(self, event: str, callback, priority: float):  # noqa: ANN001
        assert event == "KeyPressEvent"
        self._callback = callback
        return 1

    def RemoveObserver(self, observer_id: int) -> None:
        self._callback = None

    def GetKeySym(self) -> str:
        return self._key

    def trigger(self, key: str) -> None:
        self._key = key
        if self._callback is not None:
            self._callback(self, None)


def test_interaction_controller_triggers_registered_callbacks():
    triggered: list[str] = []

    controller = InteractionController()
    controller.register_shortcut("r", lambda: triggered.append("reset"))

    fake = _FakeInteractor()
    controller.attach(fake)

    fake.trigger("r")
    assert triggered == ["reset"]

    controller.trigger("R")
    assert triggered == ["reset", "reset"]

    controller.detach()
    fake.trigger("r")
    assert triggered == ["reset", "reset"]


def test_interaction_controller_rejects_empty_key():
    controller = InteractionController()
    with pytest.raises(ValueError):
        controller.register_shortcut("", lambda: None)