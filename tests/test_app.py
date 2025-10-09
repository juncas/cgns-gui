"""Smoke tests for the CGNS GUI application."""

from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("vtkmodules.qt.QVTKRenderWindowInteractor")

from PySide6.QtWidgets import QMainWindow

from cgns_gui.app import MainWindow, SectionDetailsWidget, _ModelTreeWidget
from cgns_gui.model import CgnsModel, MeshData, Section, Zone


def _is_headless() -> bool:
    platform = os.environ.get("QT_QPA_PLATFORM", "")
    display = os.environ.get("DISPLAY")
    return platform == "offscreen" or not display


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

    details.clear()
    cleared = details.snapshot()
    assert cleared["name"] == "-"
