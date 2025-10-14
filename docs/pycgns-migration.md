# pyCGNS 迁移指南

## 概述

本项目已从使用 `h5py` 直接读取 CGNS 文件迁移到使用 `pyCGNS` 库。pyCGNS 提供完整的 CGNS/SIDS 标准支持，能够正确处理边界条件、Family 分组、FlowSolution 等复杂节点结构。

## 为什么迁移到 pyCGNS？

### 优势
1. **完整的 CGNS/SIDS 支持**：pyCGNS 实现了完整的 CGNS 标准，不会丢失数据
2. **标准化 API**：符合 CGNS 社区的最佳实践
3. **边界条件支持**：正确解析 `ZoneBC_t`、`BC_t`、`Family_t` 等节点
4. **为流场数据做准备**：`FlowSolution_t` 支持更容易实现
5. **CFD 社区标准**：大多数 CFD 工具使用相同的库

### h5py 方式的局限
- 需要手动解析每种 CGNS 节点类型
- 容易遗漏 CGNS/SIDS 标准的细节
- 无法处理复杂的节点关系（如 Family 关联）

## 安装 pyCGNS

### 使用 Conda（推荐）

pyCGNS 在 conda-forge 有预编译的二进制包，支持 Windows、Linux 和 macOS：

```bash
# 安装 pyCGNS
conda install -c conda-forge pycgns

# 或者创建新环境
conda create -n cgns-gui python=3.10
conda activate cgns-gui
conda install -c conda-forge pycgns pyside6 vtk h5py numpy pytest ruff
```

### 从源码安装（高级用户）

如果需要从源码安装（不推荐），需要以下依赖：
- HDF5 开发库（C 语言）
- Meson 构建系统
- C 编译器（GCC 或 MSVC）

```bash
# Linux
sudo apt-get install libhdf5-dev

# 然后
pip install pycgns
```

**注意**：Windows 上从源码安装比较困难，强烈建议使用 conda。

## API 变化

### 加载文件

**旧方式（h5py）**：
```python
import h5py

with h5py.File(path, 'r') as f:
    # 手动遍历 HDF5 群组
    for base_name, base_group in f.items():
        # ...
```

**新方式（pyCGNS）**：
```python
from CGNS import MAP as cgnsmap

tree, links, paths = cgnsmap.load(str(path))
# tree 是 CGNS/Python 树结构 [name, value, children, type]
```

### 节点访问

**CGNS/Python 树节点结构**：
```python
node = [name, value, children, type]
# name: 字符串
# value: numpy 数组或 None
# children: 子节点列表
# type: CGNS 节点类型字符串（如 'Zone_t', 'Elements_t'）
```

**示例**：
```python
# 获取子节点
for child in node[2]:  # children
    if child[3] == 'Zone_t':  # type
        zone_name = child[0]  # name
        zone_data = child[1]  # value
```

### 边界条件

新的实现完整保留边界条件信息：
- `GridLocation`：边界位置（Vertex, FaceCenter 等）
- `FamilyName`：Family 分组关联
- `BC_t` 类型：边界条件类型

### 数据模型变化

`BoundaryInfo` 增强：
```python
@dataclass
class BoundaryInfo:
    name: str
    family: str | None = None
    bc_type: str | None = None
    grid_location: str = "Vertex"  # 新增
```

## 测试迁移

### 1. 基本功能测试

使用测试脚本验证 pyCGNS 安装：

```bash
python test_pycgns_basic.py your_file.cgns
```

### 2. 运行单元测试

```bash
pytest tests/test_loader.py -v
```

### 3. GUI 测试

```bash
python -m cgns_gui.app
```

加载 CGNS 文件，验证：
- 网格渲染正常
- Section 选择和高亮功能
- 边界条件显示（在属性面板中）
- 无性能退化

## 已知问题

### 1. CGNS 元素类型代码

pyCGNS 使用的元素类型代码与 h5py 直接读取可能不同：

| 元素类型 | pyCGNS 代码 | 说明 |
|---------|------------|------|
| BAR_2   | 3          | 线单元 |
| TRI_3   | 5          | 三角形 |
| QUAD_4  | 7          | 四边形 |
| TETRA_4 | 10         | 四面体 |
| PYRA_5  | 12         | 金字塔 |
| PENTA_6 | 14         | 三棱柱 |
| HEXA_8  | 17         | 六面体 |

**如果遇到不支持的元素类型**，检查 `_ELEMENT_TYPE_BY_CODE` 映射表。

### 2. 索引约定

CGNS 标准使用 **1-based 索引**，而 VTK 和 numpy 使用 **0-based 索引**。

新的 loader 自动处理转换：
```python
connectivity = connectivity_flat.reshape(n_elements, nodes_per_elem)
connectivity = connectivity - 1  # 转换为 0-based
```

### 3. 字符串编码

CGNS 节点中的字符串可能是 `bytes` 或 `str` 类型：

```python
if isinstance(value, bytes):
    value = value.decode('utf-8').strip()
```

## 回滚到 h5py

如果需要回滚到旧版本：

```bash
# 恢复旧的 loader
cp src/cgns_gui/loader_h5py.py.bak src/cgns_gui/loader.py

# 卸载 pyCGNS
conda remove pycgns
```

## 下一步

现在 pyCGNS 集成完成后，可以：

1. ✅ 完整的边界条件支持
2. ✅ Family 分组信息保留
3. 🔄 实现 FlowSolution_t 读取（M9 任务）
4. 🔄 添加流场可视化（云图、等值面、切片）

## 参考资源

- [pyCGNS 官方文档](http://pycgns.github.io/)
- [CGNS 标准文档](https://cgns.github.io/)
- [pyCGNS GitHub](https://github.com/pyCGNS/pyCGNS)
- [conda-forge pycgns](https://anaconda.org/conda-forge/pycgns)

## 问题反馈

如果遇到问题，请提供：
1. pyCGNS 版本：`conda list pycgns`
2. 错误信息和堆栈跟踪
3. 示例 CGNS 文件（如果可能）
4. 操作系统和 Python 版本
