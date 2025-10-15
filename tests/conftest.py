"""Shared pytest fixtures for CGNS GUI tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

try:
    from CGNS import MAP as cgnsmap
    from CGNS.PAT import cgnsutils
    from CGNS.PAT import cgnskeywords as cgk
    PYCGNS_AVAILABLE = True
except ImportError:
    PYCGNS_AVAILABLE = False


def _create_simple_cgns_pycgns(file_path: Path) -> None:
    """Create a simple CGNS file with pyCGNS (one zone, one tetrahedron)."""
    # Create CGNS tree structure: [name, value, children, type]
    
    # Root node
    tree = ['CGNSTree', None, [], 'CGNSTree_t']
    
    # Base node
    base = ['Base', np.array([3, 3], dtype='int32'), [], 'CGNSBase_t']
    tree[2].append(base)
    
    # Zone node (4 vertices, 1 cell, 0 boundary vertices)
    zone = ['Zone', np.array([[4, 1, 0]], dtype='int32'), [], 'Zone_t']
    base[2].append(zone)
    
    # Grid coordinates
    coords = ['GridCoordinates', None, [], 'GridCoordinates_t']
    zone[2].append(coords)
    
    coord_x = ['CoordinateX', np.array([0.0, 1.0, 0.0, 0.0], dtype='float64'), [], 'DataArray_t']
    coord_y = ['CoordinateY', np.array([0.0, 0.0, 1.0, 0.0], dtype='float64'), [], 'DataArray_t']
    coord_z = ['CoordinateZ', np.array([0.0, 0.0, 0.0, 1.0], dtype='float64'), [], 'DataArray_t']
    coords[2].extend([coord_x, coord_y, coord_z])
    
    # Elements section (TETRA_4 = type 10)
    section = ['Section', np.array([10, 0], dtype='int32'), [], 'Elements_t']
    zone[2].append(section)
    
    # Element range
    elem_range = ['ElementRange', np.array([1, 1], dtype='int32'), [], 'IndexRange_t']
    section[2].append(elem_range)
    
    # Element connectivity (1-based indexing for CGNS)
    connectivity = ['ElementConnectivity', np.array([1, 2, 3, 4], dtype='int32'), [], 'DataArray_t']
    section[2].append(connectivity)
    
    # Save to file
    cgnsmap.save(str(file_path), tree)


def _create_cgnsbase_pycgns(file_path: Path) -> None:
    """Create a CGNS file with CGNSBase_t label and BAR_2 elements."""
    # Root node
    tree = ['CGNSTree', None, [], 'CGNSTree_t']
    
    # Base node with CGNSBase_t label
    base = ['Base', np.array([3, 3], dtype='int32'), [], 'CGNSBase_t']
    tree[2].append(base)
    
    # Zone node (2 vertices, 1 cell, 0 boundary vertices)
    zone = ['Zone', np.array([[2, 1, 0]], dtype='int32'), [], 'Zone_t']
    base[2].append(zone)
    
    # Grid coordinates
    coords = ['GridCoordinates', None, [], 'GridCoordinates_t']
    zone[2].append(coords)
    
    coord_x = ['CoordinateX', np.array([0.0, 1.0], dtype='float64'), [], 'DataArray_t']
    coord_y = ['CoordinateY', np.array([0.0, 0.0], dtype='float64'), [], 'DataArray_t']
    coord_z = ['CoordinateZ', np.array([0.0, 0.0], dtype='float64'), [], 'DataArray_t']
    coords[2].extend([coord_x, coord_y, coord_z])
    
    # Elements section (BAR_2 = type 3)
    section = ['Edges', np.array([3, 0], dtype='int32'), [], 'Elements_t']
    zone[2].append(section)
    
    elem_range = ['ElementRange', np.array([1, 1], dtype='int32'), [], 'IndexRange_t']
    section[2].append(elem_range)
    
    connectivity = ['ElementConnectivity', np.array([1, 2], dtype='int32'), [], 'DataArray_t']
    section[2].append(connectivity)
    
    cgnsmap.save(str(file_path), tree)


def _create_boundary_cgns_pycgns(file_path: Path) -> None:
    """Create CGNS file with boundary conditions and family."""
    # Root node
    tree = ['CGNSTree', None, [], 'CGNSTree_t']
    
    # Base node
    base = ['Base', np.array([3, 3], dtype='int32'), [], 'Base_t']
    tree[2].append(base)
    
    # Family
    family = ['FamInlet', None, [], 'Family_t']
    family_name = ['FamilyName', np.frombuffer(b'Pressure Inlet', dtype=np.uint8), [], 'FamilyName_t']
    family[2].append(family_name)
    base[2].append(family)
    
    # Zone node
    zone = ['Zone', np.array([[3, 1, 0]], dtype='int32'), [], 'Zone_t']
    base[2].append(zone)
    
    # Grid coordinates
    coords = ['GridCoordinates', None, [], 'GridCoordinates_t']
    zone[2].append(coords)
    
    coord_x = ['CoordinateX', np.array([0.0, 1.0, 0.0], dtype='float64'), [], 'DataArray_t']
    coord_y = ['CoordinateY', np.array([0.0, 0.0, 1.0], dtype='float64'), [], 'DataArray_t']
    coord_z = ['CoordinateZ', np.array([0.0, 0.0, 0.0], dtype='float64'), [], 'DataArray_t']
    coords[2].extend([coord_x, coord_y, coord_z])
    
    # Volume section (TETRA_4)
    volume = ['Solid', np.array([10, 0], dtype='int32'), [], 'Elements_t']
    zone[2].append(volume)
    vol_range = ['ElementRange', np.array([1, 1], dtype='int32'), [], 'IndexRange_t']
    volume[2].append(vol_range)
    vol_conn = ['ElementConnectivity', np.array([1, 1, 1, 1], dtype='int32'), [], 'DataArray_t']
    volume[2].append(vol_conn)
    
    # Surface section (TRI_3)
    surface = ['Inlet', np.array([5, 0], dtype='int32'), [], 'Elements_t']
    zone[2].append(surface)
    surf_range = ['ElementRange', np.array([2, 2], dtype='int32'), [], 'IndexRange_t']
    surface[2].append(surf_range)
    surf_conn = ['ElementConnectivity', np.array([1, 2, 3], dtype='int32'), [], 'DataArray_t']
    surface[2].append(surf_conn)
    
    # ZoneBC
    zone_bc = ['ZoneBC', None, [], 'ZoneBC_t']
    zone[2].append(zone_bc)
    
    # BC for Inlet
    inlet_bc = ['Inlet', np.frombuffer(b'BCInflow', dtype=np.uint8), [], 'BC_t']
    zone_bc[2].append(inlet_bc)
    
    # FamilyName reference
    bc_family = ['FamilyName', np.frombuffer(b'FamInlet', dtype=np.uint8), [], 'FamilyName_t']
    inlet_bc[2].append(bc_family)
    
    # GridLocation
    grid_loc = ['GridLocation', np.frombuffer(b'FaceCenter', dtype=np.uint8), [], 'GridLocation_t']
    inlet_bc[2].append(grid_loc)
    
    cgnsmap.save(str(file_path), tree)


def _create_family_fallback_cgns_pycgns(file_path: Path) -> None:
    """Create CGNS file with family but no FamilyName dataset in BC."""
    tree = ['CGNSTree', None, [], 'CGNSTree_t']
    
    base = ['Base', np.array([3, 3], dtype='int32'), [], 'Base_t']
    tree[2].append(base)
    
    # Family
    family = ['FamOutlet', None, [], 'Family_t']
    family_name = ['FamilyName', np.frombuffer(b'Outlet', dtype=np.uint8), [], 'FamilyName_t']
    family[2].append(family_name)
    base[2].append(family)
    
    zone = ['Zone', np.array([[3, 1, 0]], dtype='int32'), [], 'Zone_t']
    base[2].append(zone)
    
    coords = ['GridCoordinates', None, [], 'GridCoordinates_t']
    zone[2].append(coords)
    
    coord_x = ['CoordinateX', np.array([0.0, 1.0, 0.0], dtype='float64'), [], 'DataArray_t']
    coord_y = ['CoordinateY', np.array([0.0, 0.0, 1.0], dtype='float64'), [], 'DataArray_t']
    coord_z = ['CoordinateZ', np.array([0.0, 0.0, 0.0], dtype='float64'), [], 'DataArray_t']
    coords[2].extend([coord_x, coord_y, coord_z])
    
    # Surface section
    surface = ['Outlet', np.array([5, 0], dtype='int32'), [], 'Elements_t']
    zone[2].append(surface)
    surf_range = ['ElementRange', np.array([1, 1], dtype='int32'), [], 'IndexRange_t']
    surface[2].append(surf_range)
    surf_conn = ['ElementConnectivity', np.array([1, 2, 3], dtype='int32'), [], 'DataArray_t']
    surface[2].append(surf_conn)
    
    # ZoneBC
    zone_bc = ['ZoneBC', None, [], 'ZoneBC_t']
    zone[2].append(zone_bc)
    
    outlet_bc = ['Outlet', np.frombuffer(b'BCOutflow', dtype=np.uint8), [], 'BC_t']
    zone_bc[2].append(outlet_bc)
    
    # No FamilyName dataset - should fall back to FamOutlet group
    
    grid_loc = ['GridLocation', np.frombuffer(b'FaceCenter', dtype=np.uint8), [], 'GridLocation_t']
    outlet_bc[2].append(grid_loc)
    
    cgnsmap.save(str(file_path), tree)


def _create_penta_cgns_pycgns(file_path: Path) -> None:
    """Create CGNS file with PENTA_6 elements using section name for type detection."""
    tree = ['CGNSTree', None, [], 'CGNSTree_t']
    
    base = ['Base', np.array([3, 3], dtype='int32'), [], 'Base_t']
    tree[2].append(base)
    
    zone = ['Zone', np.array([[6, 2, 0]], dtype='int32'), [], 'Zone_t']
    base[2].append(zone)
    
    coords = ['GridCoordinates', None, [], 'GridCoordinates_t']
    zone[2].append(coords)
    
    coord_x = ['CoordinateX', np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0], dtype='float64'), [], 'DataArray_t']
    coord_y = ['CoordinateY', np.array([0.0, 0.0, 1.0, 1.0, 0.0, 0.0], dtype='float64'), [], 'DataArray_t']
    coord_z = ['CoordinateZ', np.array([0.0, 0.0, 0.0, 0.0, 1.0, 1.0], dtype='float64'), [], 'DataArray_t']
    coords[2].extend([coord_x, coord_y, coord_z])
    
    # PENTA_6 section (type 14)
    section = ['Elem_PENTA_6', np.array([14, 0], dtype='int32'), [], 'Elements_t']
    zone[2].append(section)
    
    elem_range = ['ElementRange', np.array([1, 2], dtype='int32'), [], 'IndexRange_t']
    section[2].append(elem_range)
    
    connectivity = ['ElementConnectivity', 
                   np.array([1, 2, 3, 4, 5, 6, 1, 3, 5, 6, 4, 2], dtype='int32'), 
                   [], 'DataArray_t']
    section[2].append(connectivity)
    
    cgnsmap.save(str(file_path), tree)


@pytest.fixture()
def simple_cgns_file(tmp_path: Path) -> Path:
    """Create a simple CGNS file with one zone and one tetrahedral element."""
    file_path = tmp_path / "sample.cgns"
    if PYCGNS_AVAILABLE:
        _create_simple_cgns_pycgns(file_path)
    else:
        pytest.skip("pyCGNS not available")
    return file_path


@pytest.fixture()
def cgnsbase_file(tmp_path: Path) -> Path:
    """Create a CGNS file with CGNSBase_t label."""
    file_path = tmp_path / "cgnsbase.cgns"
    if PYCGNS_AVAILABLE:
        _create_cgnsbase_pycgns(file_path)
    else:
        pytest.skip("pyCGNS not available")
    return file_path


@pytest.fixture()
def boundary_cgns_file(tmp_path: Path) -> Path:
    """Create a CGNS file with boundary conditions."""
    file_path = tmp_path / "boundary.cgns"
    if PYCGNS_AVAILABLE:
        _create_boundary_cgns_pycgns(file_path)
    else:
        pytest.skip("pyCGNS not available")
    return file_path


@pytest.fixture()
def family_fallback_file(tmp_path: Path) -> Path:
    """Create a CGNS file with family fallback test case."""
    file_path = tmp_path / "family_fallback.cgns"
    if PYCGNS_AVAILABLE:
        _create_family_fallback_cgns_pycgns(file_path)
    else:
        pytest.skip("pyCGNS not available")
    return file_path


@pytest.fixture()
def penta_cgns_file(tmp_path: Path) -> Path:
    """Create a CGNS file with PENTA_6 elements."""
    file_path = tmp_path / "wrong_code.cgns"
    if PYCGNS_AVAILABLE:
        _create_penta_cgns_pycgns(file_path)
    else:
        pytest.skip("pyCGNS not available")
    return file_path
