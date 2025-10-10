"""VTK scene management for CGNS models."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.vtkCommonCore import vtkIdList, vtkPoints
from vtkmodules.vtkCommonDataModel import (
    VTK_HEXAHEDRON,
    VTK_LINE,
    VTK_PYRAMID,
    VTK_QUAD,
    VTK_TETRA,
    VTK_TRIANGLE,
    VTK_WEDGE,
    vtkCellArray,
    vtkUnstructuredGrid,
)
from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper, vtkRenderer

from .model import CgnsModel, MeshData, Section

_ELEMENT_TYPE_TO_VTK = {
    "BAR_2": VTK_LINE,
    "TRI_3": VTK_TRIANGLE,
    "QUAD_4": VTK_QUAD,
    "TETRA_4": VTK_TETRA,
    "PYRA_5": VTK_PYRAMID,
    "PENTA_6": VTK_WEDGE,
    "HEXA_8": VTK_HEXAHEDRON,
}


class RenderStyle(str, Enum):
    """Rendering modes supported by the scene manager."""

    SURFACE = "surface"
    WIREFRAME = "wireframe"


class SceneManager:
    """Manage VTK actors corresponding to CGNS sections."""

    def __init__(self, renderer: vtkRenderer) -> None:
        self._renderer = renderer
        self._actors: dict[tuple[str, int], vtkActor] = {}
        self._actor_lookup: dict[vtkActor, tuple[str, int]] = {}
        self._base_colors: dict[tuple[str, int], tuple[float, float, float]] = {}
        self._section_transparency: dict[tuple[str, int], float] = {}
        self._section_visibility: dict[tuple[str, int], bool] = {}
        self._highlighted: tuple[str, int] | None = None
        self._color_palette = self._build_palette()
        self._style = RenderStyle.SURFACE

    def clear(self) -> None:
        for actor in self._actors.values():
            self._renderer.RemoveActor(actor)
        self._actors.clear()
        self._actor_lookup.clear()
        self._base_colors.clear()
        self._section_transparency.clear()
        self._section_visibility.clear()
        self._highlighted = None

    @property
    def renderer(self) -> vtkRenderer:
        return self._renderer

    def visible_bounds(self) -> tuple[float, float, float, float, float, float] | None:
        bounds: list[float] | None = None
        for actor in self._actors.values():
            if actor.GetVisibility() != 1:
                continue
            actor_bounds = actor.GetBounds()
            if actor_bounds is None or actor_bounds[0] > actor_bounds[1]:
                continue
            if bounds is None:
                bounds = list(actor_bounds)
            else:
                bounds[0] = min(bounds[0], actor_bounds[0])
                bounds[1] = max(bounds[1], actor_bounds[1])
                bounds[2] = min(bounds[2], actor_bounds[2])
                bounds[3] = max(bounds[3], actor_bounds[3])
                bounds[4] = min(bounds[4], actor_bounds[4])
                bounds[5] = max(bounds[5], actor_bounds[5])
        return tuple(bounds) if bounds is not None else None

    def scene_bounds(self) -> tuple[float, float, float, float, float, float] | None:
        bounds: list[float] | None = None
        for actor in self._actors.values():
            actor_bounds = actor.GetBounds()
            if actor_bounds is None or actor_bounds[0] > actor_bounds[1]:
                continue
            if bounds is None:
                bounds = list(actor_bounds)
            else:
                bounds[0] = min(bounds[0], actor_bounds[0])
                bounds[1] = max(bounds[1], actor_bounds[1])
                bounds[2] = min(bounds[2], actor_bounds[2])
                bounds[3] = max(bounds[3], actor_bounds[3])
                bounds[4] = min(bounds[4], actor_bounds[4])
                bounds[5] = max(bounds[5], actor_bounds[5])
        return tuple(bounds) if bounds is not None else None

    def bounds_for_section(
        self,
        key: tuple[str, int],
    ) -> tuple[float, float, float, float, float, float] | None:
        actor = self._actors.get(key)
        if actor is None or actor.GetVisibility() != 1:
            return None
        bounds = actor.GetBounds()
        if bounds is None or bounds[0] > bounds[1]:
            return None
        return bounds

    def load_model(self, model: CgnsModel) -> None:
        self.clear()
        for zone_idx, zone in enumerate(model.zones):
            for section_idx, section in enumerate(zone.sections):
                actor = self._create_actor(section)
                color = self._pick_color(zone_idx, section_idx)
                actor.GetProperty().SetColor(*color)
                actor.GetProperty().EdgeVisibilityOn()
                actor.GetProperty().SetEdgeColor(0.15, 0.15, 0.15)
                self._apply_style(actor)
                self._renderer.AddActor(actor)
                key = (zone.name, section.id)
                transparency = self._default_transparency(section.element_type)
                visible = self._default_visibility(section.element_type)
                self._actors[key] = actor
                self._actor_lookup[actor] = key
                self._base_colors[key] = color
                self._section_transparency[key] = transparency
                self._section_visibility[key] = visible
                actor.SetVisibility(1 if visible else 0)
                actor.SetPickable(1 if visible else 0)
                self._apply_base_style(key, actor, color)
        if self._actors:
            self._renderer.ResetCamera()

    def iter_section_keys(self) -> Iterable[tuple[str, int]]:
        return self._actors.keys()

    def iter_actors(self) -> Iterable[vtkActor]:
        return self._actors.values()

    def iter_actor_items(self) -> Iterable[tuple[tuple[str, int], vtkActor]]:
        return self._actors.items()

    def get_actor(self, key: tuple[str, int]) -> vtkActor | None:
        return self._actors.get(key)

    def get_key_for_actor(self, actor: vtkActor | None) -> tuple[str, int] | None:
        if actor is None:
            return None
        return self._actor_lookup.get(actor)

    def _create_actor(self, section: Section) -> vtkActor:
        mesh = section.mesh
        dataset = self._build_unstructured_grid(mesh)

        mapper = vtkDataSetMapper()
        mapper.SetInputData(dataset)

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetLineWidth(1.0)
        return actor

    def _build_unstructured_grid(self, mesh: MeshData) -> vtkUnstructuredGrid:
        vtk_points = vtkPoints()
        vtk_points.SetData(numpy_to_vtk(mesh.points, deep=True))

        cell_array = vtkCellArray()
        vtk_type = _ELEMENT_TYPE_TO_VTK.get(mesh.cell_type)
        if vtk_type is None:
            msg = f"Unsupported cell type: {mesh.cell_type}"
            raise ValueError(msg)

        for cell in mesh.connectivity:
            ids = vtkIdList()
            for idx in cell:
                ids.InsertNextId(int(idx))
            cell_array.InsertNextCell(ids)

        grid = vtkUnstructuredGrid()
        grid.SetPoints(vtk_points)
        grid.SetCells(vtk_type, cell_array)
        return grid

    def _pick_color(self, zone_idx: int, section_idx: int) -> tuple[float, float, float]:
        palette = self._color_palette
        base_index = (zone_idx * len(palette) + section_idx) % len(palette)
        return palette[base_index]

    def set_render_style(self, style: RenderStyle) -> None:
        if style == self._style:
            return

        self._style = style
        for actor in self._actors.values():
            self._apply_style(actor)

    def get_render_style(self) -> RenderStyle:
        return self._style

    def highlight(self, key: tuple[str, int] | None) -> None:
        if key is not None and key not in self._actors:
            key = None

        if key is not None and not self.is_section_visible(key):
            key = None

        if key == self._highlighted and key is not None:
            return

        self._highlighted = key
        for section_key, actor in self._actors.items():
            base_color = self._base_colors.get(section_key)
            if section_key == key:
                self._apply_highlight(section_key, actor, base_color)
            else:
                self._apply_base_style(section_key, actor, base_color)

    def _apply_style(self, actor: vtkActor) -> None:
        prop = actor.GetProperty()
        if self._style is RenderStyle.WIREFRAME:
            prop.SetRepresentationToWireframe()
        else:
            prop.SetRepresentationToSurface()

    def _apply_highlight(
        self,
        key: tuple[str, int],
        actor: vtkActor,
        base_color: tuple[float, float, float] | None,
    ) -> None:
        prop = actor.GetProperty()
        color = base_color or prop.GetColor()
        highlight = tuple(min(component + 0.25, 1.0) for component in color)
        prop.SetColor(*highlight)
        prop.SetLineWidth(2.0)
        prop.EdgeVisibilityOn()
        prop.SetOpacity(self._opacity_for_key(key))

    def _apply_base_style(
        self,
        key: tuple[str, int],
        actor: vtkActor,
        base_color: tuple[float, float, float] | None,
    ) -> None:
        prop = actor.GetProperty()
        if base_color is not None:
            prop.SetColor(*base_color)
        prop.SetLineWidth(1.0)
        prop.EdgeVisibilityOn()
        prop.SetOpacity(self._opacity_for_key(key))

    def set_section_transparency(self, key: tuple[str, int], value: float) -> None:
        if key not in self._actors:
            return
        clamped = float(max(0.0, min(1.0, value)))
        self._section_transparency[key] = clamped
        base_color = self._base_colors.get(key)
        actor = self._actors[key]
        if self._highlighted == key:
            self._apply_highlight(key, actor, base_color)
        else:
            self._apply_base_style(key, actor, base_color)

    def get_section_transparency(self, key: tuple[str, int]) -> float | None:
        return self._section_transparency.get(key)

    def set_section_visible(self, key: tuple[str, int], visible: bool) -> bool:
        if key not in self._actors:
            return False
        actor = self._actors[key]
        current = self._section_visibility.get(key, True)
        if current == visible:
            return False
        self._section_visibility[key] = visible
        actor.SetVisibility(1 if visible else 0)
        actor.SetPickable(1 if visible else 0)
        base_color = self._base_colors.get(key)
        if not visible and self._highlighted == key:
            self._highlighted = None
        if visible:
            if self._highlighted == key:
                self._apply_highlight(key, actor, base_color)
            else:
                self._apply_base_style(key, actor, base_color)
        return True

    def is_section_visible(self, key: tuple[str, int]) -> bool:
        return self._section_visibility.get(key, True)

    def _opacity_for_key(self, key: tuple[str, int]) -> float:
        transparency = self._section_transparency.get(key, 0.0)
        return max(0.0, min(1.0, 1.0 - transparency))

    @staticmethod
    def _default_transparency(element_type: str) -> float:
        volume_types = {
            "TETRA_4",
            "PYRA_5",
            "PENTA_6",
            "HEXA_8",
        }
        surface_types = {
            "TRI_3",
            "QUAD_4",
        }
        if element_type in volume_types:
            return 0.0
        if element_type in surface_types:
            return 0.0
        # Treat lines and unknown types as opaque by default
        return 0.0

    @staticmethod
    def _default_visibility(element_type: str) -> bool:
        volume_types = {
            "TETRA_4",
            "PYRA_5",
            "PENTA_6",
            "HEXA_8",
        }
        return element_type not in volume_types

    @staticmethod
    def _build_palette():
        return [
            (0.2, 0.6, 0.9),
            (0.9, 0.5, 0.2),
            (0.2, 0.8, 0.5),
            (0.8, 0.3, 0.6),
            (0.7, 0.7, 0.2),
            (0.4, 0.4, 0.8),
        ]
