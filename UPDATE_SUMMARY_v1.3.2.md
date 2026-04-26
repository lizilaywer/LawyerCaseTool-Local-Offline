# v1.3.2 更新摘要

**发布日期**: 2026-03-26

## 主要更新

### 1. 电子化归档保存功能
- **保存按钮**: 将设置了变量的文档保存回原文件
- **另存为按钮**: 选择新位置保存文档
- **格式保留**: 完整保留Word文档的原有格式

### 2. 变量高亮颜色统一
- 电子化归档预览区的变量高亮颜色改为绿色
- 与Word模板制作器保持一致

### 3. 默认配置保存
- 当前软件状态保存为默认配置
- 支持"重置默认"恢复当前状态

## 修改文件

```
src/gui/archive_dialog.py           # 添加保存/另存为功能
src/gui/widgets/archive_preview.py  # 添加按钮、绿色高亮
src/config/default_templates.py     # 更新为当前状态
src/config/config_manager.py        # 修改重置默认逻辑
VERSION                             # 1.3.1 -> 1.3.2
CHANGELOG.md                        # 添加更新记录
PROJECT_RESUME.md                   # 更新版本号
```

## 日记

详细开发日记见: `docs/diary/2026-03-26_电子化归档保存功能与默认设置_diary.md`
