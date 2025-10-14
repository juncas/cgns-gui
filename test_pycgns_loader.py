#!/usr/bin/env python
"""
测试新的 pyCGNS loader 实现
"""

import sys
sys.path.insert(0, 'src')

from cgns_gui.loader_pycgns import CgnsLoader


def test_pycgns_loader(filename):
    print(f"\n{'='*60}")
    print(f"测试 pyCGNS Loader: {filename}")
    print('='*60)
    
    try:
        loader = CgnsLoader()
        model = loader.load(filename)
        
        print(f"✓ 文件加载成功")
        print(f"\nZones 数量: {len(model.zones)}")
        
        for zone in model.zones:
            print(f"\n  Zone: {zone.name}")
            print(f"  Sections 数量: {len(zone.sections)}")
            
            for section in zone.sections:
                print(f"\n    Section: {section.name}")
                print(f"      ID: {section.id}")
                print(f"      Element Type: {section.element_type}")
                print(f"      Range: {section.range}")
                
                if section.mesh:
                    print(f"      Points shape: {section.mesh.points.shape}")
                    print(f"      Connectivity shape: {section.mesh.connectivity.shape}")
                    print(f"      Cell Type: {section.mesh.cell_type}")
                
                if section.boundary:
                    print(f"      Boundary: {section.boundary.name}")
                    print(f"      Grid Location: {section.boundary.grid_location}")
        
        print(f"\n{'='*60}")
        print("✓ pyCGNS Loader 测试通过")
        print('='*60)
        return True
        
    except Exception as e:
        print(f"\n✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'test_with_solution.cgns'
    
    success = test_pycgns_loader(filename)
    sys.exit(0 if success else 1)
