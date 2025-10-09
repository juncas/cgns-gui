"""CGNS file loader built on top of h5py."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import h5py
import numpy as np

from .model import CgnsModel, MeshData, Section, Zone

_SUPPORTED_ELEMENT_SIZES: dict[str, int] = {
    "BAR_2": 2,
    "TRI_3": 3,
    "QUAD_4": 4,
    "TETRA_4": 4,
    "PYRA_5": 5,
    "PENTA_6": 6,
    "HEXA_8": 8,
}

_ELEMENT_TYPE_BY_CODE: dict[int, str] = {
    2: "BAR_2",
    5: "TRI_3",
    7: "QUAD_4",
    10: "TETRA_4",
    12: "PYRA_5",
    13: "PENTA_6",
    14: "HEXA_8",
}


class CgnsLoader:
    """Parse a subset of CGNS/HDF5 files."""

    def __init__(self) -> None:
        self._path: Path | None = None

    def load(self, path: str | Path) -> CgnsModel:
        path = Path(path)
        if not path.exists():
            msg = f"CGNS file not found: {path}"
            raise FileNotFoundError(msg)
        self._path = path

        with h5py.File(path, "r") as handle:
            zones: list[Zone] = []
            for _, base_group in self._iter_children(handle, ("Base_t", "CGNSBase_t")):
                for zone_name, zone_group in self._iter_children(base_group, "Zone_t"):
                    zones.append(self._read_zone(zone_name, zone_group))
        return CgnsModel(zones=zones)

    def _read_zone(self, name: str, group: h5py.Group) -> Zone:
        sections = []
        points = self._read_points(group)
        for section_idx, (section_name, section_group) in enumerate(
            self._iter_children(group, "Elements_t"),
            start=1,
        ):
            mesh = self._read_section_mesh(section_group, points)
            sections.append(
                Section(
                    id=section_idx,
                    name=section_name,
                    element_type=mesh.cell_type,
                    range=(1, mesh.connectivity.shape[0]),
                    mesh=mesh,
                )
            )
        return Zone(name=name, sections=sections)

    def _read_points(self, group: h5py.Group) -> np.ndarray:
        coords_group = None
        for candidate_name, candidate in self._iter_children(group, "GridCoordinates_t"):
            coords_group = candidate
            break
        if coords_group is None:
            raise ValueError(f"Zone {group.name} missing GridCoordinates")

        coord_arrays = []
        for axis in ("X", "Y", "Z"):
            node = coords_group.get(f"Coordinate{axis}")
            if node is None:
                raise ValueError(f"Missing Coordinate{axis} in {coords_group.name}")
            dataset = self._resolve_data_array(node)
            coord_arrays.append(np.asarray(dataset, dtype=float).reshape(-1))
        return np.column_stack(coord_arrays)

    def _read_section_mesh(self, section_group: h5py.Group, points: np.ndarray) -> MeshData:
        element_type_value = self._infer_element_type(section_group)

        conn_node = section_group.get("ElementConnectivity")
        if conn_node is None:
            raise ValueError(f"Section {section_group.name} missing ElementConnectivity")
        conn_dataset = self._resolve_data_array(conn_node)

        element_size = _SUPPORTED_ELEMENT_SIZES.get(element_type_value)
        if element_size is None:
            raise ValueError(f"Unsupported element type: {element_type_value}")

        connectivity_raw = np.asarray(conn_dataset, dtype=np.int64).reshape(-1, element_size)
        # CGNS uses 1-based indexing for connectivity
        connectivity = connectivity_raw - 1
        return MeshData(points=points, connectivity=connectivity, cell_type=element_type_value)

    @staticmethod
    def _iter_children(
        group: h5py.Group,
        labels: str | tuple[str, ...],
    ) -> Iterator[tuple[str, h5py.Group]]:
        if isinstance(labels, str):
            wanted = {labels}
        else:
            wanted = set(labels)

        for name, child in group.items():
            if isinstance(child, h5py.Group):
                child_label = child.attrs.get("label")
                if isinstance(child_label, bytes):
                    child_label = child_label.decode("utf-8")
                if child_label in wanted:
                    yield name, child

    @staticmethod
    def _decode_dataset(dataset: h5py.Dataset) -> str:
        value = dataset[()]
        if isinstance(value, bytes):
            return value.decode("utf-8")
        if isinstance(value, np.bytes_):
            return value.astype(str)
        if isinstance(value, np.ndarray) and value.ndim == 0:
            return str(value.item())
        return str(value)

    def _infer_element_type(self, section_group: h5py.Group) -> str:
        element_node = section_group.get("ElementType")
        if element_node is not None:
            dataset = self._resolve_data_array(element_node)
            return self._decode_dataset(dataset)

        type_node = section_group.get(" data")
        if isinstance(type_node, h5py.Dataset) and type_node.size:
            code = int(type_node[0])
            element_type = _ELEMENT_TYPE_BY_CODE.get(code)
            if element_type in _SUPPORTED_ELEMENT_SIZES:
                return element_type

        name_attr = section_group.attrs.get("name")
        if isinstance(name_attr, bytes):
            name_attr = name_attr.decode("utf-8", errors="ignore")
        if isinstance(name_attr, str):
            upper = name_attr.upper()
            for element_type in _SUPPORTED_ELEMENT_SIZES:
                token = element_type.split("_")[0]
                if token in upper:
                    return element_type

        raise ValueError(f"Unable to determine element type for {section_group.name}")

    @staticmethod
    def _resolve_data_array(node: h5py.Dataset | h5py.Group) -> h5py.Dataset:
        if isinstance(node, h5py.Dataset):
            return node
        if isinstance(node, h5py.Group):
            dataset = node.get(" data")
            if isinstance(dataset, h5py.Dataset):
                return dataset
        raise ValueError(f"Unsupported CGNS data array layout at {node}")
