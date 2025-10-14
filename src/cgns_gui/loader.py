"""CGNS file loader built on pyCGNS."""

from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    from CGNS import MAP as cgnsmap
    from CGNS.PAT import cgnskeywords as CGK
except ImportError as e:
    msg = (
        "pyCGNS is required for CGNS file loading. "
        "Please install it using: conda install -c conda-forge pycgns"
    )
    raise ImportError(msg) from e

from .model import BoundaryInfo, CgnsModel, MeshData, Section, Zone

# CGNS element type codes (pyCGNS values)
# Reference: CGNS/SIDS Element Type definitions
_SUPPORTED_ELEMENT_SIZES: dict[str, int] = {
    "BAR_2": 2,
    "TRI_3": 3,
    "QUAD_4": 4,
    "TETRA_4": 4,
    "PYRA_5": 5,
    "PENTA_6": 6,
    "HEXA_8": 8,
}

# CGNS element type code mapping (for pyCGNS)
_ELEMENT_TYPE_BY_CODE: dict[int, str] = {
    3: "BAR_2",      # BAR_2
    5: "TRI_3",      # TRI_3
    7: "QUAD_4",     # QUAD_4
    10: "TETRA_4",   # TETRA_4
    12: "PYRA_5",    # PYRA_5
    14: "PENTA_6",   # PENTA_6
    17: "HEXA_8",    # HEXA_8
}

_ELEMENT_TYPE_BY_NAME: dict[str, str] = {
    "BAR_2": "BAR_2",
    "TRI_3": "TRI_3",
    "QUAD_4": "QUAD_4",
    "TETRA_4": "TETRA_4",
    "PYRA_5": "PYRA_5",
    "PENTA_6": "PENTA_6",
    "HEXA_8": "HEXA_8",
}


class CgnsLoader:
    """Parse CGNS files using pyCGNS library.
    
    This loader handles CGNS/Python tree structure: [name, value, children, type]
    where:
        - name: string node name
        - value: numpy array or None
        - children: list of child nodes
        - type: CGNS node type string (e.g., 'Zone_t', 'Elements_t')
    """

    def __init__(self) -> None:
        self._path: Path | None = None
        self._tree: list | None = None

    def load(self, path: str | Path) -> CgnsModel:
        """Load a CGNS file and return a CgnsModel."""
        path = Path(path)
        if not path.exists():
            msg = f"CGNS file not found: {path}"
            raise FileNotFoundError(msg)
        self._path = path

        # Load CGNS tree using pyCGNS
        # Returns: (tree, links, paths)
        self._tree, _, _ = cgnsmap.load(str(path))

        zones: list[Zone] = []
        
        # Find all Base nodes
        for base in self._get_children_by_type(self._tree, ['CGNSBase_t', 'Base_t']):
            # Find all Zone nodes in this base
            for zone_node in self._get_children_by_type(base, 'Zone_t'):
                zone = self._read_zone(zone_node, base)
                if zone:
                    zones.append(zone)
        
        return CgnsModel(zones=zones)

    def _get_children_by_type(self, parent: list, node_types: str | list[str]) -> list[list]:
        """Get all child nodes of given type(s) from parent node.
        
        Args:
            parent: CGNS node [name, value, children, type]
            node_types: Single type string or list of type strings
            
        Returns:
            List of matching child nodes
        """
        if isinstance(node_types, str):
            node_types = [node_types]
        
        children = parent[2] if len(parent) > 2 else []
        return [child for child in children if len(child) > 3 and child[3] in node_types]

    def _get_child_by_name(self, parent: list, name: str) -> list | None:
        """Get a child node by name."""
        children = parent[2] if len(parent) > 2 else []
        for child in children:
            if len(child) > 0 and child[0] == name:
                return child
        return None

    def _read_zone(self, zone_node: list, base_node: list) -> Zone | None:
        """Read a Zone node and return a Zone object."""
        zone_name = zone_node[0]
        sections: list[Section] = []
        section_lookup: dict[str, list[Section]] = {}
        
        # Read grid coordinates
        points = self._read_coordinates(zone_node)
        if points is None:
            return None
        
        # Read all Elements_t nodes (sections)
        for section_idx, elem_node in enumerate(
            self._get_children_by_type(zone_node, 'Elements_t'),
            start=1,
        ):
            section = self._read_section(elem_node, points, section_idx)
            if section:
                sections.append(section)
                # Build lookup for boundary condition matching
                key = self._normalize_key(section.name)
                if key:
                    section_lookup.setdefault(key, []).append(section)
        
        # Attach boundary condition metadata
        self._attach_boundary_metadata(zone_node, base_node, section_lookup)
        
        # Renumber section IDs
        for new_id, section in enumerate(sections, start=1):
            section.id = new_id
        
        return Zone(name=zone_name, sections=sections)

    def _read_coordinates(self, zone_node: list) -> np.ndarray | None:
        """Read grid coordinates from GridCoordinates_t node."""
        # Find GridCoordinates node
        grid_coords_nodes = self._get_children_by_type(zone_node, 'GridCoordinates_t')
        if not grid_coords_nodes:
            return None
        
        grid_coords = grid_coords_nodes[0]  # Use first GridCoordinates node
        
        # Read X, Y, Z coordinates
        coord_arrays = []
        for axis in ('X', 'Y', 'Z'):
            coord_node = self._get_child_by_name(grid_coords, f'Coordinate{axis}')
            if coord_node is None:
                raise ValueError(f"Missing Coordinate{axis} in zone {zone_node[0]}")
            
            # Value is at index 1 in [name, value, children, type]
            coord_data = coord_node[1]
            if coord_data is None:
                raise ValueError(f"Coordinate{axis} has no data")
            
            coord_arrays.append(np.asarray(coord_data, dtype=float).reshape(-1))
        
        return np.column_stack(coord_arrays)

    def _read_section(self, elem_node: list, points: np.ndarray, section_id: int) -> Section | None:
        """Read an Elements_t node and return a Section object."""
        section_name = elem_node[0]
        
        # Get element type from node value (element type code)
        elem_type_code = None
        if elem_node[1] is not None and len(elem_node[1]) > 0:
            elem_type_code = int(elem_node[1][0])
        
        # Map code to element type name
        element_type = None
        if elem_type_code in _ELEMENT_TYPE_BY_CODE:
            element_type = _ELEMENT_TYPE_BY_CODE[elem_type_code]
        else:
            # Try to infer from name
            element_type = self._infer_element_type_from_name(section_name)
        
        if element_type is None or element_type not in _SUPPORTED_ELEMENT_SIZES:
            # Skip unsupported element types
            return None
        
        # Find ElementConnectivity node
        conn_node = self._get_child_by_name(elem_node, 'ElementConnectivity')
        if conn_node is None or conn_node[1] is None:
            return None
        
        connectivity_raw = np.asarray(conn_node[1], dtype=np.int64)
        
        # Get element size
        element_size = _SUPPORTED_ELEMENT_SIZES[element_type]
        
        # Reshape connectivity
        if connectivity_raw.size % element_size != 0:
            # Cannot reshape, skip this section
            return None
        
        connectivity_raw = connectivity_raw.reshape(-1, element_size)
        
        # CGNS uses 1-based indexing, convert to 0-based for VTK
        connectivity = connectivity_raw - 1
        
        # Get element range
        range_node = self._get_child_by_name(elem_node, 'ElementRange')
        if range_node is not None and range_node[1] is not None:
            elem_range = tuple(range_node[1])
        else:
            elem_range = (1, connectivity.shape[0])
        
        # Create mesh data
        mesh = MeshData(
            points=points,
            connectivity=connectivity,
            cell_type=element_type,
        )
        
        # Clean section name
        clean_name = self._clean_name(section_name)
        
        return Section(
            id=section_id,
            name=clean_name or section_name,
            element_type=element_type,
            range=elem_range,
            mesh=mesh,
        )

    def _attach_boundary_metadata(
        self,
        zone_node: list,
        base_node: list,
        section_lookup: dict[str, list[Section]],
    ) -> None:
        """Attach boundary condition metadata to sections."""
        # Find ZoneBC node
        zonebc_nodes = self._get_children_by_type(zone_node, 'ZoneBC_t')
        if not zonebc_nodes:
            return
        
        zonebc = zonebc_nodes[0]
        
        # Collect family names from base
        families = self._collect_families(base_node)
        
        # Process each BC_t node
        for bc_node in self._get_children_by_type(zonebc, 'BC_t'):
            bc_name = bc_node[0]
            
            # Try to match BC to a section
            candidates = [
                self._clean_name(bc_name),
                bc_name,
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
            
            # Extract BC metadata
            grid_location = self._read_grid_location(bc_node)
            family_name = self._read_family_name(bc_node, families)
            
            section.boundary = BoundaryInfo(
                name=family_name or resolved_name or section.name,
                grid_location=grid_location,
            )

    def _read_grid_location(self, bc_node: list) -> str | None:
        """Read GridLocation from BC node."""
        grid_loc_node = self._get_child_by_name(bc_node, 'GridLocation')
        if grid_loc_node is None or grid_loc_node[1] is None:
            return None
        
        value = grid_loc_node[1]
        if isinstance(value, np.ndarray) and value.size > 0:
            # Handle both string and bytes
            loc = value.flat[0]
            if isinstance(loc, bytes):
                return loc.decode('utf-8', errors='ignore').strip()
            return str(loc).strip()
        return None

    def _read_family_name(self, bc_node: list, families: dict[str, str]) -> str | None:
        """Read FamilyName from BC node."""
        family_node = self._get_child_by_name(bc_node, 'FamilyName')
        if family_node is not None and family_node[1] is not None:
            value = family_node[1]
            if isinstance(value, np.ndarray) and value.size > 0:
                # Decode family name
                if value.dtype.kind in ('S', 'a'):  # bytes
                    family_name = b''.join(value.flat).decode('utf-8', errors='ignore').strip()
                elif value.dtype.kind == 'U':  # unicode
                    family_name = ''.join(value.flat).strip()
                else:
                    family_name = str(value.flat[0]).strip()
                
                clean = self._clean_name(family_name)
                if clean:
                    key = self._normalize_key(clean)
                    return families.get(key, clean)
        
        # Try matching BC name to families
        bc_name = bc_node[0]
        key = self._normalize_key(bc_name)
        if key and key in families:
            return families[key]
        
        return None

    def _collect_families(self, base_node: list) -> dict[str, str]:
        """Collect Family_t nodes from base and create a lookup dict."""
        families: dict[str, str] = {}
        
        for family_node in self._get_children_by_type(base_node, 'Family_t'):
            family_name = family_node[0]
            clean_name = self._clean_name(family_name)
            display_name = clean_name or family_name
            
            # Add to lookup with various keys
            for key_candidate in [family_name, clean_name]:
                key = self._normalize_key(key_candidate)
                if key and key not in families:
                    families[key] = display_name
        
        return families

    def _infer_element_type_from_name(self, name: str) -> str | None:
        """Try to infer element type from section name."""
        if not name:
            return None
        
        upper_name = name.upper()
        for elem_type in _SUPPORTED_ELEMENT_SIZES:
            # Check if element type token appears in name
            token = elem_type.split('_')[0]  # e.g., "TETRA" from "TETRA_4"
            if token in upper_name:
                return elem_type
        
        return None

    @staticmethod
    def _clean_name(value: str | bytes | None) -> str:
        """Clean and normalize a name string."""
        if isinstance(value, bytes):
            value = value.decode('utf-8', errors='ignore')
        if not isinstance(value, str):
            return ""
        
        # Remove extra whitespace
        tokens = value.strip().split()
        return " ".join(tokens)

    @staticmethod
    def _normalize_key(name: str | bytes | None) -> str:
        """Normalize a name for use as a lookup key."""
        clean = CgnsLoader._clean_name(name)
        return clean.upper() if clean else ""
