"""Smoke tests for the CGNS GUI application."""

from __future__ import annotations

import os

import pytest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("vtkmodules.qt.QVTKRenderWindowInteractor")

from PySide6.QtWidgets import QMainWindow

from cgns_gui.app import MainWindow, _ModelTreeWidget
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
    """Main window should create a renderer with demo actor."""

    if _is_headless():
        pytest.skip("Headless environment cannot validate VTK widget")

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.renderer.GetActors().GetNumberOfItems() == 1


def test_model_tree_populates_sections(qtbot):
    tree = _ModelTreeWidget()
    qtbot.addWidget(tree)

    mesh = MeshData(points=np.zeros((4, 3)), connectivity=np.array([[0, 1, 2, 3]]), cell_type="TETRA_4")
    section = Section(id=1, name="Section#1", element_type="TETRA_4", range=(1, 1), mesh=mesh)
    model = CgnsModel(zones=[Zone(name="Zone#1", sections=[section])])

    tree.populate(model)

    assert tree.topLevelItemCount() == 1
    zone_item = tree.topLevelItem(0)
    assert zone_item.text(0) == "Zone#1"
    assert zone_item.childCount() == 1
    section_item = zone_item.child(0)
    assert section_item.text(0) == "Section#1"
