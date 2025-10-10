# 发布与打包指南

本文档说明如何基于仓库内容构建可分发的 CGNS GUI 包，并给出常见问题排查建议。

## 环境准备

1. 使用 Python 3.10 或以上版本。
2. 推荐创建独立虚拟环境（例如 `conda create -n cgns-gui python=3.10`）。
3. 安装项目及开发依赖：

```bash
pip install -e .[dev]
```

4. 确保安装 `build`（已包含在 `dev` extra 中，如有需要可单独执行 `pip install build`）。

## 生成分发包

仓库提供 `tools/build_package.py` 脚本封装了 `python -m build`：

```bash
python tools/build_package.py
```

脚本会在构建前清理 `dist/` 目录，并生成：

- `dist/cgns_gui-<version>.tar.gz`（源代码包，sdist）
- `dist/cgns_gui-<version>-py3-none-any.whl`（通用 wheel）

若脚本返回非零退出码，请检查终端输出，常见问题包括：

- 未安装 `build` 模块：`pip install build`
- 本地 Python 版本低于 3.10：升级或启用兼容环境
- 依赖拉取失败：检查网络代理或私有 PyPI 设置

### Windows 平台说明

在 PowerShell 中执行打包脚本的命令与 Linux 基本一致，只需确保虚拟环境已激活：

```powershell
# 进入仓库根目录并激活虚拟环境
cd C:\workspace\cgns-gui
./.venv/Scripts/Activate.ps1

# 运行打包脚本
python tools/build_package.py
```

如遇 Windows Defender SmartScreen 阻止脚本执行，可在 PowerShell 中执行 `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` 后重试。

脚本结束后可在当前终端使用以下命令快速验证生成的 wheel：

```powershell
pip install --force-reinstall dist\cgns_gui-<version>-py3-none-any.whl
```

> 若希望将构建结果复制到 CI 工件，可在 GitHub Actions 中追加 `actions/upload-artifact` 步骤。

## 预发布验证

发布前建议执行以下步骤：

1. 运行测试套件：`pytest`
2. 验证应用入口：
   ```bash
   python -m cgns_gui.app --offscreen
   ```
3. 安装构建产物进行冒烟测试：
   ```bash
   pip install dist/cgns_gui-<version>-py3-none-any.whl
   cgns-gui --offscreen
   ```

## GitHub Actions 发布流程

仓库提供 `Release Packages` 工作流（`.github/workflows/release.yml`），可在 GitHub Actions 页签手动触发或在推送 `v*` 标签时自动执行。流程将：

1. 在 `ubuntu-latest` 与 `windows-latest` 上分别安装依赖、运行 `ruff check .` 与 `pytest`。
2. 使用 `tools/build_package.py` 构建 sdist 与 wheel，并对 wheel 进行冒烟安装验证。
3. 将每个平台的 `dist/` 目录上传为构件；若触发条件为标签推送或手动启用了 `publish-release`，还会将产物发布到对应的 GitHub Release。

手动触发发布的示例步骤：

1. 在仓库的 “Actions” -> “Release Packages” 页面点击 “Run workflow”。
2. 输入版本号（例如 `v0.2.0`），勾选 `publish-release`（如需自动创建 Release）。
3. 等流程完成后，从 Release 或构件中下载对应平台的包。

## 发布到 PyPI（可选）

1. 安装 `twine`：`pip install twine`
2. 上传：
   ```bash
   twine upload dist/*
   ```
   若需上传到测试 PyPI，可增加 `--repository testpypi`

## 常见问题排查

| 问题 | 可能原因 | 解决方案 |
| --- | --- | --- |
| 构建输出缺少 wheel | `build` 失败或 dist 目录无写权限 | 检查终端日志，确认 dist 目录是否被锁定 |
| 运行 GUI 报错 "QT_QPA_PLATFORM" | 当前环境无图形接口 | 设定 `QT_QPA_PLATFORM=offscreen` 或在图形环境中运行 |
| 上传 PyPI 失败 | 账号凭据错误 / 版本号冲突 | 检查 `~/.pypirc`，并确保版本号递增 |

## 后续规划

- 集成自动化发布（GitHub Actions + PyPI API token）
- 根据发行反馈完善 FAQ 与故障排查章节
