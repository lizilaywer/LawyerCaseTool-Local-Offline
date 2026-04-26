# Word 模板变量替换功能 - 实现完成报告

## 🎉 实现状态

✅ **PySide6 版本已实现完成！**

---

## 📋 功能概述

实现了在律师案卷工具中为每个文件关联 Word 模板的功能。当生成案卷时，系统会自动使用关联的模板，并将用户填写的变量值替换到 Word 文档中。

---

## 🏗️ 架构设计

### 数据流

```
用户填写变量 → 选择模板 → 关联到文件 → 生成案卷 → Word 文档包含变量值
     ↓            ↓           ↓              ↓
主界面输入    模板管理器    template_path   TemplateEngine处理
                         + use_template    docxtpl替换变量
```

### 核心组件

1. **TemplatePathManager** - 模板路径管理器
   - 管理系统模板和用户自定义模板
   - 路径解析和验证
   - 模板库扫描

2. **FolderGenerator (增强)** - 文件夹生成器
   - 检测文件的 `use_template` 和 `template_path` 配置
   - 使用 TemplateEngine 生成包含变量的 Word 文档
   - 未关联模板的文件创建空文档（向后兼容）

3. **TemplateFileDialog** - 模板关联对话框
   - 可视化配置模板关联
   - 模板库快捷选择
   - 变量预览

4. **TemplateManager (增强)** - 模板管理器
   - 右键菜单关联模板
   - 显示模板关联状态（✓ 标记）

---

## 📁 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/utils/template_path_manager.py` | **新建** | 模板路径管理器 |
| `src/gui/template_file_dialog.py` | **新建** | 模板关联对话框 |
| `src/config/default_templates.py` | **修改** | 添加 use_template 字段 |
| `src/core/folder_generator.py` | **修改** | 支持 Word 模板生成 |
| `src/gui/template_manager.py` | **修改** | 集成模板关联功能 |
| `prototypes/template_association.html` | **新建** | HTML 原型演示 |
| `test_word_template.py` | **新建** | 功能测试脚本 |

---

## 🔧 核心实现细节

### 1. 模板配置结构

```python
{
    "name": '0"{{client_name}}"委托合同.docx',
    "type": "file",
    "template_path": "civil/委托合同.docx",  # 模板路径（相对或绝对）
    "use_template": True  # 是否启用模板
}
```

### 2. 文件创建逻辑（FolderGenerator._create_file）

```python
if use_template and template_path:
    resolved_template = self._template_path_manager.resolve_template_path(template_path)
    if resolved_template and resolved_template.exists():
        self._template_engine.process_template(
            resolved_template,
            file_path,
            values  # 变量值字典
        )
```

### 3. 模板路径解析优先级

1. **用户自定义模板** - 优先查找
   - 路径：`%APPDATA%/LawyerCaseTool/templates/`

2. **系统默认模板** - 后备选项
   - 路径：`项目根目录/templates/`

---

## 🎨 用户界面

### 模板关联对话框

- 📝 当前选中文件显示
- ☑️ 启用/禁用模板复选框
- 📂 模板路径输入（支持浏览）
- 📚 系统模板库快捷选择
- 📋 模板变量预览
- ✅ 实时路径验证

### 模板管理器集成

- 右键文件项 → "关联模板..."
- 已关联的文件显示 ✓ 标记
- 支持编辑和删除关联

---

## 📊 测试结果

### 测试脚本输出

```
✓ 模板路径管理器 - 正常工作
✓ 路径解析功能 - 正常工作
✓ 变量替换功能 - 正常工作
✓ 配置结构解析 - 正常工作
```

### 已关联模板的文件（民事案件模板）

| 文件名 | 模板路径 | 状态 |
|--------|----------|------|
| 0"{{client_name}}"委托合同.docx | civil/委托合同.docx | ✓ 已关联 |
| 1"{{client_name}}"委托书.docx | civil/授权委托书.docx | ✓ 已关联 |
| 4"{{client_name}}"谈话笔录.docx | civil/谈话笔录.docx | ✓ 已关联 |
| "{{client_name}}"民事起诉状.docx | civil/民事起诉状.docx | ✓ 已关联 |
| 2"{{client_name}}"答辩状.docx | civil/答辩状.docx | ✓ 已关联 |

---

## 🚀 使用方法

### 方式 1：使用系统默认模板

1. 打开主程序
2. 选择"民事案件模板"
3. 填写变量（委托人姓名、案号等）
4. 点击"生成案卷"
5. 系统自动使用关联的模板生成文档

### 方式 2：自定义模板关联

1. 打开模板管理器
2. 选择要编辑的模板
3. 在文件夹树中右键点击文件
4. 选择"关联模板..."
5. 在对话框中选择或上传 Word 模板
6. 保存配置

### 方式 3：创建自定义模板

1. 在 Word 中创建文档
2. 使用 `{{变量名}}` 格式插入变量
3. 保存为 .docx 格式
4. 复制到 `templates/` 目录
5. 在模板管理器中关联

---

## 📖 模板变量格式

在 Word 文档中使用 `{{变量名}}` 格式：

```
委托合同

编号：{{案号}}

甲方（委托人）：{{委托人姓名}}
乙方（受托人）：{{承办律师}}

因甲方与 {{对方当事人}} 之间 {{案由}} 一案...
```

### 可用变量列表

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| {{client_name}} | 委托人姓名 | 张三 |
| {{case_number}} | 案号 | (2024)京01民初123号 |
| {{case_cause}} | 案由 | 合同纠纷 |
| {{opposing_party}} | 对方当事人 | 李四有限公司 |
| {{court}} | 受理法院 | 北京市第一中级人民法院 |
| {{lawyer_name}} | 承办律师 | 王律师 |
| {{receive_date}} | 收案日期 | 2024-01-15 |

---

## ✨ 功能特点

### 核心优势

✅ **双重模板支持** - 系统默认模板 + 用户自定义模板
✅ **灵活配置** - 每个文件可独立关联模板
✅ **向后兼容** - 未关联模板的文件创建空文档
✅ **路径解析** - 自动查找系统/用户模板目录
✅ **可视化操作** - 直观的对话框界面
✅ **实时验证** - 模板路径有效性检查
✅ **变量预览** - 显示模板中的所有变量

### 技术亮点

- 使用 `docxtpl` 库处理 Word 模板
- 支持相对路径和绝对路径
- 单例模式管理器设计
- 完善的错误处理和日志记录
- PySide6 原生界面集成

---

## 🔍 测试指南

### 运行测试脚本

```bash
cd LawyerCaseTool
python test_word_template.py
```

### 手动测试步骤

1. **启动应用**：
   ```bash
   python src/main.py
   ```

2. **测试系统模板**：
   - 选择"民事案件模板"
   - 填写变量值
   - 点击"生成案卷"
   - 验证生成的 Word 文档包含变量值

3. **测试自定义模板**：
   - 打开模板管理器
   - 关联自定义模板到文件
   - 生成案卷验证

---

## 📝 后续改进建议

### 短期优化

- [ ] 添加模板变量自动提取功能（从 Word 文档读取）
- [ ] 实现模板拖拽上传
- [ ] 添加模板预览功能（显示文档内容）
- [ ] 支持模板分类管理

### 长期规划

- [ ] 在线模板库（云端模板）
- [ ] 模板版本控制
- [ ] 协作编辑功能
- [ ] 模板市场（用户共享）

---

## 🎯 总结

Word 模板变量替换功能已完整实现，包括：

✅ 后端逻辑 - TemplatePathManager、FolderGenerator 增强
✅ 前端界面 - TemplateFileDialog、TemplateManager 集成
✅ 配置扩展 - default_templates.py 添加模板关联字段
✅ 测试验证 - 功能测试脚本通过

现在用户可以：
1. 在主界面填写变量
2. 为每个文件关联 Word 模板
3. 生成案卷时自动替换变量到文档
4. 使用系统默认模板或自定义模板

**功能已可用，等待用户最终测试确认！**

---

**实现日期**: 2026-02-25
**版本**: v1.1.0-dev
**状态**: ✅ 实现完成，待用户测试
