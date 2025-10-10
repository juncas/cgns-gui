"""Interaction helpers for VTK interactor events."""

from __future__ import annotations

from collections.abc import Callable

from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera

Callback = Callable[[], None]


class InteractionController:
    """Manage custom key shortcuts for a VTK interactor."""

    def __init__(self) -> None:
        self._callbacks: dict[str, Callback] = {}
        self._interactor = None
        self._observer_id: int | None = None

    def register_shortcut(self, key: str, callback: Callback) -> None:
        if not key:
            raise ValueError("Shortcut key cannot be empty")
        self._callbacks[key.lower()] = callback

    def attach(self, interactor) -> None:  # noqa: ANN001 - VTK uses dynamic types
        if interactor is self._interactor:
            return
        self.detach()
        self._interactor = interactor
        if interactor is None:
            return
        self._observer_id = interactor.AddObserver(
            "KeyPressEvent",
            self._on_key_press,
            1.0,
        )

    def detach(self) -> None:
        if self._interactor is not None and self._observer_id is not None:
            self._interactor.RemoveObserver(self._observer_id)
        self._interactor = None
        self._observer_id = None

    def trigger(self, key: str) -> None:
        callback = self._callbacks.get(key.lower())
        if callback:
            callback()

    def _on_key_press(self, obj, event) -> None:  # noqa: ANN001, D401 - VTK callback signature
        if self._interactor is None:
            return
        key = self._interactor.GetKeySym()
        if key:
            self.trigger(key)

def _bounds_valid(bounds: tuple[float, ...]) -> bool:
    if len(bounds) != 6:
        return False
    x_min, x_max, y_min, y_max, z_min, z_max = bounds
    if x_min > x_max or y_min > y_max or z_min > z_max:
        return False
    return (x_max - x_min) > 0.0 or (y_max - y_min) > 0.0 or (z_max - z_min) > 0.0

class AdaptiveTrackballCameraStyle(vtkInteractorStyleTrackballCamera):
    """Trackball style that adapts pan speed and rotation focus to scene bounds."""

    def __init__(self) -> None:
        super().__init__()
        self._renderer = None
        self._scene_bounds: tuple[float, float, float, float, float, float] | None = None
        self._min_motion_factor = 0.2
        self._max_motion_factor = 20.0

    def set_renderer(self, renderer) -> None:  # noqa: ANN001 - VTK uses dynamic types
        self._renderer = renderer
        if renderer is not None and self._scene_bounds is not None:
            self._apply_focus(self._scene_bounds, force=True)

    def set_scene_bounds(
        self,
        bounds: tuple[float, float, float, float, float, float] | None,
    ) -> None:
        if bounds is not None and not _bounds_valid(bounds):
            return
        self._scene_bounds = bounds
        if bounds is not None:
            self._apply_focus(bounds, force=False)

    def focus_on_bounds(
        self,
        bounds: tuple[float, float, float, float, float, float] | None,
    ) -> None:
        if bounds is None or not _bounds_valid(bounds):
            return
        self._scene_bounds = bounds
        self._apply_focus(bounds, force=True)

    def Pan(self) -> None:  # noqa: N802 - VTK API
        self._update_motion_factor()
        super().Pan()

    def OnMouseWheelForward(self) -> None:  # noqa: N802 - VTK API
        super().OnMouseWheelForward()
        self._update_motion_factor()

    def OnMouseWheelBackward(self) -> None:  # noqa: N802 - VTK API
        super().OnMouseWheelBackward()
        self._update_motion_factor()

    def Rotate(self) -> None:  # noqa: N802 - VTK API
        super().Rotate()
        self._update_motion_factor()

    def _apply_focus(
        self,
        bounds: tuple[float, float, float, float, float, float],
        *,
        force: bool,
    ) -> None:
        if self._renderer is None:
            return
        camera = self._renderer.GetActiveCamera()
        if camera is None:
            return
        x_min, x_max, y_min, y_max, z_min, z_max = bounds
        center = (
            (x_min + x_max) / 2.0,
            (y_min + y_max) / 2.0,
            (z_min + z_max) / 2.0,
        )
        if force:
            camera.SetFocalPoint(*center)
        else:
            current_focus = camera.GetFocalPoint()
            if any(abs(current_focus[i] - center[i]) > 1e-6 for i in range(3)):
                camera.SetFocalPoint(*center)
        self._renderer.ResetCameraClippingRange()
        self._update_motion_factor()

    def _update_motion_factor(self) -> None:
        if self._renderer is None:
            return
        camera = self._renderer.GetActiveCamera()
        if camera is None:
            return
        bounds = self._scene_bounds
        if bounds is None or not _bounds_valid(bounds):
            return
        x_min, x_max, y_min, y_max, z_min, z_max = bounds
        dx = x_max - x_min
        dy = y_max - y_min
        dz = z_max - z_min
        extent = max(dx, dy, dz, 1e-6)
        distance = max(camera.GetDistance(), 1e-6)
        factor = distance / extent
        factor = max(self._min_motion_factor, min(self._max_motion_factor, factor))
        self.SetMotionFactor(factor)