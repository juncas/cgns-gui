"""Application entry point for the CGNS visualizer."""

from __future__ import annotations

import sys
from pathlib import Path

# VTK requires explicit imports for rendering backends
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkRenderingCore import vtkRenderer

from .interaction import InteractionController
from .loader import CgnsLoader
from .model import CgnsModel, Section, Zone
from .scene import RenderStyle, SceneManager
from .selection import SelectionController


class MainWindow(QMainWindow):
    """Main window embedding a VTK render view."""

    def __init__(self, parent: QWidget | None = None) -> None:  # noqa: D401
        super().__init__(parent)
        self.setWindowTitle("CGNS Viewer")
        self.resize(1024, 768)

        self._model: CgnsModel | None = None
        self._loader = CgnsLoader()

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal, central)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        sidebar = QWidget(splitter)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(8)

        self.tree = _ModelTreeWidget(sidebar)
        sidebar_layout.addWidget(self.tree, 1)

        self.details = SectionDetailsWidget(sidebar)
        sidebar_layout.addWidget(self.details, 0)

        splitter.addWidget(sidebar)

        vtk_container = QWidget(splitter)
        vtk_layout = QVBoxLayout(vtk_container)
        vtk_layout.setContentsMargins(0, 0, 0, 0)
        vtk_layout.setSpacing(0)
        self.vtk_widget = QVTKRenderWindowInteractor(vtk_container, renderWindow=None)
        vtk_layout.addWidget(self.vtk_widget)
        splitter.addWidget(vtk_container)
        splitter.setStretchFactor(1, 1)

        self.renderer = vtkRenderer()
        self.scene = SceneManager(self.renderer)
        self._render_group: QActionGroup | None = None
        self._surface_action: QAction | None = None
        self._wireframe_action: QAction | None = None
        self._orientation_widget: vtkOrientationMarkerWidget | None = None
        self._axes_actor: vtkAxesActor | None = None
        self._orientation_action: QAction | None = None
        self._interaction_controller = InteractionController()
        self._setup_renderer()
        self._create_actions()
        self._selection_controller = SelectionController(
            self.scene,
            self.tree,
            self.vtk_widget,
            self,
        )
        self._selection_controller.sectionChanged.connect(self._on_section_changed)
        self.details.clear()

    def _setup_renderer(self) -> None:
        """Prepare renderer background and attach to the VTK widget."""

        render_window = self.vtk_widget.GetRenderWindow()
        render_window.AddRenderer(self.renderer)
        self.renderer.SetBackground(0.1, 0.1, 0.12)

    def start(self) -> None:
        """Initialise the interactor and start rendering."""

        self.vtk_widget.Initialize()
        render_window = self.vtk_widget.GetRenderWindow()
        interactor = render_window.GetInteractor()
        if interactor is not None:
            interactor_style = vtkInteractorStyleTrackballCamera()
            interactor.SetInteractorStyle(interactor_style)
            self._interaction_controller.attach(interactor)
            self._ensure_orientation_widget(interactor)
        self.vtk_widget.Start()

    def load_file(self, path: str) -> None:
        """Load a CGNS file and refresh the UI."""

        model = self._loader.load(path)
        self.load_model(model)

    def load_model(self, model: CgnsModel) -> None:
        self._model = model
        self.tree.populate(model)
        self.scene.load_model(model)
        self._selection_controller.sync_scene()
        self._selection_controller.clear()
        self._reset_camera()

    def _on_section_changed(self, key: tuple[str, int] | None) -> None:
        info = self.tree.section_info(key)
        if info is None:
            self.details.clear()
            return

        zone, section = info
        self.details.update_section(zone, section)

    def _create_actions(self) -> None:
        toolbar = QToolBar("main", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        open_action = QAction("打开 CGNS", self)
        open_action.triggered.connect(self._open_dialog)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        self._render_group = QActionGroup(self)
        self._render_group.setExclusive(True)

        self._surface_action = QAction("表面", self)
        self._surface_action.setCheckable(True)
        self._surface_action.setChecked(True)
        self._surface_action.triggered.connect(self._set_surface_mode)
        self._render_group.addAction(self._surface_action)
        toolbar.addAction(self._surface_action)

        self._wireframe_action = QAction("线框", self)
        self._wireframe_action.setCheckable(True)
        self._wireframe_action.triggered.connect(self._set_wireframe_mode)
        self._render_group.addAction(self._wireframe_action)
        toolbar.addAction(self._wireframe_action)

        toolbar.addSeparator()

        reset_action = QAction("重置视角", self)
        reset_action.triggered.connect(self._reset_camera)
        toolbar.addAction(reset_action)

        self._orientation_action = QAction("显示坐标轴", self)
        self._orientation_action.setCheckable(True)
        self._orientation_action.setChecked(True)
        self._orientation_action.triggered.connect(self._toggle_orientation_marker)
        toolbar.addAction(self._orientation_action)

        self._interaction_controller.register_shortcut("r", self._reset_camera)
        self._interaction_controller.register_shortcut("w", self._activate_wireframe)
        self._interaction_controller.register_shortcut("s", self._activate_surface)
        self._interaction_controller.register_shortcut("o", self._toggle_orientation_shortcut)

    def _open_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 CGNS 文件",
            str(Path.home()),
            "CGNS Files (*.cgns *.hdf5 *.h5);;All Files (*)",
        )
        if file_path:
            self.load_file(file_path)

    def _reset_camera(self) -> None:
        self.renderer.ResetCamera()
        render_window = self.vtk_widget.GetRenderWindow()
        render_window.Render()

    def _toggle_orientation_marker(self, checked: bool) -> None:
        if self._orientation_widget is None:
            interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
            if interactor is not None and checked:
                self._ensure_orientation_widget(interactor)
        if self._orientation_widget is not None:
            self._orientation_widget.SetEnabled(1 if checked else 0)
            if checked:
                self._orientation_widget.InteractiveOn()
            else:
                self._orientation_widget.InteractiveOff()
        self.vtk_widget.GetRenderWindow().Render()

    def _ensure_orientation_widget(self, interactor) -> None:
        if self._orientation_widget is not None:
            self._orientation_widget.SetInteractor(interactor)
            if self._orientation_action and not self._orientation_action.isChecked():
                self._orientation_widget.SetEnabled(0)
            return

        self._axes_actor = vtkAxesActor()
        widget = vtkOrientationMarkerWidget()
        widget.SetOrientationMarker(self._axes_actor)
        widget.SetInteractor(interactor)
        widget.SetViewport(0.0, 0.0, 0.25, 0.25)
        widget.SetEnabled(1)
        widget.InteractiveOn()
        if self._orientation_action and not self._orientation_action.isChecked():
            widget.SetEnabled(0)
            widget.InteractiveOff()
        self._orientation_widget = widget

    def _set_surface_mode(self, checked: bool) -> None:
        if checked:
            self.scene.set_render_style(RenderStyle.SURFACE)

    def _set_wireframe_mode(self, checked: bool) -> None:
        if checked:
            self.scene.set_render_style(RenderStyle.WIREFRAME)


    def _activate_surface(self) -> None:
        self._set_surface_mode(True)
        if self._surface_action is not None:
            self._surface_action.setChecked(True)
        if self._wireframe_action is not None:
            self._wireframe_action.setChecked(False)

    def _activate_wireframe(self) -> None:
        self._set_wireframe_mode(True)
        if self._wireframe_action is not None:
            self._wireframe_action.setChecked(True)
        if self._surface_action is not None:
            self._surface_action.setChecked(False)

    def _toggle_orientation_shortcut(self) -> None:
        if self._orientation_action is None:
            return
        new_state = not self._orientation_action.isChecked()
        self._orientation_action.setChecked(new_state)
        self._toggle_orientation_marker(new_state)


class _ModelTreeWidget(QTreeWidget):
    """Tree widget to display CGNS zones and sections."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["名称", "类型", "单元数"])
        self.setColumnWidth(0, 200)
        self._section_index: dict[tuple[str, int], QTreeWidgetItem] = {}
        self._section_data: dict[tuple[str, int], tuple[Zone, Section]] = {}

    def populate(self, model: CgnsModel) -> None:
        self.clear()
        self._section_index.clear()
        self._section_data.clear()
        for zone in model.zones:
            zone_item = QTreeWidgetItem([zone.name, "Zone", str(zone.total_cells)])
            self.addTopLevelItem(zone_item)
            self._add_sections(zone_item, zone)
        self.expandAll()

    def _add_sections(self, parent: QTreeWidgetItem, zone: Zone) -> None:
        for section in zone.iter_sections():
            cells = str(section.mesh.connectivity.shape[0])
            item = QTreeWidgetItem([section.name, section.element_type, cells])
            key = (zone.name, section.id)
            item.setData(0, Qt.UserRole, key)
            parent.addChild(item)
            self._section_index[key] = item
            self._section_data[key] = (zone, section)

    def section_key(self, item: QTreeWidgetItem | None) -> tuple[str, int] | None:
        if item is None:
            return None
        data = item.data(0, Qt.UserRole)
        if isinstance(data, tuple) and len(data) == 2:
            return data  # type: ignore[return-value]
        return None

    def select_section(self, key: tuple[str, int] | None) -> None:
        try:
            self.blockSignals(True)
            if key is None:
                selection_model = self.selectionModel()
                if selection_model is not None:
                    selection_model.clearSelection()
                self.setCurrentIndex(QModelIndex())
                return
            item = self._section_index.get(key)
            if item is not None:
                self.setCurrentItem(item)
        finally:
            self.blockSignals(False)

    def section_info(self, key: tuple[str, int] | None) -> tuple[Zone, Section] | None:
        if key is None:
            return None
        return self._section_data.get(key)


class SectionDetailsWidget(QWidget):
    """Display basic metadata for the selected section."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self._zone_label = QLabel()
        self._name_label = QLabel()
        self._type_label = QLabel()
        self._cells_label = QLabel()
        self._points_label = QLabel()
        self._range_label = QLabel()

        for label in (
            self._zone_label,
            self._name_label,
            self._type_label,
            self._cells_label,
            self._points_label,
            self._range_label,
        ):
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addRow("Zone", self._zone_label)
        layout.addRow("Section", self._name_label)
        layout.addRow("Type", self._type_label)
        layout.addRow("Cells", self._cells_label)
        layout.addRow("Points", self._points_label)
        layout.addRow("Range", self._range_label)

        self.clear()

    def clear(self) -> None:
        self._set_text("-", "-", "-", "-", "-", "-")

    def update_section(self, zone: Zone, section: Section) -> None:
        mesh = section.mesh
        cell_count = mesh.connectivity.shape[0]
        point_count = mesh.points.shape[0]
        self._set_text(
            zone.name,
            section.name,
            section.element_type,
            str(cell_count),
            str(point_count),
            f"{section.range[0]} - {section.range[1]}",
        )

    def _set_text(
        self,
        zone: str,
        name: str,
        element_type: str,
        cells: str,
        points: str,
        range_: str,
    ) -> None:
        self._zone_label.setText(zone)
        self._name_label.setText(name)
        self._type_label.setText(element_type)
        self._cells_label.setText(cells)
        self._points_label.setText(points)
        self._range_label.setText(range_)

    def snapshot(self) -> dict[str, str]:
        """Return the current label texts for tests and debugging."""

        return {
            "zone": self._zone_label.text(),
            "name": self._name_label.text(),
            "type": self._type_label.text(),
            "cells": self._cells_label.text(),
            "points": self._points_label.text(),
            "range": self._range_label.text(),
        }


def main(argv: list[str] | None = None) -> int:
    """Application entry point."""

    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName("CGNS Viewer")
    app.setOrganizationName("CGNS")
    app.setAttribute(Qt.AA_EnableHighDpiScaling)

    window = MainWindow()
    window.show()
    window.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
