# 案件文件夹管理系统

一款以本地文件夹为核心载体的案件管理桌面应用，基于 Python + PySide6 构建，集成案件台账、模板生成、OCR 信息识别、电子归档、截图合并与工具中心能力。项目当前正向 Windows + macOS 双平台核心能力对齐，Windows 右键菜单作为平台增强能力保留。

**当前版本**: v2.0.0

为兼容既有用户数据，应用运行时的配置目录与部分内部标识仍沿用 `LawyerCaseTool`。

## 功能特性

- **案件管理**: 维护本地案件台账、标签、状态、路径历史、期限和速记
- **模板生成**: 支持创建、编辑、复制和删除案件目录模板
- **变量替换**: 支持在文件夹名称和 Word 文档中使用变量
- **批量生成**: 一键生成标准化的案件文件夹结构
- **信息识别**: OCR 智能识别身份证、户口簿、护照等证件信息，自动填充到案卷模板
- **电子归档与工具中心**: 支持归档、法院短信、截图合并 PDF、Word 文档自动排版与对比等辅助工具
- **法院短信增强**: 支持拖拽 PDF/图片自动识别传票，提取被传唤人、开庭信息并加入期限
- **Word 自动排版**: 参照 GB/T 9704-2012 标准，智能识别标题层级并应用法律文书格式
- **右键菜单**: 集成到 Windows 资源管理器右键菜单
- **实时预览**: 生成前预览文件夹结构
- **Word 模板制作器**: 可视化制作 Word 模板，支持变量替换

## 系统要求

- Windows 10 或更高版本，或 macOS
- Python 3.8+

## 安装

### 从源码安装

```bash
# 克隆仓库
git clone <repository-url>
cd <repo-dir>

# 创建虚拟环境（推荐）
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS
source .venv/bin/activate

# 安装核心桌面依赖（双平台）
pip install -r requirements.txt

# 如需 OCR，再额外安装
pip install -r requirements-ocr.txt
```

#### 关于 OCR 依赖
从 v1.2.0 开始，使用 RapidOCR 替代 PaddleOCR：
- 模型内置，无需额外下载
- 体积小（40MB vs 200MB+）
- 启动快，识别稳定
- OCR 依赖已拆分为可选安装，避免影响双平台基础启动
- 当前建议在 Python 3.12 或更低版本的虚拟环境中安装 OCR 依赖

#### macOS + VSCode 终端运行 OCR

当前项目已验证可在 macOS 上使用 Homebrew 的 Python 3.11 运行完整 OCR 功能：

```bash
bash scripts/setup_macos_ocr_env.sh
source .venv-ocr311/bin/activate
python scripts/smoke_ocr.py
python src/main.py
```

如果想直接启动应用，也可以运行：

```bash
bash scripts/run_macos_ocr.sh
```

### 打包为 EXE

```bash
pyinstaller --name="案件文件夹管理系统" --windowed --onefile --icon=resources/icons/app.ico src/main.py
```

## 使用方法

### 启动应用程序

```bash
python src/main.py
```

### 信息识别功能

从 v1.2.0 开始，支持 OCR 智能识别证件信息：

1. 选择模板后，点击"信息识别"按钮
2. 添加身份证、户口簿等证件图片或 PDF
3. 点击"开始识别"
4. 核对识别结果（低置信度字段会标红提醒）
5. 点击"应用到案卷变量"自动填充表单

**v1.2.1 优化**：所有识别到的字段（姓名、性别、出生日期、住址、身份证号等）都会自动应用到案卷表单。已存在的变量直接填充，不存在的自动创建新变量。

支持的证件类型：
- ✅ 身份证（正面/反面）
- ⚠️ 户口簿（框架已搭建）
- ⚠️ 护照（框架已搭建）
- ⚠️ 驾驶证、营业执照、判决书等（框架已搭建）

### 安装右键菜单

仅 Windows 支持，需管理员权限：

```bash
python scripts/install_context_menu.py
```

### 卸载右键菜单

仅 Windows 支持，需管理员权限：

```bash
python scripts/uninstall_context_menu.py
```

## 默认模板

### 民事案件模板(原告)

适用于民事诉讼中原告方的标准化案卷。

```
{{case_number}}_{{client_name}}/
├── 0委托手续及程序性材料/
│   ├── 委托合同.docx
│   ├── 授权委托书.docx
│   ├── 律师事务所函.docx
│   └── 谈话笔录.docx
├── 1文书材料/
│   ├── 民事起诉状.docx
│   ├── 答辩状.docx
│   └── 证据清单.docx
├── 2证据材料/
├── 3法律检索/
├── 4类案检索/
├── 5庭审材料/
├── 6裁判文书/
├── 7执行材料/
└── 8结案材料/
```

### 民事案件模板(被告)

适用于民事诉讼中被告方的标准化案卷，包含管辖权异议、反诉等材料。

### 刑事案件模板

```
{{case_number}}_{{defendant_name}}/
├── 0委托辩护材料/
├── 1会见材料/
├── 2阅卷材料/
├── 3调查取证/
├── 4庭审材料/
├── 5裁判文书/
├── 6上诉申诉/
└── 7结案材料/
```

### 非诉案件模板

```
{{matter_number}}_{{client_name}}/
├── 0委托材料/
├── 1基础材料/
├── 2工作记录/
├── 3法律文书/
├── 4成果文件/
└── 5结案材料/
```

### 劳动仲裁模板(申请人/被申请人)

适用于劳动争议仲裁案件，包含：
- 仲裁申请材料
- 劳动关系证明
- 工资社保记录
- 庭审材料等

### 商事仲裁模板(申请人/被申请人)

适用于商事仲裁案件，支持：
- 买卖合同争议
- 建设工程争议
- 股权投资争议
- 借款/租赁合同纠纷等

## 配置存储

配置文件存储在以下位置（兼容保留旧目录名）：

- **Windows**: `%APPDATA%/LawyerCaseTool/`
- **macOS**: `~/Library/Application Support/LawyerCaseTool/`

其中包含：
- `config/config.json` - 应用配置
- `config/templates.json` - 模板配置
- `logs/` - 日志文件

## 开发

### 运行测试

```bash
pytest tests/
```

### 项目结构

```
LawyerCaseTool/
├── src/
│   ├── core/              # 核心业务逻辑
│   │   ├── ocr/           # OCR 信息识别（v1.2.0 新增）
│   │   │   ├── paddle_engine.py      # RapidOCR 引擎
│   │   │   ├── document_parser.py    # 文档解析器基类
│   │   │   ├── field_matcher.py      # 字段匹配系统
│   │   │   └── parsers/              # 各类证件解析器
│   │   │       ├── id_card_parser.py      # 身份证
│   │   │       ├── household_parser.py    # 户口簿
│   │   │       ├── passport_parser.py     # 护照
│   │   │       └── ...
│   │   ├── batch_processor.py        # 批量处理器
│   │   ├── folder_generator.py       # 文件夹生成器
│   │   ├── template_engine.py        # Word 模板引擎
│   │   └── word_editor.py            # Word 编辑器
│   ├── gui/               # GUI 界面
│   │   ├── info_extraction_dialog.py # 信息识别对话框（v1.2.0 新增）
│   │   ├── template_maker.py         # Word 模板制作器
│   │   ├── main_window.py            # 主窗口
│   │   └── widgets/                  # 自定义控件
│   │       ├── image_list_widget.py  # 图片列表+预览
│   │       └── ocr_result_widget.py  # OCR 结果展示
│   ├── config/            # 配置管理
│   ├── integration/       # 系统集成
│   └── utils/             # 工具模块
├── templates/             # 模板文件
├── docs/                  # 文档
│   └── diary/             # 开发日记
├── resources/             # 资源文件
├── tests/                 # 测试文件
└── scripts/               # 脚本文件
```

## 许可证

MIT License

## 开发者

**汪立** — 安徽始信律师事务所执业律师 ｜ 全栈型律师

- 微信公众号：池州汪律的Ai进化论
- 抖音 / 小红书 / B站：池州有个汪律师
- 邮箱：491445490@qq.com
