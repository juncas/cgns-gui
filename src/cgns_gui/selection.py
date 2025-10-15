"""Selection synchronisation between UI tree and VTK scene."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QTreeWidget
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkActor, vtkCellPicker

from .scene import SceneManager


class SelectionController(QObject):
    """Coordinate section selection between the tree view and VTK actors."""

    sectionChanged = Signal(object)

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
        for key, actor in self._scene.iter_actor_items():
            if self._scene.is_section_visible(key):
                self._picker.AddPickList(actor)

    def clear(self) -> None:
        """Clear current selection state."""

        self._updating = True
        try:
            self._scene.highlight(None)
            if hasattr(self._tree, "select_section"):
                self._tree.select_section(None)  # type: ignore[attr-defined]
            self.sectionChanged.emit(None)
        finally:
            self._updating = False

    def _on_tree_selection(self) -> None:
        if self._updating:
            return

        key = None
        family_keys = None
        
        current_item = self._tree.currentItem()
        
        # 检查是否是 Family 节点
        if hasattr(self._tree, "get_family_sections"):
            family_keys = self._tree.get_family_sections(current_item)  # type: ignore[attr-defined]
        
        # 如果不是 Family，获取单个 section key
        if family_keys is None and hasattr(self._tree, "section_key"):
            key = self._tree.section_key(current_item)  # type: ignore[attr-defined]

        self._updating = True
        try:
            if family_keys:
                # Family 节点：高亮所有相关 sections
                visible_keys = [k for k in family_keys if self._scene.is_section_visible(k)]
                self._scene.highlight_multiple(visible_keys)
                # 立即刷新渲染
                self._interactor.GetRenderWindow().Render()
                # 发送第一个 key 用于详情显示，或者 None
                self.sectionChanged.emit(visible_keys[0] if visible_keys else None)
            elif key is None:
                # 无选择
                self._scene.highlight(None)
                self._interactor.GetRenderWindow().Render()
                self.sectionChanged.emit(None)
            elif self._scene.is_section_visible(key):
                # 单个 section 节点
                self._scene.highlight(key)
                self._interactor.GetRenderWindow().Render()
                self.sectionChanged.emit(key)
            else:
                # Section 不可见
                self._scene.highlight(None)
                self._interactor.GetRenderWindow().Render()
                self.sectionChanged.emit(None)
        finally:
            self._updating = False

    def _on_left_button_press(self, obj, event) -> None:  # noqa: ANN001, D401
        click_pos = self._interactor.GetEventPosition()
        self._picker.Pick(click_pos[0], click_pos[1], 0, self._scene.renderer)
        actor: vtkActor | None = self._picker.GetActor()
        key = self._scene.get_key_for_actor(actor)
        if key is not None and not self._scene.is_section_visible(key):
            key = None

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
            self.sectionChanged.emit(key)
        finally:
            self._updating = False

        style = self._interactor.GetInteractorStyle()
        if style is not None:
            style.OnLeftButtonDown()