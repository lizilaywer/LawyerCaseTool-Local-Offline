# 律师案卷工具 - Fluent Design 重设计指南

## 技术方案：PySide-Fluent-Widgets

### 为什么选择这个方案？

| 维度 | 评估 |
|------|------|
| **技术栈兼容** | ✅ 完全基于 PySide6，无需重写业务逻辑 |
| **落地难度** | ✅ 低，渐进式改进 |
| **视觉效果** | ✅ 现代化 Win11 风格，专业美观 |
| **稳定性** | ✅ 成熟开源项目，GitHub 5k+ Stars |
| **维护成本** | ✅ 持续更新，中文社区活跃 |

---

## 核心改进点

### 1. 导航架构 - 从混乱到清晰

```
当前设计                    Fluent 设计
┌─────────────────────┐    ┌─────────────────────┐
│ [菜单栏]              │    │ ┌─────┐             │
│ 文件 编辑 视图...      │    │ │ 🏠  │  创建案卷    │ ◄── 主导航
├─────────────────────┤    │ │ 🔍  │  信息识别    │
│ [工具栏]              │    │ │ 📋  │  模板管理    │
│ [图标][图标][图标]     │    │ └─────┘             │
├─────────────────────┤    │ ━━━━━━━━━━━━         │
│ [侧边栏] [主内容区]   │    │ 最近案卷             │
│         │            │    │ • 浙01民初123号      │
│         │            │    │ • 张三诉李四案       │
│         │            │    │ ━━━━━━━━━━━━         │
└─────────────────────┘    │ 设置  帮助            │
                           └─────────────────────┘
```

**改进:**
- 左侧导航栏清晰展示核心功能
- 最近使用快速访问
- 统一的视觉层级

### 2. 模板选择 - 从下拉框到卡片网格

```
当前: 下拉框                Fluent: 卡片网格
┌─────────────────┐        ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│ 民事案件模板 ▼  │        │ 👤  │ │ 👥  │ │ ⚖️  │ │ 💼  │
└─────────────────┘        │民事 │ │民事 │ │刑事 │ │劳动 │
                           │(原告)│ │(被告)│ │案件 │ │仲裁 │
                           │默认  │ │     │ │     │ │     │
                           └─────┘ └─────┘ └─────┘ └─────┘
                           
                           • 视觉直观，一眼识别
                           • 悬停动效，交互反馈
                           • 选中状态清晰
```

### 3. 表单设计 - 从密集到呼吸感

```
当前设计                    Fluent 设计
┌─────────────────────┐    ╭─────────────────────────────╮
│ 案件信息 [========]  │    │ 📄 案件信息                  │
│ 案号: [__________]  │    │                             │
│ 案由: [__________]  │    │  案号          案由          │
│ 法院: [__________]  │    │ ┌──────────┐ ┌──────────┐  │
│                     │    │ │(2024)浙  │ │民间借贷  │  │
│ 当事人信息          │    │ │01民初... │ │纠纷      │  │
│ [================]  │    │ └──────────┘ └──────────┘  │
│ 姓名: [__________]  │    │                             │
│ 性别: [__________]  │    │  法院名称                    │
└─────────────────────┘    │ ┌────────────────────────┐ │
                           │ │浙江省杭州市中级人民法院│ │
                           │ └────────────────────────┘ │
                           ╰─────────────────────────────╯
                           
                           • 卡片分组，逻辑清晰
                           • 适当间距，减少视觉疲劳
                           • 图标辅助，提升识别度
```

### 4. 文件夹预览 - 从静态到可交互

```
Fluent 树形控件
╭──────────────────────────────╮
│ 📁 案卷结构预览         🔄   │
├──────────────────────────────┤
│ ▼ 📁 (2024)浙01民初123号_张三│
│    ▼ 📁 0委托手续            │
│       📄 委托合同.docx       │
│       📄 授权委托书.docx     │
│       📄 所函.docx           │
│    ▶ 📁 1起诉材料            │
│    ▶ 📁 2证据材料            │
│    ▶ 📁 3庭审材料            │
│    ▶ 📁 4裁判文书            │
╰──────────────────────────────╯

• 可展开/折叠
• 图标区分文件类型
• 实时预览生成结果
```

### 5. 反馈系统 - 从弹窗到轻量提示

```
当前: 弹窗阻断              Fluent: 轻量提示
┌─────────────────────┐    ┌─────────────────────────┐
│ ⚠️ 提示              │    │                         │
│                     │    │  ✓ 生成成功              │ ◄── 顶部滑入
│ 案卷生成成功！       │    │  案卷文件夹已创建完成     │
│                     │    │                    [×]   │
│ [确定]              │    │                         │
└─────────────────────┘    └─────────────────────────┘
                            3秒后自动消失，不阻断操作
```

---

## 颜色系统

```python
# 主色调 - 法律蓝 (专业、信任)
PRIMARY = {
    "main": "#1e3a5f",      # 深蓝
    "light": "#2d5a87",     # 浅蓝
    "dark": "#152942",      # 暗蓝
    "50": "#f0f4f8",        # 背景
}

# 强调色 - 金色 (品质、法律)
ACCENT = {
    "main": "#d4a853",      # 金色
    "light": "#e5c47a",     # 浅金
    "dark": "#b8923f",      # 暗金
}

# 功能色
FUNCTIONAL = {
    "success": "#22c55e",   # 成功
    "warning": "#f59e0b",   # 警告
    "error": "#ef4444",     # 错误
    "info": "#3b82f6",      # 信息
}

# 中性色 (文本、边框、背景)
NEUTRAL = {
    "gray_900": "#0f172a",  # 主要文本
    "gray_600": "#475569",  # 次要文本
    "gray_400": "#94a3b8",  # 占位文本
    "gray_200": "#e2e8f0",  # 边框
    "gray_100": "#f1f5f9",  # 背景
    "gray_50": "#f8fafc",   # 卡片背景
}
```

---

## 组件对照表

| 功能 | 当前组件 | Fluent 替代 | 效果提升 |
|------|----------|-------------|----------|
| 主按钮 | `QPushButton` | `PrimaryPushButton` | 蓝色渐变，悬停动效 |
| 次按钮 | `QPushButton` | `PushButton` | 白色背景，边框精致 |
| 输入框 | `QLineEdit` | `LineEdit` | 圆角，聚焦高亮 |
| 搜索框 | `QLineEdit` | `SearchLineEdit` | 内置搜索图标，清除按钮 |
| 下拉框 | `QComboBox` | `ComboBox` | 圆角，动画展开 |
| 复选框 | `QCheckBox` | `CheckBox` | 现代样式，流畅动画 |
| 卡片 | 自定义 | `CardWidget` | 阴影，圆角，悬停效果 |
| 树形 | `QTreeWidget` | `TreeWidget` | 现代化样式，图标支持 |
| 列表 | `QListWidget` | `ListWidget` | 悬停效果，选中状态 |
| 标签页 | `QTabWidget` | `SegmentedWidget` | 分段控件，更现代 |
| 进度条 | `QProgressBar` | `IndeterminateProgressBar` | 流畅动画 |
| 提示 | `QMessageBox` | `InfoBar` | 轻量，不阻断 |
| 菜单 | `QMenu` | `RoundMenu` | 圆角，阴影，动画 |
| 工具提示 | `QToolTip` | `ToolTip` | 圆角，富文本 |
| 导航 | 自定义 | `NavigationInterface` | 专业导航栏 |

---

## 实施步骤

### 阶段一：环境准备 (1天)

```bash
# 安装依赖
pip install PySide6-Fluent-Widgets

# 验证安装
python -c "from qfluentwidgets import FluentWindow; print('OK')"
```

### 阶段二：主窗口改造 (2天)

1. 创建 `FluentWindow` 主窗口
2. 配置导航栏（创建案卷、信息识别、模板管理）
3. 添加最近使用快捷入口
4. 设置主题色（法律蓝）

### 阶段三：创建案卷界面 (3天)

1. 模板选择卡片网格
2. 案件信息表单卡片
3. 当事人信息表单卡片
4. 案卷结构预览树
5. 输出设置卡片
6. 生成按钮和反馈

### 阶段四：其他界面 (2天)

1. OCR 信息识别界面
2. 模板管理界面
3. 设置界面

### 阶段五：优化打磨 (2天)

1. 动画效果调优
2. 快捷键支持
3. 暗黑模式适配
4. 性能优化

**总计：约 10 个工作日**

---

## 代码示例

### 基础窗口框架

```python
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    setTheme, Theme, setThemeColor
)

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("律师案卷自动化生成工具")
        self.resize(1400, 900)
        
        # 设置法律蓝主题
        setTheme(Theme.LIGHT)
        setThemeColor("#1e3a5f")
        
        # 添加导航项
        self.addSubInterface(
            CreateCaseInterface(),
            FluentIcon.FOLDER_ADD,
            "创建案卷",
            NavigationItemPosition.TOP
        )
        # ... 其他界面

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

### 模板卡片

```python
from qfluentwidgets import ElevatedCardWidget, FluentIcon

class TemplateCard(ElevatedCardWidget):
    def __init__(self, title, desc, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 120)
        
        layout = QVBoxLayout(self)
        
        # 图标
        icon = QLabel()
        icon.setPixmap(FluentIcon.PEOPLE.icon().pixmap(32, 32))
        layout.addWidget(icon)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        layout.addWidget(title_label)
        
        # 描述
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(desc_label)
```

### 成功提示

```python
from qfluentwidgets import InfoBar, InfoBarPosition

# 生成成功提示
InfoBar.success(
    title="生成成功",
    content="案卷文件夹已创建完成",
    orient=Qt.Horizontal,
    isClosable=True,
    position=InfoBarPosition.TOP,
    duration=3000,
    parent=self
)
```

---

## 参考资源

- **GitHub**: [zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
- **文档**: [https://qfluentwidgets.com](https://qfluentwidgets.com)
- **示例**: 官方提供 50+ 示例程序
- **视频教程**: B站搜索 "Fluent Widgets"

---

## 预期效果

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| 界面美观度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 用户体验 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 专业感 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 开发效率 | - | 提升 30%（组件开箱即用）|
| 维护成本 | - | 降低（统一设计规范）|
