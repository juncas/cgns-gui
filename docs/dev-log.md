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
