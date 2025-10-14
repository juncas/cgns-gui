#!/usr/bin/env python
"""
创建一个包含流场解的 CGNS 测试文件
使用 CGNS/Python 树格式手动构建
"""

import numpy as np
from CGNS import MAP as cgnsmap


def create_cgns_tree_with_solution(filename='test_with_solution.cgns'):
    """
    创建一个包含网格和流场解的 CGNS 文件
    使用 CGNS/Python 树结构: [name, value, children, type]
    """
    
    # 创建根节点
    tree = ['CGNSTree', None, [], 'CGNSTree_t']
    
    # 添加 CGNSLibraryVersion
    cgns_version = ['CGNSLibraryVersion', np.array([3.3], dtype='f4'), [], 'CGNSLibraryVersion_t']
    tree[2].append(cgns_version)
    
    # 创建 Base (3D, 3 个物理维度)
    base = ['Base', np.array([3, 3], dtype='i4'), [], 'CGNSBase_t']
    
    # 创建非结构化 Zone (10个顶点, 4个四面体单元)
    n_vertices = 10
    n_cells = 4
    zone_size = np.array([[n_vertices, n_cells, 0]], dtype='i4')
    zone = ['Zone1', zone_size, [], 'Zone_t']
    
    # ZoneType = Unstructured
    zone_type = ['ZoneType', np.array(['Unstructured'], dtype='S'), [], 'ZoneType_t']
    zone[2].append(zone_type)
    
    # GridCoordinates
    grid_coords = ['GridCoordinates', None, [], 'GridCoordinates_t']
    
    # 创建一个简单的网格 (10个点构成的区域)
    x = np.array([0., 1., 2., 0., 1., 2., 0., 1., 2., 1.], dtype='f8')
    y = np.array([0., 0., 0., 1., 1., 1., 2., 2., 2., 1.5], dtype='f8')
    z = np.array([0., 0., 0., 0., 0., 0., 0., 0., 0., 1.], dtype='f8')
    
    coord_x = ['CoordinateX', x, [], 'DataArray_t']
    coord_y = ['CoordinateY', y, [], 'DataArray_t']
    coord_z = ['CoordinateZ', z, [], 'DataArray_t']
    
    grid_coords[2].extend([coord_x, coord_y, coord_z])
    zone[2].append(grid_coords)
    
    # Elements (4个四面体)
    # TETRA_4 的元素类型代码是 10
    elements = ['Elements', np.array([10], dtype='i4'), [], 'Elements_t']
    
    # ElementRange
    elem_range = ['ElementRange', np.array([1, 4], dtype='i4'), [], 'IndexRange_t']
    elements[2].append(elem_range)
    
    # ElementConnectivity (1-based indexing)
    connectivity = np.array([
        1, 2, 4, 10,  # Tetra 1
        2, 3, 5, 10,  # Tetra 2
        4, 5, 7, 10,  # Tetra 3
        5, 6, 8, 10,  # Tetra 4
    ], dtype='i4')
    elem_conn = ['ElementConnectivity', connectivity, [], 'DataArray_t']
    elements[2].append(elem_conn)
    
    zone[2].append(elements)
    
    # 添加边界条件
    zone_bc = ['ZoneBC', None, [], 'ZoneBC_t']
    
    # 壁面边界条件 (底面的点)
    bc_wall = ['Wall', None, [], 'BC_t']
    bc_type = ['BCType', np.array(['BCWall'], dtype='S'), [], 'BCType_t']
    bc_wall[2].append(bc_type)
    
    # PointList (底面的点: 1,2,3,4,5,6)
    point_list = ['PointList', np.array([[1, 2, 3, 4, 5, 6]], dtype='i4'), [], 'IndexArray_t']
    bc_wall[2].append(point_list)
    
    # GridLocation
    grid_loc = ['GridLocation', np.array(['Vertex'], dtype='S'), [], 'GridLocation_t']
    bc_wall[2].append(grid_loc)
    
    zone_bc[2].append(bc_wall)
    zone[2].append(zone_bc)
    
    # 添加 FlowSolution (流场解)
    flow_solution = ['FlowSolution', None, [], 'FlowSolution_t']
    
    # GridLocation (Vertex-centered solution)
    grid_loc_sol = ['GridLocation', np.array(['Vertex'], dtype='S'), [], 'GridLocation_t']
    flow_solution[2].append(grid_loc_sol)
    
    # Pressure (在每个顶点)
    pressure = np.array([101325., 101320., 101315., 
                        101330., 101325., 101320., 
                        101335., 101330., 101325., 
                        101300.], dtype='f8')
    pressure_node = ['Pressure', pressure, [], 'DataArray_t']
    flow_solution[2].append(pressure_node)
    
    # Density
    density = np.array([1.225, 1.225, 1.225,
                       1.224, 1.224, 1.224,
                       1.223, 1.223, 1.223,
                       1.220], dtype='f8')
    density_node = ['Density', density, [], 'DataArray_t']
    flow_solution[2].append(density_node)
    
    # VelocityX
    velocity_x = np.array([10., 10.5, 11.,
                           9.5, 10., 10.5,
                           9., 9.5, 10.,
                           8.], dtype='f8')
    velocity_x_node = ['VelocityX', velocity_x, [], 'DataArray_t']
    flow_solution[2].append(velocity_x_node)
    
    # VelocityY
    velocity_y = np.array([0., 0.1, 0.2,
                           0.1, 0.2, 0.3,
                           0.2, 0.3, 0.4,
                           0.5], dtype='f8')
    velocity_y_node = ['VelocityY', velocity_y, [], 'DataArray_t']
    flow_solution[2].append(velocity_y_node)
    
    # VelocityZ
    velocity_z = np.array([0., 0., 0.,
                           0., 0., 0.,
                           0., 0., 0.,
                           0.2], dtype='f8')
    velocity_z_node = ['VelocityZ', velocity_z, [], 'DataArray_t']
    flow_solution[2].append(velocity_z_node)
    
    zone[2].append(flow_solution)
    
    # 添加 Zone 到 Base
    base[2].append(zone)
    
    # 添加 Base 到 tree
    tree[2].append(base)
    
    # 保存文件
    cgnsmap.save(filename, tree)
    print(f"✓ 成功创建包含流场解的 CGNS 文件: {filename}")
    print(f"  - {n_vertices} 个顶点")
    print(f"  - {n_cells} 个四面体单元")
    print(f"  - 1 个边界条件 (Wall)")
    print(f"  - FlowSolution 包含: Pressure, Density, VelocityX, VelocityY, VelocityZ")
    
    return filename


def create_structured_grid_with_solution(filename='test_structured_solution.cgns'):
    """创建一个结构化网格并包含流场解"""
    
    # 创建根节点
    tree = ['CGNSTree', None, [], 'CGNSTree_t']
    
    # CGNSLibraryVersion
    cgns_version = ['CGNSLibraryVersion', np.array([3.3], dtype='f4'), [], 'CGNSLibraryVersion_t']
    tree[2].append(cgns_version)
    
    # Base
    base = ['Base', np.array([3, 3], dtype='i4'), [], 'CGNSBase_t']
    
    # 结构化 Zone (5x5x3 = 75 个顶点)
    ni, nj, nk = 5, 5, 3
    zone_size = np.array([[ni, nj, nk],      # 顶点数
                          [ni-1, nj-1, nk-1], # 单元数
                          [0, 0, 0]], dtype='i4')
    zone = ['StructuredZone', zone_size, [], 'Zone_t']
    
    # ZoneType = Structured
    zone_type = ['ZoneType', np.array(['Structured'], dtype='S'), [], 'ZoneType_t']
    zone[2].append(zone_type)
    
    # GridCoordinates
    grid_coords = ['GridCoordinates', None, [], 'GridCoordinates_t']
    
    # 创建网格坐标
    x = np.zeros((ni, nj, nk), dtype='f8')
    y = np.zeros((ni, nj, nk), dtype='f8')
    z = np.zeros((ni, nj, nk), dtype='f8')
    
    for i in range(ni):
        for j in range(nj):
            for k in range(nk):
                x[i, j, k] = i * 0.5
                y[i, j, k] = j * 0.5
                z[i, j, k] = k * 0.3
    
    coord_x = ['CoordinateX', x, [], 'DataArray_t']
    coord_y = ['CoordinateY', y, [], 'DataArray_t']
    coord_z = ['CoordinateZ', z, [], 'DataArray_t']
    
    grid_coords[2].extend([coord_x, coord_y, coord_z])
    zone[2].append(grid_coords)
    
    # FlowSolution
    flow_solution = ['FlowSolution', None, [], 'FlowSolution_t']
    
    # GridLocation
    grid_loc = ['GridLocation', np.array(['Vertex'], dtype='S'), [], 'GridLocation_t']
    flow_solution[2].append(grid_loc)
    
    # 创建流场数据 (随空间变化的压力和速度场)
    pressure = 101325.0 + 100.0 * np.sin(x * 2.0) * np.cos(y * 2.0)
    density = 1.225 - 0.005 * z
    velocity_x = 10.0 + 2.0 * np.sin(y * 1.5)
    velocity_y = 0.5 * np.cos(x * 1.5)
    velocity_z = 0.1 * (z - 1.0)
    
    pressure_node = ['Pressure', pressure, [], 'DataArray_t']
    density_node = ['Density', density, [], 'DataArray_t']
    velocity_x_node = ['VelocityX', velocity_x, [], 'DataArray_t']
    velocity_y_node = ['VelocityY', velocity_y, [], 'DataArray_t']
    velocity_z_node = ['VelocityZ', velocity_z, [], 'DataArray_t']
    
    flow_solution[2].extend([pressure_node, density_node, 
                            velocity_x_node, velocity_y_node, velocity_z_node])
    
    zone[2].append(flow_solution)
    
    # 添加边界条件
    zone_bc = ['ZoneBC', None, [], 'ZoneBC_t']
    
    # Inlet (i=0 面)
    bc_inlet = ['Inlet', None, [], 'BC_t']
    bc_type_inlet = ['BCType', np.array(['BCInflow'], dtype='S'), [], 'BCType_t']
    bc_inlet[2].append(bc_type_inlet)
    
    # PointRange for i=0 面
    point_range = ['PointRange', np.array([[1, 1], [1, nj], [1, nk]], dtype='i4'), [], 'IndexRange_t']
    bc_inlet[2].append(point_range)
    
    zone_bc[2].append(bc_inlet)
    
    # Outlet (i=ni 面)
    bc_outlet = ['Outlet', None, [], 'BC_t']
    bc_type_outlet = ['BCType', np.array(['BCOutflow'], dtype='S'), [], 'BCType_t']
    bc_outlet[2].append(bc_type_outlet)
    
    point_range_out = ['PointRange', np.array([[ni, ni], [1, nj], [1, nk]], dtype='i4'), [], 'IndexRange_t']
    bc_outlet[2].append(point_range_out)
    
    zone_bc[2].append(bc_outlet)
    
    zone[2].append(zone_bc)
    
    # 添加到 Base 和 tree
    base[2].append(zone)
    tree[2].append(base)
    
    # 保存
    cgnsmap.save(filename, tree)
    print(f"✓ 成功创建结构化网格 CGNS 文件: {filename}")
    print(f"  - {ni}x{nj}x{nk} = {ni*nj*nk} 个顶点")
    print(f"  - {(ni-1)*(nj-1)*(nk-1)} 个六面体单元")
    print(f"  - 2 个边界条件 (Inlet, Outlet)")
    print(f"  - FlowSolution 包含: Pressure, Density, Velocity[XYZ]")
    
    return filename


if __name__ == '__main__':
    print("=" * 60)
    print("创建 CGNS 测试文件（包含流场解）")
    print("=" * 60)
    print()
    
    try:
        # 创建非结构化网格 + 流场解
        file1 = create_cgns_tree_with_solution('test_with_solution.cgns')
        print()
        
        # 创建结构化网格 + 流场解
        file2 = create_structured_grid_with_solution('test_structured_solution.cgns')
        print()
        
        print("=" * 60)
        print("✓ 所有测试文件创建成功！")
        print("=" * 60)
        print()
        print("下一步测试命令：")
        print(f"  python test_pycgns_basic.py {file1}")
        print(f"  python test_pycgns_basic.py {file2}")
        print()
        
    except Exception as e:
        print(f"✗ 创建失败: {e}")
        import traceback
        traceback.print_exc()
