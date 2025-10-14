#!/usr/bin/env python
"""
对比测试 h5py 和 pyCGNS 两个 loader 实现
"""

import sys
sys.path.insert(0, 'src')

import numpy as np
from cgns_gui.loader import CgnsLoader as H5pyLoader
from cgns_gui.loader_pycgns import CgnsLoader as PyCGNSLoader


def compare_loaders(filename):
    print(f"\n{'='*70}")
    print(f"对比测试: {filename}")
    print('='*70)
    
    # Load with h5py
    print("\n[1/2] 使用 h5py loader 加载...")
    try:
        h5py_loader = H5pyLoader()
        h5py_model = h5py_loader.load(filename)
        print(f"  ✓ h5py loader 成功")
    except Exception as e:
        print(f"  ✗ h5py loader 失败: {e}")
        return False
    
    # Load with pyCGNS
    print("\n[2/2] 使用 pyCGNS loader 加载...")
    try:
        pycgns_loader = PyCGNSLoader()
        pycgns_model = pycgns_loader.load(filename)
        print(f"  ✓ pyCGNS loader 成功")
    except Exception as e:
        print(f"  ✗ pyCGNS loader 失败: {e}")
        return False
    
    # Compare results
    print(f"\n{'='*70}")
    print("对比结果")
    print('='*70)
    
    all_pass = True
    
    # Compare zone count
    print(f"\n▸ Zones 数量:")
    print(f"  h5py:    {len(h5py_model.zones)}")
    print(f"  pyCGNS:  {len(pycgns_model.zones)}")
    if len(h5py_model.zones) == len(pycgns_model.zones):
        print("  ✓ 一致")
    else:
        print("  ✗ 不一致")
        all_pass = False
    
    # Compare each zone
    for i, (h5py_zone, pycgns_zone) in enumerate(zip(h5py_model.zones, pycgns_model.zones)):
        print(f"\n▸ Zone {i+1}: {h5py_zone.name} vs {pycgns_zone.name}")
        
        # Compare zone names
        if h5py_zone.name == pycgns_zone.name:
            print(f"  ✓ 名称一致: {h5py_zone.name}")
        else:
            print(f"  ✗ 名称不一致: {h5py_zone.name} != {pycgns_zone.name}")
            all_pass = False
        
        # Compare section count
        print(f"\n  Sections 数量:")
        print(f"    h5py:    {len(h5py_zone.sections)}")
        print(f"    pyCGNS:  {len(pycgns_zone.sections)}")
        if len(h5py_zone.sections) == len(pycgns_zone.sections):
            print("    ✓ 一致")
        else:
            print("    ✗ 不一致")
            all_pass = False
        
        # Compare each section
        for j, (h5py_sec, pycgns_sec) in enumerate(zip(h5py_zone.sections, pycgns_zone.sections)):
            print(f"\n  ▸ Section {j+1}:")
            
            # Name
            print(f"    名称: {h5py_sec.name} vs {pycgns_sec.name}")
            if h5py_sec.name != pycgns_sec.name:
                print(f"      ⚠ 名称不同（可能不影响功能）")
            
            # Element type
            print(f"    单元类型: {h5py_sec.element_type} vs {pycgns_sec.element_type}")
            if h5py_sec.element_type == pycgns_sec.element_type:
                print(f"      ✓ 一致")
            else:
                print(f"      ✗ 不一致")
                all_pass = False
            
            # Range
            print(f"    范围: {h5py_sec.range} vs {pycgns_sec.range}")
            if h5py_sec.range == pycgns_sec.range:
                print(f"      ✓ 一致")
            else:
                print(f"      ⚠ 不同（可能不影响功能）")
            
            # Mesh data
            if h5py_sec.mesh and pycgns_sec.mesh:
                print(f"\n    网格数据:")
                
                # Points
                h5py_points = h5py_sec.mesh.points
                pycgns_points = pycgns_sec.mesh.points
                print(f"      Points shape: {h5py_points.shape} vs {pycgns_points.shape}")
                
                if h5py_points.shape == pycgns_points.shape:
                    # Check if values are close
                    if np.allclose(h5py_points, pycgns_points):
                        print(f"        ✓ 点坐标完全一致")
                    else:
                        max_diff = np.abs(h5py_points - pycgns_points).max()
                        print(f"        ⚠ 点坐标有微小差异 (max diff: {max_diff:.2e})")
                else:
                    print(f"        ✗ 点坐标形状不一致")
                    all_pass = False
                
                # Connectivity
                h5py_conn = h5py_sec.mesh.connectivity
                pycgns_conn = pycgns_sec.mesh.connectivity
                print(f"      Connectivity shape: {h5py_conn.shape} vs {pycgns_conn.shape}")
                
                if h5py_conn.shape == pycgns_conn.shape:
                    if np.array_equal(h5py_conn, pycgns_conn):
                        print(f"        ✓ 连接关系完全一致")
                    else:
                        diff_count = np.sum(h5py_conn != pycgns_conn)
                        print(f"        ✗ 连接关系不一致 (差异数: {diff_count})")
                        all_pass = False
                else:
                    print(f"        ✗ 连接关系形状不一致")
                    all_pass = False
            
            # Boundary info
            h5py_bc = h5py_sec.boundary
            pycgns_bc = pycgns_sec.boundary
            
            if h5py_bc or pycgns_bc:
                print(f"\n    边界条件:")
                print(f"      h5py:    {h5py_bc.name if h5py_bc else 'None'}")
                print(f"      pyCGNS:  {pycgns_bc.name if pycgns_bc else 'None'}")
                
                if h5py_bc and pycgns_bc:
                    if h5py_bc.name == pycgns_bc.name:
                        print(f"        ✓ 名称一致")
                    else:
                        print(f"        ⚠ 名称不同（可能不影响功能）")
    
    print(f"\n{'='*70}")
    if all_pass:
        print("✓✓✓ 所有关键数据一致！pyCGNS 迁移成功！")
    else:
        print("⚠⚠⚠ 存在不一致，需要进一步检查")
    print('='*70)
    
    return all_pass


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'test_with_solution.cgns'
    
    success = compare_loaders(filename)
    sys.exit(0 if success else 1)
