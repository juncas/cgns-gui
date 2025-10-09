# 开发日志

## 2025-10-09

- 完成 M0 与 M1 阶段交付。
- 建立 CGNS 数据模型（Zone / Section / MeshData），实现 `CgnsLoader` 读取基础 HDF5 结构。
- 主窗口新增 CGNS 树状视图、工具栏“打开 CGNS”操作。
- 新增测试：
  - `tests/test_loader.py` 验证简化 CGNS 文件解析。
  - `tests/test_app.py` 扩展模型树填充测试，保留 headless 环境跳过渲染验证。
- 构建 `SceneManager`，将 Section 网格映射为 VTK Actor 并接入主窗口加载流程。
- 新增 `tests/test_scene.py` 验证渲染管线创建与清理；`tests/test_app.py` 同步期待无初始 Actor。
- 更新 `docs/development-plan.md` 勾选 M1 并标记 M2 进度，记录剩余线框/表面切换事项。

## 2025-10-10

- 实现 SceneManager 渲染模式枚举，支持表面/线框切换并保持新建 Actor 状态一致。
- 工具栏新增互斥渲染模式按钮，默认表面模式，可即时切换线框显示。
- 扩充 `tests/test_scene.py` 验证默认渲染模式与切换逻辑。
- 更新开发计划标记 M2 全部事项完成。
- 创建 `SelectionController`，将树节点选中与 VTK 拾取绑定，支持点击场景与目录互相跳转。
- SceneManager 新增 Section 高亮逻辑（提亮颜色、加粗线宽），清除与重复加载后保持状态一致。
- 工具栏加载模型时同步刷新拾取列表与清空选中状态。
