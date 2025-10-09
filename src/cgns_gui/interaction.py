"""Interaction helpers for VTK interactor events."""

from __future__ import annotations

from collections.abc import Callable

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