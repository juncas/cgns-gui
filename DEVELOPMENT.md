# CGNS GUI - Conda 环境开发

## 当前状态 (2025-10-15)

项目已完全回退到基于 conda 的开发环境。uv 迁移尝试因 pyCGNS 的二进制依赖问题而失败。

## 推荐开发流程

### 1. 创建环境

```bash
conda create -n cgns-gui python=3.10 -y
conda activate cgns-gui
```

### 2. 安装依赖

```bash
# 安装 pyCGNS（必须）
conda install -c conda-forge pycgns -y

# 安装其他开发依赖
conda install -c conda-forge pytest pytest-qt ruff h5py -y
```

### 3. 运行测试（不需要 pip install）

```powershell
# Windows PowerShell
$env:PYTHONPATH = "C:\Users\pengj\work\code\cgns-gui\src"
C:\Users\pengj\anaconda3\envs\cgns-gui\python.exe -m pytest tests/

# 或运行应用
$env:PYTHONPATH = "C:\Users\pengj\work\code\cgns-gui\src"
C:\Users\pengj\anaconda3\envs\cgns-gui\python.exe -m cgns_gui.app
```

## 已知问题

- conda 环境的 pip 在某些系统上可能损坏（Windows 注册表问题）
- 解决方法：完全通过 conda 安装依赖，使用 PYTHONPATH 运行而不是 `pip install -e .`

## CI 配置

CI 使用标准的 pip 安装流程（在干净的GitHub Actions环境中pip工作正常）：

```yaml
- pip install ".[dev]"
- pytest
- ruff check .
```

## 为什么不用 uv？

pyCGNS 包含编译的 C 扩展，依赖 HDF5 DLL 和特定 Python 版本。无法通过 PyPI/uv 安装，只能通过 conda-forge 获取。

尝试将 pyCGNS 从 conda 复制到 uv 环境会导致 DLL 依赖地狱。

## 未来计划

- 保持 conda 作为主要开发环境
- CI 继续使用 pip（GitHub Actions 环境中pip工作正常）
- 考虑为 pyCGNS 构建预编译 wheels（长期目标）
