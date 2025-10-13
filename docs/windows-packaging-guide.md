# Windows 应用打包指南

本文档说明如何将 CGNS-GUI 应用打包成独立的 Windows EXE 程序。

## 环境要求

- Python 3.10+ (已安装 cgns-gui 及其依赖)
- PyInstaller 6.16.0+
- Mesa OpenGL DLLs (如果系统不支持硬件 OpenGL)

## 打包步骤

### 1. 安装 PyInstaller

```powershell
pip install pyinstaller
```

### 2. 使用提供的 spec 文件打包

项目根目录已包含 `cgns-gui.spec` 配置文件，直接使用：

```powershell
pyinstaller cgns-gui.spec --clean
```

### 3. 查看打包结果

打包完成后，可执行文件位于：

```
dist/cgns-gui/
├── cgns-gui.exe          # 主程序
└── _internal/            # 依赖库和资源
    ├── *.dll             # Python、VTK、Qt、Mesa 等 DLL
    ├── PySide6/          # Qt 插件
    ├── vtk.libs/         # VTK 库
    └── ...
```

## 运行测试

### 本地测试

```powershell
.\dist\cgns-gui\cgns-gui.exe
```

### 在其他 Windows 机器上测试

1. 将整个 `dist/cgns-gui` 文件夹复制到目标机器
2. 确保目标机器安装了 **Visual C++ Redistributable 2015-2022 (x64)**
3. 双击 `cgns-gui.exe` 运行

## Mesa OpenGL 集成

打包后的程序已自动包含 Mesa OpenGL 软件渲染器，位于 `_internal` 目录中：

- `libgallium_wgl.dll` - Mesa Gallium WGL 驱动
- `opengl32.dll` - Mesa OpenGL 入口点
- `libglapi.dll` - OpenGL API 调度器
- 其他相关 DLL

**注意**：如果目标机器有硬件 OpenGL 支持（显卡驱动正常），VTK 会优先使用硬件加速；否则自动回退到 Mesa 软件渲染。

## 打包配置说明

`cgns-gui.spec` 文件的关键配置：

```python
# 隐藏导入 - 确保所有 VTK 和 PySide6 模块被包含
hiddenimports=[
    'vtkmodules',
    'vtkmodules.all',
    'vtkmodules.qt.QVTKRenderWindowInteractor',
    'h5py',
    'h5py.defs',
    'h5py.utils',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    # ...
]

# 数据文件 - 包含翻译文件
datas=[
    ('src/cgns_gui/translations/*.qm', 'cgns_gui/translations'),
]

# 可执行文件配置
EXE(
    ...,
    console=False,  # 不显示控制台窗口
    icon=None,      # 可以添加应用图标
)
```

## 常见问题

### 1. 打包后程序无法启动

**症状**：双击 EXE 没有反应或立即退出

**解决方案**：
- 临时设置 `console=True` 重新打包以查看错误信息
- 检查是否缺少 VC++ 运行库
- 在命令行运行 EXE 查看错误输出

### 2. OpenGL 初始化失败

**症状**：程序启动但报错 "failed to get valid pixel format"

**解决方案**：
- 确认 Mesa DLLs 已打包在 `_internal` 目录
- 检查目标机器显卡驱动是否正常
- 尝试使用 `--offscreen` 参数运行

### 3. 程序体积过大

**症状**：`dist` 文件夹超过 500MB

**说明**：这是正常的，因为包含了：
- VTK 库 (~200MB)
- PySide6/Qt (~100MB)
- NumPy/SciPy (~50MB)
- H5PY/HDF5 (~30MB)
- Mesa OpenGL (~20MB)

**优化方案**：
- 使用 `--exclude-module` 排除不需要的模块
- 使用 UPX 压缩 (PyInstaller 的 `upx=True` 选项)
- 考虑制作安装程序 (NSIS, InnoSetup)

### 4. 打包时出现警告

**症状**：PyInstaller 输出大量 WARNING 信息

**说明**：大多数警告可以忽略，只要程序能正常运行。常见警告：
- "Module not found" - 通常是可选依赖
- "Hidden import not found" - 可能是未使用的模块

## 分发建议

### 选项 1: ZIP 压缩包

最简单的方式，将 `dist/cgns-gui` 文件夹打包成 ZIP：

```powershell
Compress-Archive -Path dist\cgns-gui -DestinationPath cgns-gui-windows-x64.zip
```

### 选项 2: 安装程序

使用 NSIS 或 InnoSetup 创建安装向导：

**优点**：
- 专业的安装体验
- 自动创建桌面快捷方式
- 可以检测和安装 VC++ 运行库
- 注册卸载信息

**缺点**：
- 需要额外学习安装脚本语法
- 打包流程更复杂

### 选项 3: 单文件 EXE

修改 spec 文件使用 `onefile` 模式：

```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # 添加
    a.zipfiles,  # 添加
    a.datas,     # 添加
    ...,
    name='cgns-gui',
)

# 删除 COLLECT 部分
```

**警告**：单文件模式会在每次运行时解压到临时目录，启动较慢。

## 版本管理

建议在打包前更新版本信息：

1. 修改 `pyproject.toml` 中的 `version` 字段
2. 在 spec 文件中添加版本资源（Windows）
3. 打包文件名包含版本号：`cgns-gui-v1.0.0-windows-x64.zip`

## 自动化打包

可以创建批处理脚本 `build.bat`：

```batch
@echo off
echo Cleaning previous build...
rmdir /s /q build dist
echo Building application...
pyinstaller cgns-gui.spec --clean
echo Packaging...
cd dist
tar -a -c -f cgns-gui-windows-x64.zip cgns-gui
cd ..
echo Done! Package available at dist\cgns-gui-windows-x64.zip
pause
```

## 测试清单

打包后务必测试：

- [ ] 程序能正常启动
- [ ] 主窗口正常显示
- [ ] 文件打开对话框正常
- [ ] 能加载并显示 CGNS 文件
- [ ] VTK 渲染正常（检查是否使用 Mesa）
- [ ] 交互功能正常（旋转、缩放、平移）
- [ ] 程序能正常退出

## 参考资源

- [PyInstaller 官方文档](https://pyinstaller.org/)
- [PyInstaller Spec 文件说明](https://pyinstaller.org/en/stable/spec-files.html)
- [VTK Windows 打包注意事项](https://vtk.org/Wiki/VTK/Building/Windows)

---

**最后更新**：2025-10-13  
**测试环境**：Windows 11, Python 3.12.10, PyInstaller 6.16.0
