# pyCGNS 迁移 - 下一步操作指南

## 🎉 恭喜！核心迁移已完成

所有代码重构和文档已经完成。现在需要您执行以下步骤来验证迁移。

## 📋 检查清单

### 步骤 1: 安装 pyCGNS

```bash
# 确保在 cgns-gui 环境中
conda activate cgns-gui

# 安装 pyCGNS（这是必须的步骤！）
conda install -c conda-forge pycgns -y

# 验证安装
python -c "from CGNS import MAP; print('pyCGNS 安装成功')"
```

**预期输出**: `pyCGNS 安装成功`

### 步骤 2: 测试基本功能

```bash
# 使用测试脚本验证 pyCGNS 能否加载您的 CGNS 文件
python test_pycgns_basic.py <your_cgns_file.cgns>
```

**预期输出**:
- ✓ pyCGNS 导入成功
- ✓ CGNS 文件加载成功
- 显示 Base/Zone/Elements/BC 等节点信息

### 步骤 3: 测试 GUI 应用

```bash
# 启动应用程序
python -m cgns_gui.app

# 在 GUI 中:
# 1. 打开一个 CGNS 文件
# 2. 验证网格正确显示
# 3. 检查 Section 列表
# 4. 测试选择和高亮功能
# 5. 查看属性面板中的边界条件信息
```

**检查项目**:
- [ ] 文件成功加载（无错误提示）
- [ ] 网格正确渲染
- [ ] Section 树显示完整
- [ ] 点击 Section 能正确选择和高亮
- [ ] 属性面板显示 Section 信息
- [ ] 边界条件信息显示（如果有）
- [ ] 性能正常（无明显卡顿）

### 步骤 4: 运行单元测试（可能需要调试）

```bash
# 运行 loader 测试
pytest tests/test_loader.py -v

# 如果失败，记录错误信息
```

**注意**: 单元测试可能需要更新以适配 pyCGNS。如果测试失败，请将错误信息反馈给我。

### 步骤 5: 推送到 GitHub

```bash
# 当网络恢复后
git push origin main
```

## 📝 反馈信息

如果遇到问题，请提供以下信息：

### A. 安装问题
```bash
# 运行这些命令并提供输出
conda list | grep pycgns
python -c "from CGNS import MAP; print(MAP.__file__)"
```

### B. 加载问题
```bash
# 运行测试脚本并提供完整输出
python test_pycgns_basic.py your_file.cgns 2>&1 | tee pycgns_test.log
```

### C. GUI 问题
- 截图或描述具体现象
- 错误消息（如果有）
- CGNS 文件特征（大小、元素数量等）

### D. 测试失败
```bash
# 提供详细的测试输出
pytest tests/test_loader.py -v --tb=long 2>&1 | tee pytest_output.log
```

## ❓ 常见问题

### Q1: pyCGNS 安装失败

**问题**: `CondaSSLError` 或网络错误

**解决**:
```bash
# 临时禁用 SSL 验证（仅用于调试）
conda config --set ssl_verify false

# 重试安装
conda install -c conda-forge pycgns -y

# 安装后恢复 SSL 验证
conda config --set ssl_verify true
```

### Q2: 导入错误 "No module named 'CGNS'"

**问题**: Python 找不到 pyCGNS

**解决**:
```bash
# 确认在正确的 conda 环境
conda env list

# 激活环境
conda activate cgns-gui

# 重新安装
conda install -c conda-forge pycgns -y
```

### Q3: CGNS 文件加载失败

**问题**: 文件打开后报错

**可能原因**:
1. 元素类型不在支持列表中
2. 文件结构特殊
3. 索引转换问题

**调试**:
```bash
# 使用测试脚本查看文件结构
python test_pycgns_basic.py your_file.cgns > structure.txt

# 将 structure.txt 发送给我分析
```

### Q4: 性能问题

**问题**: 加载很慢或卡顿

**排查**:
```bash
# 添加性能分析
python -m cProfile -o profile.stats -m cgns_gui.app

# 查看最耗时的函数
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

## 🔧 紧急回滚

如果遇到严重问题需要回滚：

```bash
# 恢复 h5py 版本
cp src/cgns_gui/loader_h5py.py.bak src/cgns_gui/loader.py

# 卸载 pyCGNS
conda remove pycgns

# 回滚 Git（如果已提交）
git revert HEAD~2..HEAD
```

## 📚 相关文档

- **迁移指南**: `docs/pycgns-migration.md`
- **迁移总结**: `docs/pycgns-migration-summary.md`
- **README**: 更新的安装说明
- **测试脚本**: `test_pycgns_basic.py`

## ✅ 成功标志

迁移成功的标志：
1. ✅ pyCGNS 安装无错误
2. ✅ 测试脚本正常运行
3. ✅ GUI 能加载 CGNS 文件
4. ✅ 网格渲染正确
5. ✅ 边界条件信息显示
6. ✅ 无明显性能问题

## 🚀 下一步

成功验证后，我们将进入：
- **M8.5 剩余任务**: 更新单元测试、CI 配置
- **M9 里程碑**: FlowSolution_t 流场数据支持

---

**准备好了吗？** 按照上面的步骤开始测试吧！有任何问题随时告诉我。
