# 图标资源说明

此目录包含应用程序图标文件，采用现代扁平化设计风格。

## 当前品牌

- 中文名：案件文件夹管理系统
- 英文名：LEXORA
- 辅助说明：LOCAL OFFLINE CASE MANAGEMENT

## 图标设计

**设计理念**：
- 主元素：文件夹 + 法律文档
- 风格：现代扁平化，圆角设计
- 主色调：专业蓝 #3b82f6
- 辅助色：白色、浅蓝、成功绿

**含义**：
- 蓝色背景：代表专业、信任的法律服务
- 白色文件夹：案卷文件夹
- 浅蓝文档：法律文件/合同
- 绿色圆点：代表"完成/成功"状态

## 文件列表

### 应用图标
| 文件 | 说明 |
|------|------|
| `app_icon.ico` | Windows 应用图标（多尺寸） |
| `app_logo.png` | 应用 Logo（1024x1024） |
| `app_logo_shadow.png` | 带阴影版本（512x512） |
| `app_icon_1024.png` | macOS 图标基础 |
| `lexora_app_icon.ico` | LEXORA Windows 应用图标（多尺寸） |
| `lexora_app_icon.png` | LEXORA 应用图标（512x512） |
| `lexora_mark.png` | LEXORA 单色标识 |
| `lexora_wordmark.png` | LEXORA 英文 wordmark |
| `lexora_full_lockup.png` | LEXORA 完整组合标识 |

### 多尺寸 PNG（用于不同场景）
- `app_icon_16x16.png` ~ `app_icon_1024x1024.png`（共25个尺寸）
- 覆盖：16, 20, 24, 32, 36, 40, 48, 57, 60, 64, 72, 76, 88, 96, 100, 114, 120, 128, 144, 152, 180, 192, 256, 512, 1024

## 使用场景

| 尺寸 | 用途 |
|------|------|
| 16x16 | 窗口标题栏、状态栏 |
| 32x32 | 任务栏（小图标）、开始菜单 |
| 48x48 | 资源管理器列表视图 |
| 64x64, 96x96 | 资源管理器大图标视图 |
| 128x128, 256x256 | 桌面快捷方式、应用商店 |
| 512x512, 1024x1024 | 宣传物料、高分辨率屏幕 |

## 生成新图标

如需重新生成图标，运行：

```bash
python scripts/generate_icons.py
```

此脚本会自动生成所有尺寸的图标文件。

## 打包注意事项

使用 PyInstaller 打包时，确保包含图标文件：

```bash
pyinstaller --add-data "resources/icons;resources/icons" --icon=resources/icons/app_icon.ico src/main.py
```
