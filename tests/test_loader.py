"""Tests for CGNS loader."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

from cgns_gui.loader import CgnsLoader


@pytest.fixture()
def simple_cgns_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "sample.cgns"
    with h5py.File(file_path, "w") as handle:
        base = handle.create_group("Base")
        base.attrs["label"] = b"Base_t"

        zone = base.create_group("Zone")
        zone.attrs["label"] = b"Zone_t"

        coords = zone.create_group("GridCoordinates")
        coords.attrs["label"] = b"GridCoordinates_t"
        coords.create_dataset("CoordinateX", data=[0.0, 1.0, 0.0, 0.0])
        coords.create_dataset("CoordinateY", data=[0.0, 0.0, 1.0, 0.0])
        coords.create_dataset("CoordinateZ", data=[0.0, 0.0, 0.0, 1.0])

        section = zone.create_group("Section")
        section.attrs["label"] = b"Elements_t"
        section.create_dataset("ElementType", data=np.array("TETRA_4", dtype="S8"))
        section.create_dataset("ElementConnectivity", data=[1, 2, 3, 4])
    return file_path


@pytest.fixture()
def cgnsbase_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "cgnsbase.cgns"
    with h5py.File(file_path, "w") as handle:
        base = handle.create_group("Base")
        base.attrs["label"] = b"CGNSBase_t"

        zone = base.create_group("Zone")
        zone.attrs["label"] = b"Zone_t"

        coords = zone.create_group("GridCoordinates")
        coords.attrs["label"] = b"GridCoordinates_t"
        coords.create_dataset("CoordinateX", data=[0.0, 1.0])
        coords.create_dataset("CoordinateY", data=[0.0, 0.0])
        coords.create_dataset("CoordinateZ", data=[0.0, 0.0])

        section = zone.create_group("Edges")
        section.attrs["label"] = b"Elements_t"
        section.create_dataset("ElementType", data=np.array("BAR_2", dtype="S8"))
        section.create_dataset("ElementConnectivity", data=[1, 2])
    return file_path


def test_loader_reads_zone_and_section(simple_cgns_file: Path) -> None:
    loader = CgnsLoader()

    model = loader.load(simple_cgns_file)

    assert len(model.zones) == 1
    zone = model.zones[0]
    assert zone.name == "Zone"
    assert zone.total_points == 4
    assert zone.total_cells == 1

    section = zone.sections[0]
    assert section.element_type == "TETRA_4"
    np.testing.assert_array_equal(section.mesh.connectivity, [[0, 1, 2, 3]])


def test_loader_missing_file(tmp_path: Path) -> None:
    loader = CgnsLoader()
    missing = tmp_path / "missing.cgns"

    with pytest.raises(FileNotFoundError):
        loader.load(missing)


def test_loader_supports_cgnsbase_label(cgnsbase_file: Path) -> None:
    loader = CgnsLoader()

    model = loader.load(cgnsbase_file)

    assert [zone.name for zone in model.zones] == ["Zone"]


def test_loader_attaches_boundary_conditions(tmp_path: Path) -> None:
    file_path = tmp_path / "boundary.cgns"
    with h5py.File(file_path, "w") as handle:
        base = handle.create_group("Base")
        base.attrs["label"] = b"Base_t"

        zone = base.create_group("Zone")
        zone.attrs["label"] = b"Zone_t"

        coords = zone.create_group("GridCoordinates")
        coords.attrs["label"] = b"GridCoordinates_t"
        coords.create_dataset("CoordinateX", data=[0.0, 1.0, 0.0])
        coords.create_dataset("CoordinateY", data=[0.0, 0.0, 1.0])
        coords.create_dataset("CoordinateZ", data=[0.0, 0.0, 0.0])

        volume = zone.create_group("Solid")
        volume.attrs["label"] = b"Elements_t"
        volume.create_dataset("ElementType", data=np.array("TETRA_4", dtype="S8"))
        volume.create_dataset("ElementConnectivity", data=[1, 1, 1, 1])

        surface = zone.create_group(" Inlet  ")
        surface.attrs["label"] = b"Elements_t"
        surface.create_dataset("ElementType", data=np.array("TRI_3", dtype="S8"))
        surface.create_dataset("ElementConnectivity", data=[1, 2, 3])

        family = base.create_group("FamInlet")
        family.attrs["label"] = b"Family_t"
        family.attrs["name"] = b"Pressure Inlet"

        zone_bc = zone.create_group("ZoneBC")
        zone_bc.attrs["label"] = b"ZoneBC_t"
        inlet_bc = zone_bc.create_group(" Inlet  ")
        inlet_bc.attrs["label"] = b"BC_t"
        inlet_bc.attrs["name"] = b" Inlet  "
        inlet_bc.create_dataset("FamilyName", data=np.frombuffer(b"FamInlet", dtype=np.uint8))
        grid_location = inlet_bc.create_group("GridLocation")
        grid_location.attrs["label"] = b"GridLocation_t"
        grid_location.create_dataset(" data", data=np.frombuffer(b"FaceCenter", dtype=np.uint8))

    loader = CgnsLoader()

    model = loader.load(file_path)

    zone = model.zones[0]
    sections = {section.name: section for section in zone.sections}
    assert "Inlet" in sections
    inlet = sections["Inlet"]
    assert inlet.boundary is not None
    assert inlet.boundary.name == "Pressure Inlet"
    assert inlet.boundary.grid_location == "FaceCenter"

def test_loader_prefers_section_name_when_type_code_incorrect(tmp_path: Path) -> None:
    file_path = tmp_path / "wrong_code.cgns"
    with h5py.File(file_path, "w") as handle:
        base = handle.create_group("Base")
        base.attrs["label"] = b"Base_t"

        zone = base.create_group("Zone")
        zone.attrs["label"] = b"Zone_t"

        coords = zone.create_group("GridCoordinates")
        coords.attrs["label"] = b"GridCoordinates_t"
        coords.create_dataset("CoordinateX", data=[0.0, 1.0, 0.0, 1.0, 0.0, 1.0])
        coords.create_dataset("CoordinateY", data=[0.0, 0.0, 1.0, 1.0, 0.0, 0.0])
        coords.create_dataset("CoordinateZ", data=[0.0, 0.0, 0.0, 0.0, 1.0, 1.0])

        section = zone.create_group("Elem_PENTA_6")
        section.attrs["label"] = b"Elements_t"
        section.attrs["name"] = b"Elem_PENTA_6"
        section.create_dataset(" data", data=np.array([14, 0], dtype=np.int32))

        element_range = section.create_group("ElementRange")
        element_range.attrs["label"] = b"IndexRange_t"
        element_range.create_dataset(" data", data=np.array([1, 2], dtype=np.int32))

        connectivity = section.create_group("ElementConnectivity")
        connectivity.attrs["label"] = b"DataArray_t"
        connectivity.create_dataset(
            " data",
            data=np.array([
                1,
                2,
                3,
                4,
                5,
                6,
                1,
                3,
                5,
                6,
                4,
                2,
            ], dtype=np.int32),
        )

    loader = CgnsLoader()

    model = loader.load(file_path)

    section = model.zones[0].sections[0]
    assert section.element_type == "PENTA_6"
    assert section.mesh.connectivity.shape == (2, 6)