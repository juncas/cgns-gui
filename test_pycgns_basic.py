"""测试 pyCGNS 基本功能的脚本。"""
import sys
from pathlib import Path

try:
    from CGNS import MAP as cgnsmap
    from CGNS import PAT as cgnspat
    print("✓ pyCGNS 导入成功")
    print(f"  CGNS.MAP 版本: {cgnsmap.__version__ if hasattr(cgnsmap, '__version__') else '未知'}")
except ImportError as e:
    print(f"✗ pyCGNS 未安装或导入失败: {e}")
    print("\n请使用以下命令安装:")
    print("  conda install -c conda-forge pycgns")
    sys.exit(1)

# 测试 CGNS 文件加载
def test_load_cgns(cgns_file):
    """测试加载 CGNS 文件并打印基本结构。"""
    print(f"\n正在加载 CGNS 文件: {cgns_file}")
    
    if not Path(cgns_file).exists():
        print(f"✗ 文件不存在: {cgns_file}")
        return
    
    try:
        # 使用 CGNS.MAP 加载文件
        tree, links, paths = cgnsmap.load(str(cgns_file))
        print("✓ CGNS 文件加载成功")
        
        # 打印树的基本信息
        print(f"\n根节点: {tree[0]}")
        print(f"根节点类型: {tree[3]}")
        print(f"子节点数量: {len(tree[2])}")
        
        # 遍历 CGNSBase 节点
        print("\n=== CGNSBase 节点 ===")
        for base in tree[2]:
            if base[3] in ['CGNSBase_t', 'Base_t']:
                print(f"\nBase 名称: {base[0]}")
                print(f"Base 类型: {base[3]}")
                if base[1] is not None:
                    print(f"Base 数据: {base[1]}")
                
                # 遍历 Zone 节点
                print("\n  --- Zone 节点 ---")
                for zone in base[2]:
                    if zone[3] == 'Zone_t':
                        print(f"  Zone 名称: {zone[0]}")
                        if zone[1] is not None:
                            print(f"  Zone 尺寸: {zone[1]}")
                        
                        # 查找 Elements_t 节点
                        elements = [n for n in zone[2] if n[3] == 'Elements_t']
                        print(f"  Elements 数量: {len(elements)}")
                        for elem in elements[:3]:  # 只显示前3个
                            print(f"    - {elem[0]}: 类型={elem[3]}")
                        
                        # 查找 ZoneBC_t 节点
                        zonebc = [n for n in zone[2] if n[3] == 'ZoneBC_t']
                        if zonebc:
                            print(f"  边界条件节点 (ZoneBC_t): {len(zonebc)}")
                            for bc_container in zonebc:
                                bcs = [n for n in bc_container[2] if n[3] == 'BC_t']
                                print(f"    边界条件数量: {len(bcs)}")
                                for bc in bcs[:3]:  # 只显示前3个
                                    print(f"      - {bc[0]}")
                        
                        # 查找 FlowSolution_t 节点
                        flowsol = [n for n in zone[2] if n[3] == 'FlowSolution_t']
                        if flowsol:
                            print(f"  流场解节点 (FlowSolution_t): {len(flowsol)}")
                            for fs in flowsol[:2]:  # 只显示前2个
                                print(f"    - {fs[0]}")
                        
                        # 查找 Family_t 关联
                        family_name = [n for n in zone[2] if n[0] == 'FamilyName']
                        if family_name:
                            print(f"  Family 关联: {family_name[0][1] if family_name[0][1] is not None else 'N/A'}")
        
        print("\n✓ 树结构打印完成")
        return tree
        
    except Exception as e:
        print(f"✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 如果提供了命令行参数，使用它作为 CGNS 文件路径
    if len(sys.argv) > 1:
        cgns_file = sys.argv[1]
    else:
        # 否则提示用户
        print("\n使用方法:")
        print("  python test_pycgns_basic.py <cgns_file_path>")
        print("\n示例:")
        print("  python test_pycgns_basic.py test.cgns")
        sys.exit(0)
    
    test_load_cgns(cgns_file)
