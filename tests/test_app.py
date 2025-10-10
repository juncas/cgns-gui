"""Smoke tests for the CGNS GUI application."""

from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("vtkmodules.qt.QVTKRenderWindowInteractor")

from PySide6.QtWidgets import QDialog, QMainWindow, QToolBar

from cgns_gui.app import (
    MainWindow,
    SectionDetailsWidget,
    _missing_xcb_libs,
    _ModelTreeWidget,
    _prepare_environment,
    _should_force_offscreen,
)
from cgns_gui.model import BoundaryInfo, CgnsModel, MeshData, Section, Zone
from cgns_gui.scene import RenderStyle


def _is_headless() -> bool:
    platform = os.environ.get("QT_QPA_PLATFORM", "")
    display = os.environ.get("DISPLAY")
    return platform == "offscreen" or not display


def test_should_force_offscreen_without_gl():
    env: dict[str, str] = {}
    assert _should_force_offscreen(env, find_gl=lambda name: None, path_exists=lambda path: False)


def test_should_force_offscreen_when_driver_available(tmp_path):
    driver_dir = tmp_path / "dri"
    driver_dir.mkdir()
    (driver_dir / "mock_dri.so").write_text("")

    env: dict[str, str] = {"LIBGL_DRIVERS_PATH": str(driver_dir), "DISPLAY": ":0"}
    assert _should_force_offscreen(env, find_gl=lambda name: "libGL.so.1") is False


def test_should_force_offscreen_when_headless(tmp_path):
    driver_dir = tmp_path / "dri"
    driver_dir.mkdir()
    (driver_dir / "mock_dri.so").write_text("")

    env: dict[str, str] = {"LIBGL_DRIVERS_PATH": str(driver_dir)}
    assert _should_force_offscreen(
        env,
        find_gl=lambda name: "libGL.so.1",
        is_headless=True,
    )


def test_missing_xcb_libs_reports_required_names(monkeypatch):
    monkeypatch.setattr("ctypes.util.find_library", lambda name: None)
    missing = _missing_xcb_libs(find_lib=lambda name: None)
    assert missing


def test_main_window_class_registered():
    """MainWindow should be a proper Qt window subclass."""

    assert issubclass(MainWindow, QMainWindow)


@pytest.mark.qt_no_exception_capture
def test_main_window_initializes(qtbot):
    """Main window should initialise renderer without actors before loading data."""

    if _is_headless():
        pytest.skip("Headless environment cannot validate VTK widget")

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.renderer.GetActors().GetNumberOfItems() == 0


def test_model_tree_populates_sections(qtbot):
    tree = _ModelTreeWidget()
    qtbot.addWidget(tree)

    mesh = MeshData(
        points=np.zeros((4, 3)),
        connectivity=np.array([[0, 1, 2, 3]]),
        cell_type="TETRA_4",
    )
    section = Section(id=1, name="Section#1", element_type="TETRA_4", range=(1, 1), mesh=mesh)
    model = CgnsModel(zones=[Zone(name="Zone#1", sections=[section])])

    tree.populate(model)

    assert tree.topLevelItemCount() == 1
    zone_item = tree.topLevelItem(0)
    assert zone_item.text(0) == "Zone#1"
    assert zone_item.childCount() == 1
    section_item = zone_item.child(0)
    assert section_item.text(0) == "Section#1"

    key = tree.section_key(section_item)
    assert key == ("Zone#1", 1)
    info = tree.section_info(key)
    assert info is not None
    zone_obj, section_obj = info
    assert zone_obj.name == "Zone#1"
    assert section_obj is section


def test_model_tree_groups_boundary_sections(qtbot):
    tree = _ModelTreeWidget()
    qtbot.addWidget(tree)

    volume_mesh = MeshData(
        points=np.zeros((4, 3)),
        connectivity=np.array([[0, 1, 2, 3]]),
        cell_type="TETRA_4",
    )
    surface_mesh = MeshData(
        points=np.zeros((3, 3)),
        connectivity=np.array([[0, 1, 2]]),
        cell_type="TRI_3",
    )
    volume = Section(id=1, name="Volume", element_type="TETRA_4", range=(1, 1), mesh=volume_mesh)
    boundary = Section(
        id=2,
        name="Inlet",
        element_type="TRI_3",
        range=(1, 1),
        mesh=surface_mesh,
        boundary=BoundaryInfo(name="Inlet", grid_location="FaceCenter"),
    )
    zone = Zone(name="Zone#1", sections=[volume, boundary])

    tree.populate(CgnsModel(zones=[zone]))

    zone_item = tree.topLevelItem(0)
    assert zone_item.childCount() == 2
    volume_item = zone_item.child(0)
    assert volume_item.text(0) == "Volume"
    boundary_group = zone_item.child(1)
    assert boundary_group.text(0) == "Boundary Conditions"
    assert boundary_group.childCount() == 1
    boundary_item = boundary_group.child(0)
    assert boundary_item.text(0) == "Inlet"
    assert "Boundary" in boundary_item.text(1)

    key = tree.section_key(boundary_item)
    assert key == ("Zone#1", 2)


def test_section_details_widget_updates(qtbot):
    details = SectionDetailsWidget()
    qtbot.addWidget(details)

    mesh = MeshData(
        points=np.zeros((4, 3)),
        connectivity=np.array([[0, 1, 2]]),
        cell_type="TRI_3",
    )
    section = Section(id=5, name="Wing Surface", element_type="TRI_3", range=(1, 1), mesh=mesh)
    zone = Zone(name="Wing", sections=[section])

    details.update_section(zone, section)
    snapshot = details.snapshot()
    assert snapshot["zone"] == "Wing"
    assert snapshot["name"] == "Wing Surface"
    assert snapshot["type"] == "TRI_3"
    assert snapshot["cells"] == "1"
    assert snapshot["points"] == "4"
    assert snapshot["range"] == "1 - 1"
    assert snapshot["transparency"] == "0%"

    details.clear()
    cleared = details.snapshot()
    assert cleared["name"] == "-"
    assert cleared["transparency"] == "0%"


def test_section_details_widget_shows_boundary_info(qtbot):
    details = SectionDetailsWidget()
    qtbot.addWidget(details)

    mesh = MeshData(
        points=np.zeros((3, 3)),
        connectivity=np.array([[0, 1, 2]]),
        cell_type="TRI_3",
    )
    section = Section(
        id=7,
        name="Inlet",
        element_type="TRI_3",
        range=(1, 1),
        mesh=mesh,
        boundary=BoundaryInfo(name="Inlet", grid_location="FaceCenter"),
    )
    zone = Zone(name="Wing", sections=[section])

    details.update_section(zone, section)
    snapshot = details.snapshot()
    assert snapshot["name"] == "Inlet"
    assert "Boundary" in snapshot["type"]
    assert "FaceCenter" in snapshot["type"]


def test_section_details_widget_emits_transparency_signal(qtbot):
    details = SectionDetailsWidget()
    qtbot.addWidget(details)

    mesh = MeshData(
        points=np.zeros((4, 3)),
        connectivity=np.array([[0, 1, 2]]),
        cell_type="TRI_3",
    )
    section = Section(id=5, name="Wing Surface", element_type="TRI_3", range=(1, 1), mesh=mesh)
    zone = Zone(name="Wing", sections=[section])
    key = ("Wing", 5)

    details.update_section(zone, section, key=key, transparency=0.2)

    with qtbot.waitSignal(details.transparencyChanged, timeout=1000) as blocker:
        slider = getattr(details, "_transparency_slider")
        slider.setValue(80)

    emitted_key, value = blocker.args[0]
    assert emitted_key == key
    assert value == pytest.approx(0.8)


@pytest.mark.qt_no_exception_capture
def test_main_window_toolbar_camera_actions(qtbot):
    if _is_headless():
        pytest.skip("Headless environment cannot validate VTK widget")

    window = MainWindow()
    qtbot.addWidget(window)

    toolbars = window.findChildren(QToolBar)
    assert toolbars, "Main toolbar should be present"
    actions = {action.text(): action for action in toolbars[0].actions()}

    assert "Reset Camera" in actions
    assert "Show Axes" in actions

    actions["Show Axes"].trigger()
    actions["Show Axes"].trigger()


@pytest.mark.qt_no_exception_capture
def test_open_settings_updates_preferences(qtbot, monkeypatch):
    if _is_headless():
        pytest.skip("Headless environment cannot validate VTK widget")

    window = MainWindow()
    qtbot.addWidget(window)

    dialog = window._create_settings_dialog()
    qtbot.addWidget(dialog)
    bg_index = dialog.background_combo.findData("Light Gray")
    if bg_index >= 0:
        dialog.background_combo.setCurrentIndex(bg_index)
    index = dialog.render_combo.findText("Wireframe")
    dialog.render_combo.setCurrentIndex(index)

    monkeypatch.setattr(window, "_create_settings_dialog", lambda: dialog)
    monkeypatch.setattr(dialog, "exec", lambda: QDialog.Accepted)

    window._open_settings()

    assert window._background_name == "Light Gray"
    assert window.scene.get_render_style() is RenderStyle.WIREFRAME
    assert window._wireframe_action is not None and window._wireframe_action.isChecked()


@pytest.mark.qt_no_exception_capture
def test_toggle_section_visibility(qtbot):
    if _is_headless():
        pytest.skip("Headless environment cannot validate VTK widget")

    window = MainWindow()
    qtbot.addWidget(window)

    mesh = MeshData(
        points=np.zeros((4, 3)),
        connectivity=np.array([[0, 1, 2, 3]]),
        cell_type="TETRA_4",
    )
    section = Section(id=1, name="Vol", element_type="TETRA_4", range=(1, 1), mesh=mesh)
    model = CgnsModel(zones=[Zone(name="Zone", sections=[section])])

    window.load_model(model)
    key = ("Zone", 1)

    assert window.scene.is_section_visible(key) is False

    window._set_section_visibility(key, True)
    assert window.scene.is_section_visible(key) is True

    window._set_section_visibility(key, False)
    assert window.scene.is_section_visible(key) is False


def test_prepare_environment_force_offscreen():
    fake_env: dict[str, str] = {}
    _prepare_environment(True, fake_env)
    assert fake_env["QT_QPA_PLATFORM"] == "offscreen"
    assert fake_env["VTK_DEFAULT_RENDER_WINDOW_OFFSCREEN"] == "1"


def test_prepare_environment_headless_default():
    fake_env: dict[str, str] = {}
    _prepare_environment(False, fake_env)
    assert fake_env["QT_QPA_PLATFORM"] == "offscreen"
