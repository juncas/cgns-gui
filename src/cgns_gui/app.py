"""Application entry point for the CGNS visualizer."""

from __future__ import annotations

import sys
from pathlib import Path

# VTK requires explicit imports for rendering backends
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
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
from vtkmodules.vtkRenderingCore import vtkRenderer

from .loader import CgnsLoader
from .model import CgnsModel, Zone
from .scene import SceneManager


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

        self.tree = _ModelTreeWidget(splitter)
        splitter.addWidget(self.tree)

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
        self._setup_renderer()
        self._create_actions()

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
        self.vtk_widget.Start()

    def load_file(self, path: str) -> None:
        """Load a CGNS file and refresh the UI."""

        model = self._loader.load(path)
        self.load_model(model)

    def load_model(self, model: CgnsModel) -> None:
        self._model = model
        self.tree.populate(model)
        self.scene.load_model(model)

    def _create_actions(self) -> None:
        toolbar = QToolBar("main", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        open_action = QAction("打开 CGNS", self)
        open_action.triggered.connect(self._open_dialog)
        toolbar.addAction(open_action)

    def _open_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 CGNS 文件",
            str(Path.home()),
            "CGNS Files (*.cgns *.hdf5 *.h5);;All Files (*)",
        )
        if file_path:
            self.load_file(file_path)


class _ModelTreeWidget(QTreeWidget):
    """Tree widget to display CGNS zones and sections."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["名称", "类型", "单元数"])
        self.setColumnWidth(0, 200)

    def populate(self, model: CgnsModel) -> None:
        self.clear()
        for zone in model.zones:
            zone_item = QTreeWidgetItem([zone.name, "Zone", str(zone.total_cells)])
            self.addTopLevelItem(zone_item)
            self._add_sections(zone_item, zone)
        self.expandAll()

    def _add_sections(self, parent: QTreeWidgetItem, zone: Zone) -> None:
        for section in zone.iter_sections():
            cells = str(section.mesh.connectivity.shape[0])
            item = QTreeWidgetItem([section.name, section.element_type, cells])
            item.setData(0, Qt.UserRole, section.id)
            parent.addChild(item)


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
