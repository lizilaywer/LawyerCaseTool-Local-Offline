# 双平台架构改造方案

目标：在不削弱项目核心能力的前提下，使软件在 Windows 和 macOS 上都可安装、启动和完成主要业务流程。

## 核心原则

1. 核心业务优先跨平台
   案卷模板、变量填充、文件夹生成、案件管理、期限日历必须在双平台上保持可用。

2. 系统集成功能模块化
   Windows 注册表右键菜单保留为平台增强能力，不再作为应用启动前提。

3. 可选能力延迟加载
   OCR 等对解释器版本、平台 wheel 和系统库敏感的能力改为可选增强模块。

4. 依赖分层
   基础桌面功能与 OCR/平台增强依赖分离，保证基础安装在双平台上可完成。

## 当前已完成的第一阶段

- 新增 `src/utils/platform_utils.py`
  - 统一平台判断
  - 统一应用数据目录
  - 统一默认案卷输出目录
  - 统一默认字体
  - 统一打开文件/文件夹行为

- `src/config/path_manager.py`
  - 应用数据目录改为按平台选择

- `src/config/config_manager.py`
  - 默认配置改为深拷贝，避免共享默认字典
  - 默认案卷输出目录按平台自动生成

- `src/app.py`
  - 默认字体改为按平台选择

- `src/gui/case_manager_dialog.py`
  - 打开文件/文件夹不再直接依赖 `os.startfile`

- `src/gui/generation_dialog.py`
  - 生成后自动打开目录改为统一平台接口
  - 默认输出目录改为统一平台接口

- `src/gui/settings_dialog.py`
  - 默认输出目录改为统一平台接口

- `src/gui/template_maker.py`
  - 使用系统默认程序打开文件改为统一平台接口

- `src/gui/main_window.py`
  - OCR 对话框改为延迟导入，避免启动时被可选依赖阻塞
  - 主界面增加 OCR 可用性状态提示与安装说明入口

- `src/gui/info_extraction_dialog.py`
  - OCR 不可用时显示状态提示与安装说明
  - PDF 临时目录改为跨平台临时目录接口

- 依赖拆分
  - `requirements-core.txt`
  - `requirements-ocr.txt`
  - `requirements-full.txt`

- OCR 状态检测
  - 区分“未安装依赖”“当前 Python 版本不支持”“运行时初始化失败”

## 当前验证结果

- 已在项目内 `.venv` 中安装 `PySide6`
- `src.gui.main_window.MainWindow` 已在 macOS 下完成导入和实例化验证
- 已在 macOS + Homebrew Python 3.11 的 `.venv-ocr311` 中安装完整 OCR 依赖
- OCR 引擎已完成初始化，并对测试图像成功识别出文本块
- 主窗口与信息识别对话框在 OCR 环境下均显示为可用状态
- `python -m compileall src tests` 已通过
- 在当前受限沙箱中，配置目录写入会被系统权限策略拦截；这属于运行环境限制，不是应用跨平台代码本身的问题

## 下一阶段建议

### 阶段 2：功能对齐

- 为 OCR 安装说明增加一键复制命令能力
- 在 OCR 不可用时补充更细的运行诊断信息
- 为 macOS 增加 Finder 打开路径、图标、菜单体验优化
- 检查所有 `win32`/`darwin`/`os.startfile` 零散调用并收口

### 阶段 3：发布对齐

- Windows
  - 保留 PyInstaller 单文件/目录打包
  - 保留注册表右键菜单脚本

- macOS
  - 产出 `.app`
  - 补充图标和 Bundle 元数据
  - 视发布需求增加签名与 notarization

### 阶段 4：测试对齐

- 基础 smoke test
  - 应用启动
  - 主窗口创建
  - 模板加载
  - 案卷生成
  - 案件管理打开文件夹

- 平台行为测试
  - 应用数据目录
  - 平台默认打开路径
  - OCR 模块缺失时的降级行为

## 功能边界定义

双平台必须保证：

- 模板管理
- 模板制作
- 案卷生成
- 电子化归档
- 案件管理
- 期限日历

可作为平台增强或可选安装能力：

- OCR 信息识别
- Windows 资源管理器右键菜单

## 推荐安装策略

基础安装：

```bash
pip install -r requirements.txt
```

完整安装：

```bash
pip install -r requirements-full.txt
```

仅补充 OCR：

```bash
pip install -r requirements-ocr.txt
```
