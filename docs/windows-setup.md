# Windows 环境搭建指南

本文档用于指导在 64 位 Windows 平台上准备 CGNS GUI 的开发、测试与打包环境，并记录 PySide6、VTK、CGNS 相关依赖的安装要点及常见问题排查思路。

## 支持范围

- 操作系统：Windows 10 21H2 及以上、Windows 11（64 位）
- Python 版本：3.10、3.11、3.12（需 64 位发行版）
- 图形驱动：建议更新至最新的厂商稳定版本（NVIDIA/AMD/Intel），以保证 VTK 的 OpenGL 管线运行稳定

> 若必须在无 GPU 或远程桌面环境执行，可使用 `--offscreen` 模式或设定 `QT_QPA_PLATFORM=offscreen`，详见下文“运行验证”。

## 先决条件

1. **安装 Visual C++ Redistributable 2015-2022**（x64）。
   - 可通过 `winget install Microsoft.VCRedist.2015+.x64` 安装。
   - 缺失该组件时，PySide6/VTK 导入可能报错 `MSVCP140.dll not found`。
2. **安装 64 位 Python**。
   - 推荐从 Microsoft Store、官方安装包或 `winget` 获取，例如 `winget install Python.Python.3.11`。
   - 安装时勾选 “Add python.exe to PATH”，或在命令行使用 `py -3.11` 指定版本。
3. **确保 PowerShell 执行策略允许激活虚拟环境**。
   - 若激活时提示受限，可执行 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`。

## 环境准备步骤

以下步骤假定代码已克隆至 `C:\workspace\cgns-gui`，并使用 PowerShell 执行命令；如使用 `cmd.exe`，请将 `./.venv/Scripts/activate` 换为 `./.venv/Scripts/activate.bat`。

```powershell
# 切换到仓库根目录
cd C:\workspace\cgns-gui

# 创建虚拟环境（示例使用 Python 3.11）
py -3.11 -m venv .venv

# 激活虚拟环境
./.venv/Scripts/Activate.ps1

# 升级 pip 并安装项目依赖（含开发工具）
python -m pip install --upgrade pip
pip install -e .[dev]
```

> 若仅需运行应用，可安装发布包：`pip install cgns-gui`（待后续发布）。

## 依赖说明

### PySide6

- 官方提供 Windows x64 的二进制 wheel，无需额外的 Qt 安装。
- wheel 内置 Qt 插件，安装成功后 `PySide6\plugins` 会自动被包含在包中。
- 若运行时报缺少 Qt 平台插件，可检查 `QT_PLUGIN_PATH` 是否被外部程序覆盖，必要时执行 `set QT_PLUGIN_PATH=` 清空后重试。

### VTK

- 项目使用 `vtk>=9.3`，同样提供 64 位 wheel。
- 需确保 Python 与 VTK wheel 架构一致（均为 64 位），否则导入时报 `DLL load failed`。
- OpenGL 依赖来自显卡驱动，若在远程桌面环境下渲染失败，可切换到 `--offscreen` 模式。

### h5py 与 CGNS 数据

- `h5py` wheel 默认带有 HDF5 动态库，无需额外安装 CGNS C API。
- 项目通过 `h5py` 直接解析 `.cgns`（HDF5）文件，无本地 CGNS 库绑定。
- 若需处理基于 ADF 的旧格式，可在后续迭代评估是否引入 `pycgns` 等库。

## 运行验证

在虚拟环境激活状态下，执行以下命令确认环境配置正确：

```powershell
# 运行测试套件（包含 Qt/VTK 相关测试）
pytest

# 启动 GUI（窗口模式）
python -m cgns_gui.app

# 无图形环境下的离屏运行（输出日志，无窗口）
python -m cgns_gui.app --offscreen
```

如需验证打包流程，可执行：

```powershell
python tools/build_package.py
```

构建成功后，`dist/` 下将生成 wheel 与 sdist，可在同一环境中通过 `pip install dist/<artifact>.whl` 进行冒烟测试。

## 常见问题排查

| 场景 | 现象 | 处理建议 |
| --- | --- | --- |
| 缺少 MSVC 运行库 | 导入 PySide6/VTK 报 `VCRUNTIME140.dll` 或 `MSVCP140.dll` 缺失 | 安装 Visual C++ Redistributable 2015-2022（x64） |
| 使用 32 位 Python | VTK 导入失败，提示 `DLL load failed` | 安装 64 位 Python，并重新创建虚拟环境 |
| 远程桌面渲染崩溃 | 打开窗口即退出或显示空白 | 运行时追加 `--offscreen`，或设定 `set QT_QPA_PLATFORM=offscreen` |
| Qt 插件冲突 | 启动时报错无法加载 `platform plugin "windows"` | 清理或重置 `QT_PLUGIN_PATH`，确保只使用 PySide6 提供的插件 |
| CGNS 文件加载异常 | 读取大文件时抛出 HDF5 相关错误 | 确保文件未被其他程序占用，必要时复制至本地磁盘后再加载 |

## 后续事项

- M7 仍需完成 Windows CI workflow 与打包验证（见任务 T-013）。
- 发布前请在 Windows 环境内执行一次完整的测试与打包流程，并记录结果于 `docs/dev-log.md`。
