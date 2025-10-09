"""Tests for the SceneManager."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("vtkmodules.vtkRenderingCore")

from vtkmodules.vtkRenderingCore import vtkRenderer

from cgns_gui.model import CgnsModel, MeshData, Section, Zone
from cgns_gui.scene import SceneManager


def _sample_model() -> CgnsModel:
    mesh = MeshData(
        points=np.zeros((4, 3)),
        connectivity=np.array([[0, 1, 2, 3]]),
        cell_type="TETRA_4",
    )
    section = Section(
        id=1,
        name="Section",
        element_type="TETRA_4",
        range=(1, 1),
        mesh=mesh,
    )
    zone = Zone(name="Zone", sections=[section])
    return CgnsModel(zones=[zone])


def test_scene_manager_creates_actor():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    scene.load_model(_sample_model())

    assert renderer.GetActors().GetNumberOfItems() == 1


def test_scene_manager_clears_previous_actors():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    model = _sample_model()
    scene.load_model(model)
    scene.load_model(CgnsModel(zones=[]))

    assert renderer.GetActors().GetNumberOfItems() == 0