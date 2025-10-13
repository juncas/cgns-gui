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
        points=np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        ),
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


def test_scene_manager_default_visibility():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

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

    volume_section = Section(
        id=1,
        name="Volume",
        element_type="TETRA_4",
        range=(1, 1),
        mesh=volume_mesh,
    )
    surface_section = Section(
        id=2,
        name="Surface",
        element_type="TRI_3",
        range=(1, 1),
        mesh=surface_mesh,
    )
    zone = Zone(name="Zone", sections=[volume_section, surface_section])

    scene.load_model(CgnsModel(zones=[zone]))

    volume_actor = scene.get_actor(("Zone", 1))
    surface_actor = scene.get_actor(("Zone", 2))

    assert volume_actor is not None
    assert surface_actor is not None
    assert scene.is_section_visible(("Zone", 1)) is False
    assert scene.is_section_visible(("Zone", 2)) is True
    assert volume_actor.GetVisibility() == 0
    assert surface_actor.GetVisibility() == 1
    assert surface_actor.GetProperty().GetOpacity() == pytest.approx(1.0)


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

    scene.set_section_visible(key, True)

    scene.highlight(key)
    highlight_color = actor.GetProperty().GetColor()
    assert highlight_color == pytest.approx((0.45, 0.85, 1.0))
    assert actor.GetProperty().GetLineWidth() == pytest.approx(2.0)

    scene.highlight(None)
    base_color = actor.GetProperty().GetColor()
    assert base_color == pytest.approx((0.2, 0.6, 0.9))
    assert actor.GetProperty().GetLineWidth() == pytest.approx(1.0)


def test_scene_manager_allows_transparency_updates():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    scene.load_model(_sample_model())

    key = ("Zone", 1)
    actor = scene.get_actor(key)
    assert actor is not None

    scene.set_section_visible(key, True)
    scene.set_section_transparency(key, 0.3)
    assert scene.get_section_transparency(key) == pytest.approx(0.3)
    assert actor.GetProperty().GetOpacity() == pytest.approx(0.7)


def test_scene_manager_toggle_visibility():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    scene.load_model(_sample_model())

    key = ("Zone", 1)
    actor = scene.get_actor(key)
    assert actor is not None

    changed = scene.set_section_visible(key, True)
    assert changed is True
    assert scene.is_section_visible(key) is True
    assert actor.GetVisibility() == 1

    scene.highlight(key)
    changed = scene.set_section_visible(key, False)
    assert changed is True
    assert scene.is_section_visible(key) is False
    assert actor.GetVisibility() == 0
    assert scene.get_key_for_actor(actor) == key


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


def test_scene_manager_bounds_respect_visibility():
    renderer = vtkRenderer()
    scene = SceneManager(renderer)

    surface_mesh = MeshData(
        points=np.array(
            [
                [0.0, 0.0, 0.0],
                [2.0, 0.0, 0.0],
                [0.0, 2.0, 0.0],
            ]
        ),
        connectivity=np.array([[0, 1, 2]]),
        cell_type="TRI_3",
    )
    section = Section(
        id=10,
        name="Surface",
        element_type="TRI_3",
        range=(1, 1),
        mesh=surface_mesh,
    )
    zone = Zone(name="Zone", sections=[section])

    scene.load_model(CgnsModel(zones=[zone]))
    key = ("Zone", 10)
    scene.set_section_visible(key, True)

    visible_bounds = scene.visible_bounds()
    assert visible_bounds is not None
    scene_bounds = scene.scene_bounds()
    assert scene_bounds == visible_bounds

    scene.set_section_visible(key, False)
    assert scene.visible_bounds() is None
    assert scene.scene_bounds() == scene_bounds
