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
- 左侧栏加入 Section 信息面板，实时显示名称、类型、单元数、点数与索引范围。
- 新增重置视角按钮与 VTK 坐标轴小部件，保持 Trackball Camera 交互一致。
- 扩展 GUI 测试覆盖工具栏视角控制，确保在 headless 环境触发安全。
- 引入 `InteractionController` 管理键盘快捷键（R/S/W/O），可扩展后续交互事件。
- 解析 ZoneBC 边界条件并与对应的面单元 Section 关联，树状视图下新增“Boundary Conditions”分组，详情面板展示 GridLocation 信息；补充加载与界面测试验证分组行为。

## 2025-10-09（续）

- 主窗口整合状态栏进度指示与错误弹窗，加载流程可视化并捕获异常信息。
- 新增显示设置对话框，支持背景色与渲染模式即时切换，并同步更新工具栏状态。
- 扩充 `tests/test_app.py` 验证设置对话框选择后背景与线框模式正确生效。
- `CgnsLoader` 支持 `CGNSBase_t` 标签和 `DataArray_t` 数据布局，可正确读取真实 CGNS 示例；新增 `tests/test_loader.py::test_loader_supports_cgnsbase_label`。
- 引入字体自动配置逻辑，优先选择系统中的 CJK 字体以解决中文界面显示方块问题；更新 README 记录环境变量和字体排查建议。
- 体单元与面单元默认透明度区分，体单元初始透明而面单元保持可见；详情面板新增透明度滑条支持按 section 调整并实时刷新渲染。
- 全面改为英文界面文本，并接入 Qt 翻译加载机制（默认加载 `cgns_gui_<locale>.qm`），避免字体缺失导致的乱码，同时保留本地化能力。
- 为提升性能，体单元 section 默认不加入渲染并从拾取列表移除，可通过模型树右键菜单的“Show/Hide Section” 随时切换显隐。
- 解析边界条件时，优先使用 FamilyName/Families 配置确定显示名称，确保 UI 呈现与物理边界一致，补充加载与界面测试。
