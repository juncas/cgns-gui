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