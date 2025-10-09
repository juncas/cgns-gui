"""CGNS file loader built on top of h5py."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import h5py
import numpy as np

from .model import BoundaryInfo, CgnsModel, MeshData, Section, Zone

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
                    zones.append(self._read_zone(zone_name, zone_group, base_group))
        return CgnsModel(zones=zones)

    def _read_zone(self, name: str, group: h5py.Group, base_group: h5py.Group) -> Zone:
        sections: list[Section] = []
        section_lookup: dict[str, list[Section]] = {}
        points = self._read_points(group)
        for section_idx, (section_name, section_group) in enumerate(
            self._iter_children(group, "Elements_t"),
            start=1,
        ):
            mesh = self._read_section_mesh(section_group, points)
            clean_name = self._clean_name(section_name)
            sections.append(
                Section(
                    id=section_idx,
                    name=clean_name or section_name,
                    element_type=mesh.cell_type,
                    range=(1, mesh.connectivity.shape[0]),
                    mesh=mesh,
                )
            )
            key = self._normalize_key(clean_name or section_name)
            if key:
                section_lookup.setdefault(key, []).append(sections[-1])

        self._attach_boundary_metadata(group, base_group, section_lookup)

        for new_id, section in enumerate(sections, start=1):
            section.id = new_id
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

        name_candidate = self._extract_name_token(section_group)
        if name_candidate is not None:
            return name_candidate

        type_node = section_group.get(" data")
        if isinstance(type_node, h5py.Dataset) and type_node.size:
            code = int(type_node[0])
            element_type = _ELEMENT_TYPE_BY_CODE.get(code)
            if element_type in _SUPPORTED_ELEMENT_SIZES:
                return element_type

        if name_candidate is None:
            name_candidate = self._extract_name_token(section_group, use_path=True)
            if name_candidate is not None:
                return name_candidate

        raise ValueError(f"Unable to determine element type for {section_group.name}")

    def _attach_boundary_metadata(
        self,
        zone_group: h5py.Group,
        base_group: h5py.Group,
        section_lookup: dict[str, list[Section]],
    ) -> None:
        zone_bc = zone_group.get("ZoneBC")
        if not isinstance(zone_bc, h5py.Group):
            return

        families = self._collect_families(base_group)
        for bc_name, bc_group in self._iter_children(zone_bc, "BC_t"):
            candidates = [
                self._clean_name(bc_group.attrs.get("name")),
                self._clean_name(bc_name),
            ]
            section: Section | None = None
            resolved_name = ""
            for candidate in candidates:
                key = self._normalize_key(candidate)
                if key and key in section_lookup and section_lookup[key]:
                    section = section_lookup[key].pop(0)
                    resolved_name = candidate or section.name
                    if not section_lookup[key]:
                        section_lookup.pop(key, None)
                    break

            if section is None:
                continue

            grid_location = self._read_grid_location(bc_group)
            family_name = self._read_family_name(bc_group, families)
            section.boundary = BoundaryInfo(
                name=family_name or resolved_name or section.name,
                grid_location=grid_location,
            )

    @staticmethod
    def _extract_name_token(section_group: h5py.Group, use_path: bool = False) -> str | None:
        if use_path:
            raw_name = section_group.name.rsplit("/", maxsplit=1)[-1]
        else:
            raw_name = section_group.attrs.get("name")
            if isinstance(raw_name, bytes):
                raw_name = raw_name.decode("utf-8", errors="ignore")

        if isinstance(raw_name, str):
            upper = raw_name.upper()
            for element_type in _SUPPORTED_ELEMENT_SIZES:
                token = element_type.split("_")[0]
                if token in upper:
                    return element_type
        return None

    @staticmethod
    def _clean_name(value: str | bytes | None) -> str:
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        if not isinstance(value, str):
            return ""
        tokens = value.strip().split()
        return " ".join(tokens)

    @staticmethod
    def _normalize_key(name: str | bytes | None) -> str:
        clean = CgnsLoader._clean_name(name)
        return clean.upper() if clean else ""

    def _read_grid_location(self, bc_group: h5py.Group) -> str | None:
        node = bc_group.get("GridLocation")
        if node is None:
            return None
        dataset = self._resolve_data_array(node)
        return self._decode_character_array(dataset)

    def _read_family_name(self, bc_group: h5py.Group, families: dict[str, str]) -> str | None:
        node = bc_group.get("FamilyName")
        if node is not None:
            dataset = self._resolve_data_array(node)
            name = self._decode_character_array(dataset)
            clean = self._clean_name(name)
            if clean:
                mapped = families.get(self._normalize_key(clean))
                return mapped or clean

        data_node = bc_group.get(" data")
        if isinstance(data_node, h5py.Dataset):
            inferred = self._decode_character_array(data_node)
            clean = self._clean_name(inferred)
            if clean:
                mapped = families.get(self._normalize_key(clean))
                return mapped or clean

        for key in (
            self._normalize_key(bc_group.attrs.get("name")),
            self._normalize_key(bc_group.name.rsplit("/", 1)[-1]),
        ):
            if key and key in families:
                return families[key]
        return None

    def _collect_families(self, base_group: h5py.Group) -> dict[str, str]:
        families: dict[str, str] = {}
        for family_name, family_group in self._iter_children(base_group, "Family_t"):
            cleaned_attr = self._clean_name(family_group.attrs.get("name"))
            group_clean = self._clean_name(family_name)
            display = cleaned_attr or group_clean or family_name
            for candidate in (cleaned_attr, family_group.attrs.get("name"), family_name, group_clean):
                key = self._normalize_key(candidate)
                if key and key not in families:
                    families[key] = display
        return families

    @staticmethod
    def _resolve_data_array(node: h5py.Dataset | h5py.Group) -> h5py.Dataset:
        if isinstance(node, h5py.Dataset):
            return node
        if isinstance(node, h5py.Group):
            dataset = node.get(" data")
            if isinstance(dataset, h5py.Dataset):
                return dataset
        raise ValueError(f"Unsupported CGNS data array layout at {node}")

    @staticmethod
    def _decode_character_array(dataset: h5py.Dataset) -> str:
        array = np.asarray(dataset)
        if array.dtype.kind in {"S", "a"}:
            return b"".join(part.rstrip(b"\x00") for part in array.flatten()).decode(
                "utf-8",
                errors="ignore",
            ).strip()
        if array.dtype.kind == "U":
            return "".join(array.flatten()).strip()
        if array.dtype.kind in {"i", "u"}:
            chars = [chr(int(value)) for value in array.flatten() if int(value) != 0]
            return "".join(chars).strip()
        value = dataset[()]
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore").strip()
        if isinstance(value, np.ndarray):
            return "".join(map(str, value.flatten())).strip()
        return str(value).strip()
