"""VTK scene management for CGNS models."""

from __future__ import annotations

from collections.abc import Iterable

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

class SceneManager:
    """Manage VTK actors corresponding to CGNS sections."""

    def __init__(self, renderer: vtkRenderer) -> None:
        self._renderer = renderer
        self._actors: dict[tuple[str, int], vtkActor] = {}
        self._color_palette = self._build_palette()

    def clear(self) -> None:
        for actor in self._actors.values():
            self._renderer.RemoveActor(actor)
        self._actors.clear()

    def load_model(self, model: CgnsModel) -> None:
        self.clear()
        for zone_idx, zone in enumerate(model.zones):
            for section_idx, section in enumerate(zone.sections):
                actor = self._create_actor(section)
                color = self._pick_color(zone_idx, section_idx)
                actor.GetProperty().SetColor(*color)
                actor.GetProperty().EdgeVisibilityOn()
                actor.GetProperty().SetEdgeColor(0.15, 0.15, 0.15)
                self._renderer.AddActor(actor)
                self._actors[(zone.name, section.id)] = actor
        if self._actors:
            self._renderer.ResetCamera()

    def iter_section_keys(self) -> Iterable[tuple[str, int]]:
        return self._actors.keys()

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
