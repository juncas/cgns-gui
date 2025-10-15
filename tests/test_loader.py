"""Tests for CGNS loader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cgns_gui.loader import CgnsLoader

# Fixtures are imported from conftest.py


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


def test_loader_attaches_boundary_conditions(boundary_cgns_file: Path) -> None:
    loader = CgnsLoader()

    model = loader.load(boundary_cgns_file)

    zone = model.zones[0]
    sections = {section.name: section for section in zone.sections}
    assert "Inlet" in sections
    inlet = sections["Inlet"]
    assert inlet.boundary is not None
    assert inlet.boundary.name == "Pressure Inlet"
    assert inlet.boundary.grid_location == "FaceCenter"


def test_loader_boundary_uses_family_group_when_dataset_missing(family_fallback_file: Path) -> None:
    loader = CgnsLoader()

    model = loader.load(family_fallback_file)

    boundary_section = model.zones[0].sections[0]
    assert boundary_section.boundary is not None
    assert boundary_section.boundary.name == "Outlet"
    assert boundary_section.boundary.grid_location == "FaceCenter"


def test_loader_prefers_section_name_when_type_code_incorrect(penta_cgns_file: Path) -> None:
    loader = CgnsLoader()

    model = loader.load(penta_cgns_file)

    section = model.zones[0].sections[0]
    assert section.element_type == "PENTA_6"
    assert section.mesh.connectivity.shape == (2, 6)