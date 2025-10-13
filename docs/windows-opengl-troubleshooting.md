# Windows OpenGL 问题排查与解决方案

## 问题现状

在 Windows 环境下，即使安装了 Intel Arc 显卡驱动（支持 OpenGL 4.6），VTK 仍然报告 `SupportsOpenGL() = 0`，导致应用无法使用硬件加速渲染。

## 已验证的信息

- ✅ Python 3.12.10 已正确安装
- ✅ VTK 9.5.2 已安装
- ✅ Intel Arc 显卡驱动 32.0.101.7026 正常工作
- ✅ Mesa 24.3.2 DLLs 已复制到 Python 目录
- ❌ VTK 仍然无法识别 OpenGL 支持

## 根本原因

VTK 的 Windows 预编译包（从 PyPI 安装的 wheel）在初始化 OpenGL 上下文时，直接调用 Windows 的 WGL API。当系统存在以下情况时会失败：

1. **虚拟显示驱动优先**：远程桌面、虚拟显示器（如 Oray、ToDesk）占用了主显示输出
2. **会话类型限制**：某些 Windows 会话类型（如服务会话、某些 RDP 配置）不暴露 OpenGL 3.2+
3. **Mesa 兼容性**：PyPI 的 VTK wheel 可能未针对 Mesa 优化，即使放置了 Mesa DLLs 也无法使用

## 当前可用解决方案

### 方案 1：使用离屏渲染模式（已验证可用）

```powershell
python -m cgns_gui.app --offscreen
```

- **优点**：无需解决 OpenGL 问题即可运行
- **缺点**：无交互式窗口，仅适用于批处理/测试

### 方案 2：切换到本地控制台会话

1. 如果当前是远程连接，改为：
   - 物理机本地登录
   - 使用支持 GPU 直通的远程工具（Parsec、Moonlight、NoMachine）

2. 禁用虚拟显示驱动：
   ```powershell
   # 在设备管理器中禁用 Oray、ToDesk 等虚拟显示适配器
   Get-PnpDevice -Class Display | Where-Object {$_.FriendlyName -like "*Oray*" -or $_.FriendlyName -like "*Virtual*"} | Disable-PnpDevice -Confirm:$false
   ```

3. 重启后测试：
   ```powershell
   python -c "from vtkmodules.vtkRenderingCore import vtkRenderWindow; print(vtkRenderWindow().SupportsOpenGL())"
   ```

### 方案 3：从源代码编译 VTK（高级用户）

如果必须在当前环境使用 Mesa，需要：

1. 安装 Visual Studio 2022 及 CMake
2. 下载 VTK 源代码
3. 配置时启用 OSMesa 或 EGL 支持
4. 重新编译 VTK Python 绑定

**注意**：此方案工作量大，不建议普通用户尝试。

### 方案 4：等待应用改进

项目可以考虑以下改进：

1. 提供预构建的离屏渲染版本
2. 集成 VTK OSMesa 构建
3. 添加更智能的环境检测和回退机制

## 推荐工作流程

对于开发和测试：

1. **日常开发**：在物理机本地运行，使用硬件加速
2. **CI/CD**：使用 `--offscreen` 模式进行自动化测试
3. **远程工作**：
   - 使用支持 GPU 的远程工具
   - 或使用 `--offscreen` 模式配合截图功能

## 验证步骤

```powershell
# 1. 检查 OpenGL 支持
python -c "from vtkmodules.vtkRenderingCore import vtkRenderWindow; print('OpenGL:', vtkRenderWindow().SupportsOpenGL())"

# 2. 检查显示适配器
Get-WmiObject Win32_VideoController | Select-Object Name,DriverVersion,Status

# 3. 测试离屏模式
python -m cgns_gui.app --offscreen

# 4. 测试窗口模式（如果 OpenGL 支持为 1）
python -m cgns_gui.app
```

## 相关资源

- [VTK Windows OpenGL 问题](https://discourse.vtk.org/t/opengl-initialization-failed/8234)
- [Mesa for Windows](https://github.com/pal1000/mesa-dist-win)
- [VTK 编译指南](https://vtk.org/Wiki/VTK/Building/Windows)

## 更新日志

- 2025-10-13：初始文档，确认离屏模式可用，OpenGL 硬件加速待解决
