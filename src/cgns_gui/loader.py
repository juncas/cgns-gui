"""CGNS file loader built on pyCGNS.""""""CGNS file loader built on top of h5py."""



from __future__ import annotationsfrom __future__ import annotations



from pathlib import Pathfrom collections.abc import Iterator

from pathlib import Path

import numpy as np

import h5py

try:import numpy as np

    from CGNS import MAP as cgnsmap

    from CGNS.PAT import cgnskeywords, cgnsutilsfrom .model import BoundaryInfo, CgnsModel, MeshData, Section, Zone

except ImportError as e:

    msg = (_SUPPORTED_ELEMENT_SIZES: dict[str, int] = {

        "pyCGNS is required for CGNS file loading. "    "BAR_2": 2,

        "Please install it using: conda install -c conda-forge pycgns"    "TRI_3": 3,

    )    "QUAD_4": 4,

    raise ImportError(msg) from e    "TETRA_4": 4,

    "PYRA_5": 5,

from .model import BoundaryInfo, CgnsModel, MeshData, Section, Zone    "PENTA_6": 6,

    "HEXA_8": 8,

# CGNS 单元类型映射到我们的命名}

_ELEMENT_TYPE_BY_CODE: dict[int, str] = {

    3: "BAR_2",      # BAR_2_ELEMENT_TYPE_BY_CODE: dict[int, str] = {

    5: "TRI_3",      # TRI_3    2: "BAR_2",

    7: "QUAD_4",     # QUAD_4    5: "TRI_3",

    10: "TETRA_4",   # TETRA_4    7: "QUAD_4",

    12: "PYRA_5",    # PYRA_5    10: "TETRA_4",

    14: "PENTA_6",   # PENTA_6    12: "PYRA_5",

    17: "HEXA_8",    # HEXA_8    13: "PENTA_6",

}    14: "HEXA_8",

}

_SUPPORTED_ELEMENT_SIZES: dict[str, int] = {

    "BAR_2": 2,

    "TRI_3": 3,class CgnsLoader:

    "QUAD_4": 4,    """Parse a subset of CGNS/HDF5 files."""

    "TETRA_4": 4,

    "PYRA_5": 5,    def __init__(self) -> None:

    "PENTA_6": 6,        self._path: Path | None = None

    "HEXA_8": 8,

}    def load(self, path: str | Path) -> CgnsModel:

        path = Path(path)

        if not path.exists():

class CgnsLoader:            msg = f"CGNS file not found: {path}"

    """Parse CGNS files using pyCGNS library."""            raise FileNotFoundError(msg)

        self._path = path

    def __init__(self) -> None:

        self._path: Path | None = None        with h5py.File(path, "r") as handle:

        self._tree: list | None = None            zones: list[Zone] = []

            for _, base_group in self._iter_children(handle, ("Base_t", "CGNSBase_t")):

    def load(self, path: str | Path) -> CgnsModel:                for zone_name, zone_group in self._iter_children(base_group, "Zone_t"):

        """Load a CGNS file and return a CgnsModel.                    zones.append(self._read_zone(zone_name, zone_group, base_group))

                return CgnsModel(zones=zones)

        Args:

            path: Path to the CGNS file    def _read_zone(self, name: str, group: h5py.Group, base_group: h5py.Group) -> Zone:

                    sections: list[Section] = []

        Returns:        section_lookup: dict[str, list[Section]] = {}

            CgnsModel containing zones and sections        points = self._read_points(group)

                    for section_idx, (section_name, section_group) in enumerate(

        Raises:            self._iter_children(group, "Elements_t"),

            FileNotFoundError: If the file doesn't exist            start=1,

            ValueError: If the file format is invalid        ):

        """            mesh = self._read_section_mesh(section_group, points)

        path = Path(path)            clean_name = self._clean_name(section_name)

        if not path.exists():            sections.append(

            msg = f"CGNS file not found: {path}"                Section(

            raise FileNotFoundError(msg)                    id=section_idx,

                            name=clean_name or section_name,

        self._path = path                    element_type=mesh.cell_type,

                            range=(1, mesh.connectivity.shape[0]),

        # 使用 pyCGNS 加载文件                    mesh=mesh,

        try:                )

            self._tree, links, paths = cgnsmap.load(str(path))            )

        except Exception as e:            key = self._normalize_key(clean_name or section_name)

            msg = f"Failed to load CGNS file: {e}"            if key:

            raise ValueError(msg) from e                section_lookup.setdefault(key, []).append(sections[-1])

        

        # 解析 zones        self._attach_boundary_metadata(group, base_group, section_lookup)

        zones: list[Zone] = []

        for base in self._get_children_by_type(self._tree, ['CGNSBase_t', 'Base_t']):        for new_id, section in enumerate(sections, start=1):

            for zone in self._get_children_by_type(base, 'Zone_t'):            section.id = new_id

                zones.append(self._read_zone(zone, base))        return Zone(name=name, sections=sections)

        

        return CgnsModel(zones=zones)    def _read_points(self, group: h5py.Group) -> np.ndarray:

        coords_group = None

    def _get_children_by_type(self, node: list, node_types: str | list[str]) -> list:        for candidate_name, candidate in self._iter_children(group, "GridCoordinates_t"):

        """获取指定类型的子节点。            coords_group = candidate

                    break

        Args:        if coords_group is None:

            node: CGNS/Python 节点 [name, value, children, type]            raise ValueError(f"Zone {group.name} missing GridCoordinates")

            node_types: 节点类型字符串或类型列表

                    coord_arrays = []

        Returns:        for axis in ("X", "Y", "Z"):

            匹配的子节点列表            node = coords_group.get(f"Coordinate{axis}")

        """            if node is None:

        if isinstance(node_types, str):                raise ValueError(f"Missing Coordinate{axis} in {coords_group.name}")

            node_types = [node_types]            dataset = self._resolve_data_array(node)

                    coord_arrays.append(np.asarray(dataset, dtype=float).reshape(-1))

        if not node or len(node) < 3:        return np.column_stack(coord_arrays)

            return []

            def _read_section_mesh(self, section_group: h5py.Group, points: np.ndarray) -> MeshData:

        children = node[2] if node[2] is not None else []        element_type_value = self._infer_element_type(section_group)

        return [child for child in children if len(child) > 3 and child[3] in node_types]

        conn_node = section_group.get("ElementConnectivity")

    def _get_child_by_name(self, node: list, name: str) -> list | None:        if conn_node is None:

        """按名称获取子节点。"""            raise ValueError(f"Section {section_group.name} missing ElementConnectivity")

        if not node or len(node) < 3 or node[2] is None:        conn_dataset = self._resolve_data_array(conn_node)

            return None

                element_size = _SUPPORTED_ELEMENT_SIZES.get(element_type_value)

        for child in node[2]:        if element_size is None:

            if len(child) > 0 and child[0] == name:            raise ValueError(f"Unsupported element type: {element_type_value}")

                return child

        return None        connectivity_raw = np.asarray(conn_dataset, dtype=np.int64).reshape(-1, element_size)

        # CGNS uses 1-based indexing for connectivity

    def _read_zone(self, zone_node: list, base_node: list) -> Zone:        connectivity = connectivity_raw - 1

        """从 CGNS 树节点读取 Zone。        return MeshData(points=points, connectivity=connectivity, cell_type=element_type_value)

        

        Args:    @staticmethod

            zone_node: Zone_t 节点    def _iter_children(

            base_node: 父 CGNSBase_t 节点        group: h5py.Group,

                    labels: str | tuple[str, ...],

        Returns:    ) -> Iterator[tuple[str, h5py.Group]]:

            Zone 对象        if isinstance(labels, str):

        """            wanted = {labels}

        zone_name = zone_node[0]        else:

                    wanted = set(labels)

        # 读取网格坐标

        points = self._read_coordinates(zone_node)        for name, child in group.items():

                    if isinstance(child, h5py.Group):

        # 读取所有 Elements_t 节点                child_label = child.attrs.get("label")

        sections: list[Section] = []                if isinstance(child_label, bytes):

        section_lookup: dict[str, list[Section]] = {}                    child_label = child_label.decode("utf-8")

                        if child_label in wanted:

        for section_idx, elem_node in enumerate(                    yield name, child

            self._get_children_by_type(zone_node, 'Elements_t'),

            start=1    @staticmethod

        ):    def _decode_dataset(dataset: h5py.Dataset) -> str:

            section = self._read_section(elem_node, points, section_idx)        value = dataset[()]

            if section:        if isinstance(value, bytes):

                sections.append(section)            return value.decode("utf-8")

                # 构建查找表用于边界条件关联        if isinstance(value, np.bytes_):

                key = self._normalize_key(section.name)            return value.astype(str)

                if key:        if isinstance(value, np.ndarray) and value.ndim == 0:

                    section_lookup.setdefault(key, []).append(section)            return str(value.item())

                return str(value)

        # 读取边界条件并关联到 sections

        self._attach_boundary_metadata(zone_node, base_node, section_lookup)    def _infer_element_type(self, section_group: h5py.Group) -> str:

                element_node = section_group.get("ElementType")

        return Zone(name=zone_name, sections=sections)        if element_node is not None:

            dataset = self._resolve_data_array(element_node)

    def _read_coordinates(self, zone_node: list) -> np.ndarray:            return self._decode_dataset(dataset)

        """读取 Zone 的网格坐标。

                name_candidate = self._extract_name_token(section_group)

        Args:        if name_candidate is not None:

            zone_node: Zone_t 节点            return name_candidate

            

        Returns:        type_node = section_group.get(" data")

            形状为 (n_points, 3) 的坐标数组        if isinstance(type_node, h5py.Dataset) and type_node.size:

        """            code = int(type_node[0])

        # 查找 GridCoordinates_t 节点            element_type = _ELEMENT_TYPE_BY_CODE.get(code)

        grid_coords = self._get_children_by_type(zone_node, 'GridCoordinates_t')            if element_type in _SUPPORTED_ELEMENT_SIZES:

        if not grid_coords:                return element_type

            msg = f"No GridCoordinates found in zone {zone_node[0]}"

            raise ValueError(msg)        if name_candidate is None:

                    name_candidate = self._extract_name_token(section_group, use_path=True)

        coords_node = grid_coords[0]            if name_candidate is not None:

                        return name_candidate

        # 读取 X, Y, Z 坐标

        x_node = self._get_child_by_name(coords_node, 'CoordinateX')        raise ValueError(f"Unable to determine element type for {section_group.name}")

        y_node = self._get_child_by_name(coords_node, 'CoordinateY')

        z_node = self._get_child_by_name(coords_node, 'CoordinateZ')    def _attach_boundary_metadata(

                self,

        if not all([x_node, y_node, z_node]):        zone_group: h5py.Group,

            msg = f"Missing coordinate data in zone {zone_node[0]}"        base_group: h5py.Group,

            raise ValueError(msg)        section_lookup: dict[str, list[Section]],

            ) -> None:

        x = x_node[1] if x_node[1] is not None else np.array([])        zone_bc = zone_group.get("ZoneBC")

        y = y_node[1] if y_node[1] is not None else np.array([])        if not isinstance(zone_bc, h5py.Group):

        z = z_node[1] if z_node[1] is not None else np.array([])            return

        

        # 组合成 (n, 3) 数组        families = self._collect_families(base_group)

        return np.column_stack([x, y, z])        for bc_name, bc_group in self._iter_children(zone_bc, "BC_t"):

            candidates = [

    def _read_section(self, elem_node: list, points: np.ndarray, section_id: int) -> Section | None:                self._clean_name(bc_group.attrs.get("name")),

        """读取 Elements_t 节点并创建 Section。                self._clean_name(bc_name),

                    ]

        Args:            section: Section | None = None

            elem_node: Elements_t 节点            resolved_name = ""

            points: 网格坐标点            for candidate in candidates:

            section_id: Section ID                key = self._normalize_key(candidate)

                            if key and key in section_lookup and section_lookup[key]:

        Returns:                    section = section_lookup[key].pop(0)

            Section 对象，如果元素类型不支持则返回 None                    resolved_name = candidate or section.name

        """                    if not section_lookup[key]:

        section_name = elem_node[0]                        section_lookup.pop(key, None)

                            break

        # 获取元素类型（ElementType）

        elem_type_node = self._get_child_by_name(elem_node, 'ElementType')            if section is None:

        if not elem_type_node or elem_type_node[1] is None:                continue

            return None

                    grid_location = self._read_grid_location(bc_group)

        elem_type_code = int(elem_type_node[1])            family_name = self._read_family_name(bc_group, families)

        elem_type_name = _ELEMENT_TYPE_BY_CODE.get(elem_type_code)            section.boundary = BoundaryInfo(

                        name=family_name or resolved_name or section.name,

        if not elem_type_name:                grid_location=grid_location,

            # 不支持的元素类型，跳过            )

            return None

            @staticmethod

        # 获取元素连接性（ElementConnectivity）    def _extract_name_token(section_group: h5py.Group, use_path: bool = False) -> str | None:

        connectivity_node = self._get_child_by_name(elem_node, 'ElementConnectivity')        if use_path:

        if not connectivity_node or connectivity_node[1] is None:            raw_name = section_group.name.rsplit("/", maxsplit=1)[-1]

            return None        else:

                    raw_name = section_group.attrs.get("name")

        connectivity_flat = connectivity_node[1]            if isinstance(raw_name, bytes):

                        raw_name = raw_name.decode("utf-8", errors="ignore")

        # 获取元素范围（ElementRange）

        elem_range_node = self._get_child_by_name(elem_node, 'ElementRange')        if isinstance(raw_name, str):

        if elem_range_node and elem_range_node[1] is not None:            upper = raw_name.upper()

            elem_range = tuple(elem_range_node[1])            for element_type in _SUPPORTED_ELEMENT_SIZES:

        else:                token = element_type.split("_")[0]

            elem_range = (1, len(connectivity_flat) // _SUPPORTED_ELEMENT_SIZES[elem_type_name])                if token in upper:

                            return element_type

        # 重塑连接性数组        return None

        nodes_per_elem = _SUPPORTED_ELEMENT_SIZES[elem_type_name]

        n_elements = (elem_range[1] - elem_range[0] + 1)    @staticmethod

            def _clean_name(value: str | bytes | None) -> str:

        try:        if isinstance(value, bytes):

            connectivity = connectivity_flat.reshape(n_elements, nodes_per_elem)            value = value.decode("utf-8", errors="ignore")

            # CGNS 索引从 1 开始，转换为从 0 开始        if not isinstance(value, str):

            connectivity = connectivity - 1            return ""

        except ValueError:        tokens = value.strip().split()

            # 如果 reshape 失败，跳过这个 section        return " ".join(tokens)

            return None

            @staticmethod

        # 创建 MeshData    def _normalize_key(name: str | bytes | None) -> str:

        mesh = MeshData(        clean = CgnsLoader._clean_name(name)

            points=points,        return clean.upper() if clean else ""

            connectivity=connectivity,

            cell_type=elem_type_name    def _read_grid_location(self, bc_group: h5py.Group) -> str | None:

        )        node = bc_group.get("GridLocation")

                if node is None:

        # 清理名称            return None

        clean_name = self._clean_name(section_name)        dataset = self._resolve_data_array(node)

                return self._decode_character_array(dataset)

        return Section(

            id=section_id,    def _read_family_name(self, bc_group: h5py.Group, families: dict[str, str]) -> str | None:

            name=clean_name or section_name,        node = bc_group.get("FamilyName")

            element_type=elem_type_name,        if node is not None:

            range=elem_range,            dataset = self._resolve_data_array(node)

            mesh=mesh            name = self._decode_character_array(dataset)

        )            clean = self._clean_name(name)

            if clean:

    def _attach_boundary_metadata(                mapped = families.get(self._normalize_key(clean))

        self,                return mapped or clean

        zone_node: list,

        base_node: list,        data_node = bc_group.get(" data")

        section_lookup: dict[str, list[Section]]        if isinstance(data_node, h5py.Dataset):

    ) -> None:            inferred = self._decode_character_array(data_node)

        """读取边界条件并关联到对应的 sections。            clean = self._clean_name(inferred)

                    if clean:

        Args:                mapped = families.get(self._normalize_key(clean))

            zone_node: Zone_t 节点                return mapped or clean

            base_node: 父 CGNSBase_t 节点

            section_lookup: section 名称到 Section 对象的映射        for key in (

        """            self._normalize_key(bc_group.attrs.get("name")),

        # 查找 ZoneBC_t 容器            self._normalize_key(bc_group.name.rsplit("/", 1)[-1]),

        zonebc_containers = self._get_children_by_type(zone_node, 'ZoneBC_t')        ):

        if not zonebc_containers:            if key and key in families:

            return                return families[key]

                return None

        # 遍历所有 BC_t 节点

        for zonebc in zonebc_containers:    def _collect_families(self, base_group: h5py.Group) -> dict[str, str]:

            for bc_node in self._get_children_by_type(zonebc, 'BC_t'):        families: dict[str, str] = {}

                self._process_boundary_condition(bc_node, base_node, section_lookup)        for family_name, family_group in self._iter_children(base_group, "Family_t"):

            cleaned_attr = self._clean_name(family_group.attrs.get("name"))

    def _process_boundary_condition(            group_clean = self._clean_name(family_name)

        self,            display = cleaned_attr or group_clean or family_name

        bc_node: list,            candidates = (

        base_node: list,                cleaned_attr,

        section_lookup: dict[str, list[Section]]                family_group.attrs.get("name"),

    ) -> None:                family_name,

        """处理单个边界条件节点。"""                group_clean,

        bc_name = bc_node[0]            )

                    for candidate in candidates:

        # 读取 GridLocation（默认为 Vertex）                key = self._normalize_key(candidate)

        grid_location = "Vertex"                if key and key not in families:

        gl_node = self._get_child_by_name(bc_node, 'GridLocation')                    families[key] = display

        if gl_node and gl_node[1] is not None:        return families

            # GridLocation 是一个字符串

            gl_value = gl_node[1]    @staticmethod

            if isinstance(gl_value, bytes):    def _resolve_data_array(node: h5py.Dataset | h5py.Group) -> h5py.Dataset:

                grid_location = gl_value.decode('utf-8').strip()        if isinstance(node, h5py.Dataset):

            elif isinstance(gl_value, str):            return node

                grid_location = gl_value.strip()        if isinstance(node, h5py.Group):

                    dataset = node.get(" data")

        # 读取 FamilyName            if isinstance(dataset, h5py.Dataset):

        family_name = None                return dataset

        family_node = self._get_child_by_name(bc_node, 'FamilyName')        raise ValueError(f"Unsupported CGNS data array layout at {node}")

        if family_node and family_node[1] is not None:

            fn_value = family_node[1]    @staticmethod

            if isinstance(fn_value, bytes):    def _decode_character_array(dataset: h5py.Dataset) -> str:

                family_name = fn_value.decode('utf-8').strip()        array = np.asarray(dataset)

            elif isinstance(fn_value, str):        if array.dtype.kind in {"S", "a"}:

                family_name = fn_value.strip()            return b"".join(part.rstrip(b"\x00") for part in array.flatten()).decode(

                        "utf-8",

        # 创建 BoundaryInfo                errors="ignore",

        boundary_info = BoundaryInfo(            ).strip()

            name=bc_name,        if array.dtype.kind == "U":

            family=family_name,            return "".join(array.flatten()).strip()

            bc_type=None,  # 可以从 BC_t 的 value 读取        if array.dtype.kind in {"i", "u"}:

            grid_location=grid_location            chars = [chr(int(value)) for value in array.flatten() if int(value) != 0]

        )            return "".join(chars).strip()

                value = dataset[()]

        # 尝试关联到 section        if isinstance(value, bytes):

        # 1. 精确匹配 BC 名称            return value.decode("utf-8", errors="ignore").strip()

        key = self._normalize_key(bc_name)        if isinstance(value, np.ndarray):

        if key in section_lookup:            return "".join(map(str, value.flatten())).strip()

            for section in section_lookup[key]:        return str(value).strip()

                section.boundary = boundary_info
            return
        
        # 2. 如果有 FamilyName，尝试匹配
        if family_name:
            family_key = self._normalize_key(family_name)
            if family_key in section_lookup:
                for section in section_lookup[family_key]:
                    section.boundary = boundary_info

    @staticmethod
    def _clean_name(name: str) -> str:
        """清理名称，移除空格前的部分。"""
        if " " in name:
            return name.split(" ", 1)[1]
        return name

    @staticmethod
    def _normalize_key(name: str) -> str:
        """规范化名称用于查找。"""
        return name.lower().replace(" ", "").replace("_", "").replace("-", "")
