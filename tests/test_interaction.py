"""Tests for the InteractionController."""

from __future__ import annotations

import pytest

pytest.importorskip("vtkmodules.vtkRenderingCore")

from vtkmodules.vtkRenderingCore import vtkRenderer

from cgns_gui.interaction import AdaptiveTrackballCameraStyle, InteractionController


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


def test_adaptive_style_focus_updates_camera_and_motion_factor():
    renderer = vtkRenderer()
    style = AdaptiveTrackballCameraStyle()
    style.set_renderer(renderer)

    camera = renderer.GetActiveCamera()
    camera.SetPosition(0.0, 0.0, 50.0)
    camera.SetFocalPoint(0.0, 0.0, 0.0)

    bounds = (0.0, 10.0, -5.0, 5.0, -2.0, 2.0)
    style.focus_on_bounds(bounds)

    focus = camera.GetFocalPoint()
    assert focus == pytest.approx((5.0, 0.0, 0.0))

    distance = camera.GetDistance()
    extent = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])
    expected = max(0.2, min(20.0, distance / extent))
    assert style.GetMotionFactor() == pytest.approx(expected, rel=1e-3)


def test_adaptive_style_ignores_invalid_bounds():
    renderer = vtkRenderer()
    style = AdaptiveTrackballCameraStyle()
    style.set_renderer(renderer)

    original_factor = style.GetMotionFactor()
    style.focus_on_bounds((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    assert style.GetMotionFactor() == pytest.approx(original_factor)