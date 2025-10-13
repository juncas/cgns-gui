"""Application entry point for the CGNS visualizer."""

from __future__ import annotations

import os
import sys
import warnings
import ctypes
from collections.abc import MutableMapping
from ctypes.util import find_library
from dataclasses import dataclass
from functools import lru_cache, partial
from pathlib import Path

# VTK requires explicit imports for rendering backends
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QSlider,
    QSplitter,
    QStatusBar,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkRenderer

if __package__ in {None, ""}:
    package_root = Path(__file__).resolve().parent.parent
    package_path = str(package_root)
    if package_path not in sys.path:
        sys.path.insert(0, package_path)

from .i18n import install_translators
from .interaction import AdaptiveTrackballCameraStyle, InteractionController
from .loader import CgnsLoader
from .model import CgnsModel, Section, Zone
from .scene import RenderStyle, SceneManager
from .selection import SelectionController

BACKGROUND_OPTIONS: dict[str, tuple[float, float, float]] = {
    "Dark Slate": (0.1, 0.1, 0.12),
    "Carbon Black": (0.05, 0.05, 0.07),
    "Light Gray": (0.85, 0.85, 0.9),
}

DEFAULT_BACKGROUND_NAME = "Dark Slate"

RENDER_STYLE_LABELS: dict[RenderStyle, str] = {
    RenderStyle.SURFACE: "Surface",
    RenderStyle.WIREFRAME: "Wireframe",
}


@dataclass
class ViewerSettings:
    background: str
    render_style: RenderStyle


@lru_cache(maxsize=1)
def _windows_supports_opengl() -> bool:
    window: vtkRenderWindow | None = None
    try:
        window = vtkRenderWindow()
        window.SetOffScreenRendering(0)
        return bool(window.SupportsOpenGL())
    except Exception:
        return False
    finally:
        if window is not None:
            try:
                window.Finalize()
            except Exception:
                pass


def _should_force_offscreen(
    environ: MutableMapping[str, str],
    *,
    find_gl=find_library,
    path_exists=Path.exists,
    is_headless: bool | None = None,
) -> bool:
    is_windows = os.name == "nt"
    if is_headless is None:
        if is_windows:
            session = environ.get("SESSIONNAME", "")
            is_headless = session.upper().startswith("RDP-")
        else:
            display = environ.get("DISPLAY")
            is_headless = not bool(display)
    if environ.get("CGNS_GUI_DISABLE_OFFSCREEN_FALLBACK") == "1":
        return False
    if is_headless:
        return True
    if not is_windows and find_gl("GL") is None:
        return True

    if is_windows:
        try:
            # Windows provides OpenGL via opengl32.dll; failure implies no ICD.
            ctypes.windll.opengl32  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            return True
        if not _windows_supports_opengl():
            return True
        return False

    drivers_env = environ.get("LIBGL_DRIVERS_PATH")
    search_dirs: list[str] = []
    if drivers_env:
        search_dirs.extend(path for path in drivers_env.split(os.pathsep) if path)
    search_dirs.extend(
        [
            "/usr/lib/x86_64-linux-gnu/dri",
            "/usr/lib64/dri",
            "/usr/lib/dri",
        ]
    )

    for directory in search_dirs:
        path = Path(directory)
        try:
            if not path_exists(path):
                continue
            for entry in path.iterdir():
                if entry.suffix == ".so" and entry.name.endswith("_dri.so"):
                    return False
        except OSError:
            continue

    return True


_REQUIRED_XCB_LIBS = (
    "xcb-cursor",
    "xcb-icccm",
    "xcb-keysyms",
    "xcb-shape",
    "xcb-xfixes",
    "xcb-xinerama",
    "xkbcommon-x11",
)


def _missing_xcb_libs(
    find_lib=find_library,
) -> list[str]:
    missing: list[str] = []
    for name in _REQUIRED_XCB_LIBS:
        try:
            if find_lib(name) is None:
                missing.append(name)
        except OSError:
            missing.append(name)
    return missing


def _prepare_environment(
    force_offscreen: bool,
    environ: MutableMapping[str, str] | None = None,
) -> None:
    """Prepare Qt/VTK environment variables before creating QApplication."""

    if environ is None:
        environ = os.environ

    platform = environ.get("QT_QPA_PLATFORM")
    display = environ.get("DISPLAY")
    wayland = environ.get("WAYLAND_DISPLAY")

    if environ.get("CGNS_GUI_FORCE_OFFSCREEN") == "1":
        force_offscreen = True

    if not force_offscreen and _should_force_offscreen(environ):
        warnings.warn(
            "OpenGL drivers not detected; falling back to offscreen rendering. "
            "Install vendor GPU drivers or a Mesa OpenGL package (e.g. libgl1-mesa-dri on Linux, "
            "mesa-dist-win on Windows) or set CGNS_GUI_DISABLE_OFFSCREEN_FALLBACK=1 to bypass.",
            RuntimeWarning,
            stacklevel=2,
        )
        force_offscreen = True

    # On Windows, Qt will automatically use the "windows" platform plugin if no platform is specified
    # Only force offscreen if explicitly requested or if OpenGL is not available
    is_windows = os.name == "nt"
    if force_offscreen or (not is_windows and platform is None and not display and not wayland):
        environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        platform = environ.get("QT_QPA_PLATFORM")

    if platform == "offscreen":
        environ.setdefault("VTK_DEFAULT_RENDER_WINDOW_OFFSCREEN", "1")
        return

    # Only check for xcb libs on Linux systems
    if not is_windows and platform in {None, "", "xcb"}:
        missing = _missing_xcb_libs()
        if missing:
            message = (
                "Qt xcb platform dependencies missing: "
                + ", ".join(missing)
                + ". Install packages such as libxcb-cursor0, libxkbcommon-x11-0, "
                  "libxcb-icccm4, libxcb-keysyms1, libxcb-xfixes0, libxcb-xinerama0."
            )
            raise RuntimeError(message)


def _configure_application_font(app: QApplication) -> None:
    """Ensure the UI uses a font that supports CJK characters when available."""

    preferred_fonts = (
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "Source Han Sans SC",
        "Microsoft YaHei",
        "PingFang SC",
    )
    families = {family.lower() for family in QFontDatabase().families()}
    for name in preferred_fonts:
        if name.lower() in families:
            app.setFont(QFont(name))
            return


class MainWindow(QMainWindow):
    """Main window embedding a VTK render view."""

    def __init__(self, parent: QWidget | None = None) -> None:  # noqa: D401
        super().__init__(parent)
        self.setWindowTitle(self.tr("CGNS Viewer"))
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
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
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
        self._adaptive_style: AdaptiveTrackballCameraStyle | None = None
        self._toolbar: QToolBar | None = None
        self._status_bar: QStatusBar = self.statusBar()
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        self._status_bar.addPermanentWidget(self._progress)
        self._status_bar.showMessage(self.tr("Ready"))
        self._background_name = DEFAULT_BACKGROUND_NAME
        self._viewer_settings = ViewerSettings(
            background=self._background_name,
            render_style=RenderStyle.SURFACE,
        )
        self._loading_active = False
        self._setup_renderer()
        self._create_actions()
        self._selection_controller = SelectionController(
            self.scene,
            self.tree,
            self.vtk_widget,
            self,
        )
        self._selection_controller.sectionChanged.connect(self._on_section_changed)
        self.details.transparencyChanged.connect(self._on_section_transparency_changed)
        self.details.clear()

    def _setup_renderer(self) -> None:
        """Prepare renderer background and attach to the VTK widget."""

        render_window = self.vtk_widget.GetRenderWindow()
        render_window.AddRenderer(self.renderer)
        self._apply_background(self._background_name)

    def start(self) -> None:
        """Initialise the interactor and start rendering."""

        self.vtk_widget.Initialize()
        render_window = self.vtk_widget.GetRenderWindow()
        interactor = render_window.GetInteractor()
        if interactor is not None:
            style = AdaptiveTrackballCameraStyle()
            style.set_renderer(self.renderer)
            interactor.SetInteractorStyle(style)
            self._adaptive_style = style
            self._interaction_controller.attach(interactor)
            self._ensure_orientation_widget(interactor)
        self.vtk_widget.Start()

    def _update_interactor_focus(
        self,
        key: tuple[str, int] | None = None,
        *,
        force: bool,
    ) -> None:
        if self._adaptive_style is None:
            return
        bounds = None
        if key is not None:
            bounds = self.scene.bounds_for_section(key)
        if bounds is None:
            bounds = self.scene.visible_bounds()
        if bounds is None:
            bounds = self.scene.scene_bounds()
        if bounds is None:
            return
        if force:
            self._adaptive_style.focus_on_bounds(bounds)
        else:
            self._adaptive_style.set_scene_bounds(bounds)

    def load_file(self, path: str) -> None:
        """Load a CGNS file and refresh the UI."""

        filename = Path(path).name
        self._show_loading(filename)
        try:
            model = self._loader.load(path)
        except Exception as exc:  # noqa: BLE001
            self._show_error(
                self.tr("Failed to read {filename}").format(filename=filename),
                str(exc),
            )
        else:
            self.load_model(model)
            self._status_bar.showMessage(
                self.tr("Load complete: {filename}").format(filename=filename),
                5000,
            )
        finally:
            self._hide_loading()

    def load_model(self, model: CgnsModel) -> None:
        self._model = model
        self.tree.populate(model)
        self.scene.load_model(model)
        self._selection_controller.sync_scene()
        self._selection_controller.clear()
        self._reset_camera()
        self._update_interactor_focus(force=True)

    def _on_section_changed(self, key: tuple[str, int] | None) -> None:
        info = self.tree.section_info(key)
        if info is None:
            self.details.clear()
            self._update_interactor_focus(force=False)
            return

        zone, section = info
        transparency = 0.0
        if key is not None:
            value = self.scene.get_section_transparency(key)
            if value is not None:
                transparency = value
        self.details.update_section(zone, section, key=key, transparency=transparency)
        self._update_interactor_focus(key, force=True)

    def _on_section_transparency_changed(self, payload: tuple[tuple[str, int], float]) -> None:
        key, transparency = payload
        self.scene.set_section_transparency(key, transparency)
        self.vtk_widget.GetRenderWindow().Render()

    def _create_actions(self) -> None:
        toolbar = QToolBar("main", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self._toolbar = toolbar

        open_action = QAction(self.tr("Open CGNS..."), self)
        open_action.triggered.connect(self._open_dialog)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        self._render_group = QActionGroup(self)
        self._render_group.setExclusive(True)

        self._surface_action = QAction(self.tr("Surface"), self)
        self._surface_action.setCheckable(True)
        self._surface_action.setChecked(True)
        self._surface_action.triggered.connect(self._set_surface_mode)
        self._render_group.addAction(self._surface_action)
        toolbar.addAction(self._surface_action)

        self._wireframe_action = QAction(self.tr("Wireframe"), self)
        self._wireframe_action.setCheckable(True)
        self._wireframe_action.triggered.connect(self._set_wireframe_mode)
        self._render_group.addAction(self._wireframe_action)
        toolbar.addAction(self._wireframe_action)

        toolbar.addSeparator()

        reset_action = QAction(self.tr("Reset Camera"), self)
        reset_action.triggered.connect(self._reset_camera)
        toolbar.addAction(reset_action)

        self._orientation_action = QAction(self.tr("Show Axes"), self)
        self._orientation_action.setCheckable(True)
        self._orientation_action.setChecked(True)
        self._orientation_action.triggered.connect(self._toggle_orientation_marker)
        toolbar.addAction(self._orientation_action)

        self._interaction_controller.register_shortcut("r", self._reset_camera)
        self._interaction_controller.register_shortcut("w", self._activate_wireframe)
        self._interaction_controller.register_shortcut("s", self._activate_surface)
        self._interaction_controller.register_shortcut("o", self._toggle_orientation_shortcut)

        toolbar.addSeparator()

        settings_action = QAction(self.tr("Settings"), self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

    def _create_settings_dialog(self) -> _SettingsDialog:
        return _SettingsDialog(self._viewer_settings, self)

    def _open_settings(self) -> None:
        dialog = self._create_settings_dialog()
        if dialog.exec() != QDialog.Accepted:
            return

        settings = dialog.selected_settings()
        self._apply_background(settings.background)
        if settings.render_style is RenderStyle.SURFACE:
            self._activate_surface()
        else:
            self._activate_wireframe()
        self._status_bar.showMessage(self.tr("Settings updated"), 3000)

    def _open_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select CGNS File"),
            str(Path.home()),
            "CGNS Files (*.cgns *.hdf5 *.h5);;All Files (*)",
        )
        if file_path:
            self.load_file(file_path)

    def _reset_camera(self) -> None:
        self.renderer.ResetCamera()
        render_window = self.vtk_widget.GetRenderWindow()
        render_window.Render()
        self._update_interactor_focus(force=False)

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
            self._viewer_settings.render_style = RenderStyle.SURFACE
            self.vtk_widget.GetRenderWindow().Render()

    def _set_wireframe_mode(self, checked: bool) -> None:
        if checked:
            self.scene.set_render_style(RenderStyle.WIREFRAME)
            self._viewer_settings.render_style = RenderStyle.WIREFRAME
            self.vtk_widget.GetRenderWindow().Render()


    def _on_tree_context_menu(self, position) -> None:  # noqa: ANN001
        item = self.tree.itemAt(position)
        if item is None or not hasattr(self.tree, "section_key"):
            return
        key = self.tree.section_key(item)  # type: ignore[attr-defined]
        if key is None:
            return

        menu = QMenu(self.tree)
        visible = self.scene.is_section_visible(key)
        if visible:
            action = menu.addAction(self.tr("Hide Section"))
            action.triggered.connect(partial(self._set_section_visibility, key, False))
        else:
            action = menu.addAction(self.tr("Show Section"))
            action.triggered.connect(partial(self._set_section_visibility, key, True))
        menu.exec(self.tree.viewport().mapToGlobal(position))


    def _set_section_visibility(self, key: tuple[str, int], visible: bool) -> None:
        changed = self.scene.set_section_visible(key, visible)
        if not changed:
            return

        current_item = self.tree.currentItem()
        current_key = None
        if hasattr(self.tree, "section_key"):
            current_key = self.tree.section_key(current_item)  # type: ignore[attr-defined]

        if current_key == key:
            if visible:
                self.scene.highlight(key)
            else:
                self.scene.highlight(None)
            self._on_section_changed(current_key)

        self._selection_controller.sync_scene()
        self.vtk_widget.GetRenderWindow().Render()
        self._update_interactor_focus(current_key if visible else None, force=False)


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

    def _apply_background(self, name: str) -> None:
        color = BACKGROUND_OPTIONS.get(name)
        if color is None:
            name = DEFAULT_BACKGROUND_NAME
            color = BACKGROUND_OPTIONS[name]
        self.renderer.SetBackground(*color)
        self._background_name = name
        self._viewer_settings.background = name
        render_window = self.vtk_widget.GetRenderWindow()
        render_window.Render()

    def _show_loading(self, filename: str) -> None:
        self._loading_active = True
        self._progress.setVisible(True)
        if self._toolbar is not None:
            self._toolbar.setEnabled(False)
        self._status_bar.showMessage(
            self.tr("Loading: {filename}").format(filename=filename)
        )
        QApplication.processEvents()

    def _hide_loading(self) -> None:
        self._progress.setVisible(False)
        if self._toolbar is not None:
            self._toolbar.setEnabled(True)
        if self._loading_active:
            self._status_bar.showMessage(self.tr("Ready"))
        self._loading_active = False

    def _show_error(self, title: str, detail: str) -> None:
        QMessageBox.critical(self, title, detail)
        self._status_bar.showMessage(self.tr("Load failed"), 5000)


class _SettingsDialog(QDialog):
    def __init__(self, settings: ViewerSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Display Settings"))
        self.setModal(True)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.background_combo = QComboBox()
        for name in BACKGROUND_OPTIONS:
            self.background_combo.addItem(self.tr(name), name)
        index = self.background_combo.findData(settings.background)
        if index < 0:
            index = 0
        self.background_combo.setCurrentIndex(index)

        self.render_combo = QComboBox()
        for style, label in RENDER_STYLE_LABELS.items():
            self.render_combo.addItem(self.tr(label), style.value)
        current_index = self.render_combo.findData(settings.render_style.value)
        if current_index >= 0:
            self.render_combo.setCurrentIndex(current_index)
        else:
            self.render_combo.setCurrentIndex(0)

        form.addRow(self.tr("Background Color"), self.background_combo)
        form.addRow(self.tr("Render Style"), self.render_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_settings(self) -> ViewerSettings:
        data = self.background_combo.currentData()
        background = data if isinstance(data, str) else DEFAULT_BACKGROUND_NAME
        style_value = self.render_combo.currentData()
        try:
            render_style = RenderStyle(style_value)
        except ValueError:
            render_style = RenderStyle.SURFACE
        return ViewerSettings(background=background, render_style=render_style)


class _ModelTreeWidget(QTreeWidget):
    """Tree widget to display CGNS zones and sections."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderLabels([self.tr("Name"), self.tr("Type"), self.tr("Cells")])
        self.setColumnWidth(0, 200)
        self._section_index: dict[tuple[str, int], QTreeWidgetItem] = {}
        self._section_data: dict[tuple[str, int], tuple[Zone, Section]] = {}

    def populate(self, model: CgnsModel) -> None:
        self.clear()
        self._section_index.clear()
        self._section_data.clear()
        for zone in model.zones:
            zone_item = QTreeWidgetItem([zone.name, self.tr("Zone"), str(zone.total_cells)])
            self.addTopLevelItem(zone_item)
            body_sections = list(zone.iter_body_sections())
            boundary_sections = list(zone.iter_boundary_sections())
            self._add_sections(zone_item, zone, body_sections, boundary=False)
            if boundary_sections:
                boundary_group = QTreeWidgetItem([self.tr("Boundary Conditions"), "", ""])
                boundary_group.setFlags(boundary_group.flags() & ~Qt.ItemIsSelectable)
                zone_item.addChild(boundary_group)
                self._add_sections(boundary_group, zone, boundary_sections, boundary=True)
        self.expandAll()

    def _add_sections(
        self,
        parent: QTreeWidgetItem,
        zone: Zone,
        sections: list[Section],
        *,
        boundary: bool,
    ) -> None:
        for section in sections:
            display_name = section.name
            type_label = section.element_type
            if boundary and section.boundary is not None:
                display_name = section.boundary.name or section.name
                location = section.boundary.grid_location
                if location:
                    type_label = self.tr("Boundary ({element}, {location})").format(
                        element=section.element_type,
                        location=location,
                    )
                else:
                    type_label = self.tr("Boundary ({element})").format(
                        element=section.element_type,
                    )
            cells = str(section.mesh.connectivity.shape[0])
            item = QTreeWidgetItem([display_name, type_label, cells])
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

    transparencyChanged = Signal(tuple)

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
        self._transparency_slider = QSlider(Qt.Horizontal)
        self._transparency_slider.setRange(0, 100)
        self._transparency_slider.setSingleStep(5)
        self._transparency_slider.setPageStep(10)
        self._transparency_slider.setEnabled(False)
        self._transparency_label = QLabel("0%")
        self._transparency_label.setMinimumWidth(40)
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)
        controls_layout.addWidget(self._transparency_slider, 1)
        controls_layout.addWidget(self._transparency_label, 0)
        self._current_key: tuple[str, int] | None = None
        self._updating_slider = False
        self._transparency_slider.valueChanged.connect(self._on_slider_value_changed)

        for label in (
            self._zone_label,
            self._name_label,
            self._type_label,
            self._cells_label,
            self._points_label,
            self._range_label,
        ):
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addRow(self.tr("Zone"), self._zone_label)
        layout.addRow(self.tr("Section"), self._name_label)
        layout.addRow(self.tr("Type"), self._type_label)
        layout.addRow(self.tr("Cells"), self._cells_label)
        layout.addRow(self.tr("Points"), self._points_label)
        layout.addRow(self.tr("Range"), self._range_label)
        layout.addRow(self.tr("Transparency"), controls)

        self.clear()

    def clear(self) -> None:
        self._set_text("-", "-", "-", "-", "-", "-")
        self._current_key = None
        self._set_transparency_value(0.0)
        self._transparency_slider.setEnabled(False)

    def update_section(
        self,
        zone: Zone,
        section: Section,
        *,
        key: tuple[str, int] | None = None,
        transparency: float | None = None,
    ) -> None:
        mesh = section.mesh
        cell_count = mesh.connectivity.shape[0]
        point_count = mesh.points.shape[0]
        display_name = section.name
        type_label = section.element_type
        if section.boundary is not None:
            display_name = section.boundary.name or section.name
            if section.boundary.grid_location:
                type_label = self.tr("Boundary ({element}, {location})").format(
                    element=section.element_type,
                    location=section.boundary.grid_location,
                )
            else:
                type_label = self.tr("Boundary ({element})").format(
                    element=section.element_type,
                )
        self._set_text(
            zone.name,
            display_name,
            type_label,
            str(cell_count),
            str(point_count),
            f"{section.range[0]} - {section.range[1]}",
        )
        self._current_key = key
        value = 0.0 if transparency is None else float(max(0.0, min(1.0, transparency)))
        self._set_transparency_value(value)
        self._transparency_slider.setEnabled(key is not None)

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
            "transparency": self._transparency_label.text(),
        }

    def _set_transparency_value(self, value: float) -> None:
        self._updating_slider = True
        try:
            self._transparency_slider.setValue(int(round(value * 100)))
        finally:
            self._updating_slider = False
        self._transparency_label.setText(f"{int(round(value * 100))}%")

    def _on_slider_value_changed(self, slider_value: int) -> None:
        if self._updating_slider or self._current_key is None:
            return
        value = max(0.0, min(1.0, slider_value / 100.0))
        self._transparency_label.setText(f"{int(round(value * 100))}%")
        self.transparencyChanged.emit((self._current_key, value))


def main(argv: list[str] | None = None) -> int:
    """Application entry point."""

    argv = list(sys.argv if argv is None else argv)
    force_offscreen = False
    filtered: list[str] = []
    for arg in argv:
        if arg == "--offscreen":
            force_offscreen = True
            continue
        filtered.append(arg)

    _prepare_environment(force_offscreen)

    app = QApplication(filtered)
    app.setApplicationName("CGNS Viewer")
    app.setOrganizationName("CGNS")
    _configure_application_font(app)
    translators = install_translators(app)
    # retain references so translators stay in scope
    setattr(app, "_cgns_gui_translators", translators)

    window = MainWindow()
    window.show()
    window.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
