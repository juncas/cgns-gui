"""Core data structures for CGNS GUI."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class BoundaryInfo:
    """Metadata describing a boundary condition associated with a section."""

    name: str
    grid_location: str | None = None


@dataclass(slots=True)
class MeshData:
    """Point and connectivity information for a mesh fragment."""

    points: np.ndarray
    connectivity: np.ndarray
    cell_type: str

    def __post_init__(self) -> None:
        if self.points.ndim != 2 or self.points.shape[1] != 3:
            msg = "points must be a (N, 3) array"
            raise ValueError(msg)
        if self.connectivity.ndim != 2:
            msg = "connectivity must be a (M, K) array"
            raise ValueError(msg)
        if not isinstance(self.cell_type, str):
            msg = "cell_type must be a string"
            raise TypeError(msg)


@dataclass(slots=True)
class Section:
    """Section definition inside a zone."""

    id: int
    name: str
    element_type: str
    range: tuple[int, int]
    mesh: MeshData
    boundary: BoundaryInfo | None = None


@dataclass(slots=True)
class Zone:
    """Zone grouping multiple sections."""

    name: str
    sections: list[Section] = field(default_factory=list)

    @property
    def total_cells(self) -> int:
        return int(sum(section.mesh.connectivity.shape[0] for section in self.sections))

    @property
    def total_points(self) -> int:
        if not self.sections:
            return 0
        return int(max(section.mesh.points.shape[0] for section in self.sections))

    def iter_sections(self) -> Iterable[Section]:
        return iter(self.sections)

    def iter_body_sections(self) -> Iterable[Section]:
        return (section for section in self.sections if section.boundary is None)

    def iter_boundary_sections(self) -> Iterable[Section]:
        return (section for section in self.sections if section.boundary is not None)


@dataclass(slots=True)
class CgnsModel:
    """Root container for a CGNS dataset."""

    zones: list[Zone] = field(default_factory=list)

    def find_section(self, zone_name: str, section_id: int) -> Section | None:
        for zone in self.zones:
            if zone.name != zone_name:
                continue
            for section in zone.sections:
                if section.id == section_id:
                    return section
        return None
