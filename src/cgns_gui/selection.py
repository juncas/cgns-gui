"""Selection synchronisation between UI tree and VTK scene."""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QTreeWidget
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkActor, vtkCellPicker

from .scene import SceneManager


class SelectionController(QObject):
    """Coordinate section selection between the tree view and VTK actors."""

    def __init__(
        self,
        scene: SceneManager,
        tree: QTreeWidget,
        interactor: QVTKRenderWindowInteractor,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._scene = scene
        self._tree = tree
        self._interactor = interactor
        self._updating = False

        self._picker = vtkCellPicker()
        self._picker.SetTolerance(0.0005)
        self._picker.PickFromListOn()

        self._tree.itemSelectionChanged.connect(self._on_tree_selection)
        self._interactor.AddObserver(
            "LeftButtonPressEvent",
            self._on_left_button_press,
            1.0,
        )

    def sync_scene(self) -> None:
        """Refresh pick list after actors change."""

        self._picker.InitializePickList()
        for actor in self._scene.iter_actors():
            self._picker.AddPickList(actor)

    def clear(self) -> None:
        """Clear current selection state."""

        self._updating = True
        try:
            self._scene.highlight(None)
            if hasattr(self._tree, "select_section"):
                self._tree.select_section(None)  # type: ignore[attr-defined]
        finally:
            self._updating = False

    def _on_tree_selection(self) -> None:
        if self._updating:
            return

        key = None
        if hasattr(self._tree, "section_key"):
            key = self._tree.section_key(self._tree.currentItem())  # type: ignore[attr-defined]

        self._updating = True
        try:
            self._scene.highlight(key)
        finally:
            self._updating = False

    def _on_left_button_press(self, obj, event) -> None:  # noqa: ANN001, D401
        click_pos = self._interactor.GetEventPosition()
        self._picker.Pick(click_pos[0], click_pos[1], 0, self._scene.renderer)
        actor: vtkActor | None = self._picker.GetActor()
        key = self._scene.get_key_for_actor(actor)

        self._updating = True
        try:
            if key is not None:
                self._scene.highlight(key)
                if hasattr(self._tree, "select_section"):
                    self._tree.select_section(key)  # type: ignore[attr-defined]
            else:
                self._scene.highlight(None)
                if hasattr(self._tree, "select_section"):
                    self._tree.select_section(None)  # type: ignore[attr-defined]
        finally:
            self._updating = False

        style = self._interactor.GetInteractorStyle()
        if style is not None:
            style.OnLeftButtonDown()