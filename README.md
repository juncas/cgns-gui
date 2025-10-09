# CGNS GUI

基于 PySide6 的 CGNS 网格可视化客户端，目标是提供加载、浏览、选取和高亮 CGNS 文件中网格 Section 的桌面工具。

## 功能目标

- 打开并解析 CGNS 文件（支持多 Zone / Section）。
- 网格显式渲染（VTK 管线集成）。
- Section 级别选中、高亮、属性展示。
- 鼠标交互：旋转、缩放、平移视角。
- 友好的 UI：文件树、属性面板、状态提示。

## 环境需求

- Python 3.10+
- 推荐使用虚拟环境（Conda / venv）。
- 依赖列表详见 `pyproject.toml`。

### 安装步骤

```bash
# 创建并激活虚拟环境（示例：conda）
conda create -n cgns-gui python=3.10 -y
conda activate cgns-gui

# 安装依赖
pip install -e .[dev]
```

如使用系统提供的 Conda 环境，可直接在根目录执行 `pip install -e .[dev]`。

## 开发节奏

| 里程碑 | 内容 | 产出 |
| --- | --- | --- |
| M0 | 项目初始化，PySide6 + VTK 最小示例 | 可运行的空白窗口 |
| M1 | CGNS 文件解析与内部模型 | 加载并列出 Zone/Section |
| M2 | 网格渲染管线 | 场景中渲染网格 |
| M3 | Section 拾取与高亮 | UI + 场景联动 |
| M4 | 视角交互增强 | 交互顺畅、视角控制 |
| M5 | 体验与稳定性优化 | 状态栏、错误处理、偏好设置 |
| M6 | 测试与打包 | 测试用例、文档、可分发包 |

详细计划见 `docs/development-plan.md`。

## 运行与调试

项目采用 `src` 布局，应用入口位于 `src/cgns_gui/app.py`。当前版本提供：

- 工具栏“打开 CGNS”操作，使用 `CgnsLoader` 加载 HDF5 CGNS 文件。
- 左侧树状视图展示 Zone / Section 结构及单元数。
- `SceneManager` 将 Section 网格转换为 VTK Actor 并在右侧视口渲染（支持多种常见单元类型）。
- 工具栏提供表面/线框渲染模式切换，便于检查网格拓扑。
- 支持在树与视口之间同步选中 Section，拾取后自动高亮显示。
- Section 信息面板展示当前选中单元的类型、数量与索引范围。

开发阶段建议使用以下命令行启动脚本（示例）：

```bash
python -m cgns_gui.app
```

## 文档索引

- `docs/development-plan.md`：详细开发计划与任务分解。
- `docs/dev-log.md`：开发过程记录与每日摘要。
- `docs/architecture.md`（待补充）：模块设计与数据流。

## 贡献指南

- 提交前运行 `ruff check .` 与 `pytest`。
- 遵循 PEP 8 与类型标注约定。

## 许可证

MIT License。
