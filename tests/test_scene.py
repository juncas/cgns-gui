"""Tests for the SceneManager."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("vtkmodules.vtkRenderingCore")

from vtkmodules.vtkRenderingCore import vtkRenderer

from cgns_gui.model import CgnsModel, MeshData, Section, Zone
from cgns_gui.scene import RenderStyle, SceneManager


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


def test_scene_manager_default_render_style():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    assert scene.get_render_style() is RenderStyle.SURFACE


def test_scene_manager_switches_render_style():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    scene.load_model(_sample_model())
    scene.set_render_style(RenderStyle.WIREFRAME)

    actors = renderer.GetActors()
    actors.InitTraversal()
    actor = actors.GetNextActor()

    assert actor.GetProperty().GetRepresentationAsString() == "Wireframe"

    scene.set_render_style(RenderStyle.SURFACE)
    actors.InitTraversal()
    actor = actors.GetNextActor()

    assert actor.GetProperty().GetRepresentationAsString() == "Surface"


def test_scene_manager_highlight_cycle():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    scene.load_model(_sample_model())

    key = ("Zone", 1)
    actor = scene.get_actor(key)
    assert actor is not None

    scene.highlight(key)
    highlight_color = actor.GetProperty().GetColor()
    assert highlight_color == pytest.approx((0.45, 0.85, 1.0))
    assert actor.GetProperty().GetLineWidth() == pytest.approx(2.0)

    scene.highlight(None)
    base_color = actor.GetProperty().GetColor()
    assert base_color == pytest.approx((0.2, 0.6, 0.9))
    assert actor.GetProperty().GetLineWidth() == pytest.approx(1.0)


def test_scene_manager_key_lookup():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    scene.load_model(_sample_model())

    key = ("Zone", 1)
    actor = scene.get_actor(key)
    assert actor is not None
    assert scene.get_key_for_actor(actor) == key
    assert scene.get_key_for_actor(None) is None


def test_scene_manager_clears_previous_actors():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    model = _sample_model()
    scene.load_model(model)
    scene.load_model(CgnsModel(zones=[]))

    assert renderer.GetActors().GetNumberOfItems() == 0