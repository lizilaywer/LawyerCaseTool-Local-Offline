# -*- coding: utf-8 -*-
"""
律师案卷工具 - Fluent Design 界面原型
基于 PySide-Fluent-Widgets

运行前请先安装:
    pip install PySide6 PySide6-Fluent-Widgets
"""

import sys
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QTextEdit, QTreeWidgetItem, 
    QSplitter, QScrollArea, QFrame, QFileDialog
)

# Fluent Widgets
try:
    from qfluentwidgets import (
        FluentWindow, NavigationItemPosition, FluentIcon,
        PrimaryPushButton, PushButton, ToolButton, 
        LineEdit, SearchLineEdit, ComboBox, CheckBox,
        CardWidget, ElevatedCardWidget, SimpleCardWidget,
        TreeWidget, ListWidget, ListView,
        InfoBar, InfoBarPosition, MessageBox, Dialog,
        ProgressBar, IndeterminateProgressBar,
        SegmentedWidget, Pivot, BreadcrumbBar,
        RoundMenu, Action, ToolTip,
        setTheme, Theme, setThemeColor, setFont,
        isDarkTheme
    )
    FLUENT_AVAILABLE = True
except ImportError:
    print("请先安装 PySide-Fluent-Widgets: pip install PySide6-Fluent-Widgets")
    FLUENT_AVAILABLE = False
    sys.exit(1)


class TemplateCard(ElevatedCardWidget):
    """模板卡片组件"""
    
    def __init__(self, title, desc, icon, color, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 120)
        self.selected = False
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 顶部图标和标签
        top_layout = QHBoxLayout()
        
        icon_label = QLabel()
        icon_label.setPixmap(icon.icon(color=color).pixmap(32, 32))
        top_layout.addWidget(icon_label)
        
        top_layout.addStretch()
        
        if parent and parent.property("default_template") == title:
            default_tag = QLabel("默认")
            default_tag.setStyleSheet("""
                QLabel {
                    background-color: #1e3a5f;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 11px;
                }
            """)
            top_layout.addWidget(default_tag)
        
        layout.addLayout(top_layout)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #0f172a;
            }
        """)
        layout.addWidget(title_label)
        
        # 描述
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #64748b;
            }
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addStretch()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.set_selected(True)
            
    def set_selected(self, selected):
        self.selected = selected
        if selected:
            self.setStyleSheet("""
                ElevatedCardWidget {
                    border: 2px solid #1e3a5f;
                    background-color: #f0f4f8;
                }
            """)
        else:
            self.setStyleSheet("")


class FormCard(CardWidget):
    """表单卡片组件"""
    
    def __init__(self, title, icon, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        icon_label = QLabel()
        icon_label.setPixmap(icon.icon(color="#64748b").pixmap(18, 18))
        title_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #0f172a;
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # 内容区域（供子类填充）
        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)


class CreateCaseInterface(QWidget):
    """创建案卷界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 24, 32, 32)
        
        # 模板选择区域
        template_section = QVBoxLayout()
        
        section_header = QHBoxLayout()
        section_title = QLabel("选择模板")
        section_title.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        """)
        section_header.addWidget(section_title)
        section_header.addStretch()
        
        manage_btn = PushButton("管理模板")
        manage_btn.setIcon(FluentIcon.SETTING)
        section_header.addWidget(manage_btn)
        
        template_section.addLayout(section_header)
        
        # 模板卡片网格
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        
        self.template_cards = []
        
        templates = [
            ("民事案件(原告)", "适用于民事诉讼案件原告方", FluentIcon.PEOPLE, "#3b82f6"),
            ("民事案件(被告)", "适用于民事诉讼案件被告方", FluentIcon.CONTACT, "#f59e0b"),
            ("刑事案件", "适用于刑事辩护案件", FluentIcon.SHIELD, "#ef4444"),
            ("劳动仲裁", "适用于劳动争议仲裁案件", FluentIcon.BRIEFCASE, "#22c55e"),
        ]
        
        for i, (title, desc, icon, color) in enumerate(templates):
            card = TemplateCard(title, desc, icon, color, self)
            if i == 0:
                card.setProperty("default_template", title)
                card.set_selected(True)
            card.mousePressEvent = lambda e, c=card: self.on_template_selected(c)
            cards_layout.addWidget(card)
            self.template_cards.append(card)
        
        cards_layout.addStretch()
        template_section.addLayout(cards_layout)
        layout.addLayout(template_section)
        
        # 分割布局
        content_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧表单区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(16)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 案件信息卡片
        case_card = FormCard("案件信息", FluentIcon.DOCUMENT, self)
        
        # 案号、案由
        row1 = QHBoxLayout()
        
        case_number_layout = QVBoxLayout()
        case_number_label = QLabel("案号")
        case_number_label.setStyleSheet("font-size: 13px; color: #374151;")
        case_number_layout.addWidget(case_number_label)
        self.case_number_input = LineEdit()
        self.case_number_input.setText("(2024)浙01民初123号")
        case_number_layout.addWidget(self.case_number_input)
        row1.addLayout(case_number_layout)
        
        case_type_layout = QVBoxLayout()
        case_type_label = QLabel("案由")
        case_type_label.setStyleSheet("font-size: 13px; color: #374151;")
        case_type_layout.addWidget(case_type_label)
        self.case_type_input = LineEdit()
        self.case_type_input.setText("民间借贷纠纷")
        case_type_layout.addWidget(self.case_type_input)
        row1.addLayout(case_type_layout)
        
        case_card.content_layout.addLayout(row1)
        
        # 法院名称
        court_layout = QVBoxLayout()
        court_label = QLabel("法院名称")
        court_label.setStyleSheet("font-size: 13px; color: #374151;")
        court_layout.addWidget(court_label)
        self.court_input = LineEdit()
        self.court_input.setText("浙江省杭州市中级人民法院")
        court_layout.addWidget(self.court_input)
        case_card.content_layout.addLayout(court_layout)
        
        # 办理阶段
        stage_layout = QVBoxLayout()
        stage_header = QHBoxLayout()
        stage_label = QLabel("办理阶段")
        stage_label.setStyleSheet("font-size: 13px; color: #374151;")
        stage_header.addWidget(stage_label)
        stage_header.addStretch()
        optional_label = QLabel("可选")
        optional_label.setStyleSheet("font-size: 11px; color: #9ca3af;")
        stage_header.addWidget(optional_label)
        stage_layout.addLayout(stage_header)
        
        self.stage_combo = ComboBox()
        self.stage_combo.addItems(["一审阶段", "二审阶段", "执行阶段", "再审阶段"])
        stage_layout.addWidget(self.stage_combo)
        case_card.content_layout.addLayout(stage_layout)
        
        left_layout.addWidget(case_card)
        
        # 当事人信息卡片
        party_card = FormCard("当事人信息", FluentIcon.PEOPLE, self)
        
        # 委托人姓名
        client_layout = QVBoxLayout()
        client_label = QLabel("委托人姓名")
        client_label.setStyleSheet("font-size: 13px; color: #374151;")
        client_layout.addWidget(client_label)
        
        client_input_layout = QHBoxLayout()
        self.client_input = LineEdit()
        self.client_input.setText("张三")
        client_input_layout.addWidget(self.client_input)
        
        ocr_btn = ToolButton(FluentIcon.SCAN)
        ocr_btn.setToolTip("从OCR识别")
        client_input_layout.addWidget(ocr_btn)
        
        client_layout.addLayout(client_input_layout)
        party_card.content_layout.addLayout(client_layout)
        
        # 性别、电话
        row2 = QHBoxLayout()
        
        gender_layout = QVBoxLayout()
        gender_label = QLabel("性别")
        gender_label.setStyleSheet("font-size: 13px; color: #374151;")
        gender_layout.addWidget(gender_label)
        self.gender_combo = ComboBox()
        self.gender_combo.addItems(["男", "女"])
        gender_layout.addWidget(self.gender_combo)
        row2.addLayout(gender_layout)
        
        phone_layout = QVBoxLayout()
        phone_label = QLabel("联系电话")
        phone_label.setStyleSheet("font-size: 13px; color: #374151;")
        phone_layout.addWidget(phone_label)
        self.phone_input = LineEdit()
        self.phone_input.setPlaceholderText("138****8888")
        phone_layout.addWidget(self.phone_input)
        row2.addLayout(phone_layout)
        
        party_card.content_layout.addLayout(row2)
        
        # 对方当事人
        opponent_layout = QVBoxLayout()
        opponent_label = QLabel("对方当事人")
        opponent_label.setStyleSheet("font-size: 13px; color: #374151;")
        opponent_layout.addWidget(opponent_label)
        self.opponent_input = LineEdit()
        self.opponent_input.setText("李四")
        opponent_layout.addWidget(self.opponent_input)
        party_card.content_layout.addLayout(opponent_layout)
        
        left_layout.addWidget(party_card)
        left_layout.addStretch()
        
        content_splitter.addWidget(left_widget)
        
        # 右侧预览区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(16)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 案卷结构预览卡片
        preview_card = FormCard("案卷结构预览", FluentIcon.FOLDER, self)
        
        preview_header = QHBoxLayout()
        preview_header.addStretch()
        refresh_btn = PushButton("刷新")
        refresh_btn.setIcon(FluentIcon.SYNC)
        preview_header.addWidget(refresh_btn)
        preview_card.content_layout.insertLayout(0, preview_header)
        
        # 文件夹树
        self.folder_tree = TreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setColumnCount(1)
        
        # 添加示例数据
        root = QTreeWidgetItem(self.folder_tree)
        root.setText(0, "(2024)浙01民初123号_张三")
        root.setIcon(0, FluentIcon.FOLDER.icon(color="#3b82f6"))
        
        folder1 = QTreeWidgetItem(root)
        folder1.setText(0, "0委托手续")
        folder1.setIcon(0, FluentIcon.FOLDER.icon(color="#f59e0b"))
        
        file1 = QTreeWidgetItem(folder1)
        file1.setText(0, "委托合同.docx")
        file1.setIcon(0, FluentIcon.DOCUMENT.icon(color="#60a5fa"))
        
        file2 = QTreeWidgetItem(folder1)
        file2.setText(0, "授权委托书.docx")
        file2.setIcon(0, FluentIcon.DOCUMENT.icon(color="#60a5fa"))
        
        file3 = QTreeWidgetItem(folder1)
        file3.setText(0, "所函.docx")
        file3.setIcon(0, FluentIcon.DOCUMENT.icon(color="#60a5fa"))
        
        folders = ["1起诉材料", "2证据材料", "3庭审材料", "4裁判文书"]
        for name in folders:
            item = QTreeWidgetItem(root)
            item.setText(0, name)
            item.setIcon(0, FluentIcon.FOLDER.icon(color="#f59e0b"))
        
        self.folder_tree.expandAll()
        preview_card.content_layout.addWidget(self.folder_tree)
        
        right_layout.addWidget(preview_card)
        
        # 输出设置卡片
        output_card = FormCard("输出设置", FluentIcon.SETTING, self)
        
        # 输出目录
        output_dir_layout = QVBoxLayout()
        output_dir_label = QLabel("输出目录")
        output_dir_label.setStyleSheet("font-size: 13px; color: #374151;")
        output_dir_layout.addWidget(output_dir_label)
        
        output_dir_input_layout = QHBoxLayout()
        self.output_dir_input = LineEdit()
        self.output_dir_input.setText("C:\\Users\\Lawyer\\案卷\\2024")
        output_dir_input_layout.addWidget(self.output_dir_input)
        
        browse_btn = PushButton("浏览")
        browse_btn.setFixedWidth(60)
        output_dir_input_layout.addWidget(browse_btn)
        
        output_dir_layout.addLayout(output_dir_input_layout)
        output_card.content_layout.addLayout(output_dir_layout)
        
        # 选项
        self.open_folder_check = CheckBox("生成后打开文件夹")
        self.open_folder_check.setChecked(True)
        output_card.content_layout.addWidget(self.open_folder_check)
        
        self.readme_check = CheckBox("生成目录说明文件")
        output_card.content_layout.addWidget(self.readme_check)
        
        right_layout.addWidget(output_card)
        right_layout.addStretch()
        
        content_splitter.addWidget(right_widget)
        content_splitter.setSizes([500, 500])
        
        layout.addWidget(content_splitter, 1)
        
        # 底部生成按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.generate_btn = PrimaryPushButton("生成案卷")
        self.generate_btn.setIcon(FluentIcon.PLAY)
        self.generate_btn.setFixedSize(140, 40)
        self.generate_btn.clicked.connect(self.on_generate)
        bottom_layout.addWidget(self.generate_btn)
        
        layout.addLayout(bottom_layout)
        
    def on_template_selected(self, selected_card):
        """模板选择事件"""
        for card in self.template_cards:
            card.set_selected(False)
        selected_card.set_selected(True)
        
    def on_generate(self):
        """生成案卷"""
        # 显示进度
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("生成中...")
        
        # 模拟生成过程
        QTimer.singleShot(1500, self.on_generate_complete)
        
    def on_generate_complete(self):
        """生成完成"""
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("生成案卷")
        
        # 显示成功提示
        InfoBar.success(
            title="生成成功",
            content="案卷文件夹已创建完成",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )


class OCRInterface(QWidget):
    """OCR信息识别界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 24, 32, 32)
        
        # 标题
        title = QLabel("OCR信息识别")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a;")
        layout.addWidget(title)
        
        # 说明
        desc = QLabel("支持身份证、户口簿、护照、驾驶证、营业执照等证件的自动识别")
        desc.setStyleSheet("font-size: 13px; color: #64748b;")
        layout.addWidget(desc)
        
        # 文件拖放区域
        drop_card = ElevatedCardWidget()
        drop_card.setFixedHeight(200)
        drop_card.setStyleSheet("""
            ElevatedCardWidget {
                border: 2px dashed #cbd5e1;
                background-color: #f8fafc;
            }
            ElevatedCardWidget:hover {
                border-color: #1e3a5f;
                background-color: #f0f4f8;
            }
        """)
        
        drop_layout = QVBoxLayout(drop_card)
        drop_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel()
        icon_label.setPixmap(FluentIcon.PHOTO.icon(color="#94a3b8").pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(icon_label)
        
        text_label = QLabel("拖放图片或PDF到这里，或点击选择文件")
        text_label.setStyleSheet("font-size: 14px; color: #64748b; margin-top: 12px;")
        text_label.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(text_label)
        
        select_btn = PushButton("选择文件")
        select_btn.setIcon(FluentIcon.FOLDER_ADD)
        select_btn.setFixedWidth(120)
        drop_layout.addWidget(select_btn, alignment=Qt.AlignCenter)
        
        layout.addWidget(drop_card)
        
        # 最近识别记录
        history_label = QLabel("最近识别")
        history_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #0f172a;")
        layout.addWidget(history_label)
        
        # 使用 ListWidget 显示记录
        history_list = ListWidget()
        history_list.setFixedHeight(200)
        
        # 添加示例记录
        items = [
            ("身份证 - 张三", "2026-03-12 14:32", FluentIcon.CONTACT),
            ("判决书 - (2024)浙01民初123号", "2026-03-12 10:15", FluentIcon.DOCUMENT),
            ("营业执照 - 某某有限公司", "2026-03-11 16:45", FluentIcon.SHOP),
        ]
        
        for text, time, icon in items:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(12, 8, 12, 8)
            
            icon_label = QLabel()
            icon_label.setPixmap(icon.icon().pixmap(24, 24))
            item_layout.addWidget(icon_label)
            
            text_label = QLabel(text)
            text_label.setStyleSheet("font-size: 13px; color: #0f172a;")
            item_layout.addWidget(text_label, stretch=1)
            
            time_label = QLabel(time)
            time_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
            item_layout.addWidget(time_label)
            
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            history_list.addItem(list_item)
            history_list.setItemWidget(list_item, item_widget)
        
        layout.addWidget(history_list)
        layout.addStretch()


class TemplateManageInterface(QWidget):
    """模板管理界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 24, 32, 32)
        
        # 标题
        title = QLabel("模板管理")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a;")
        layout.addWidget(title)
        
        # 操作栏
        toolbar = QHBoxLayout()
        
        search_input = SearchLineEdit()
        search_input.setPlaceholderText("搜索模板...")
        search_input.setFixedWidth(300)
        toolbar.addWidget(search_input)
        
        toolbar.addStretch()
        
        new_btn = PrimaryPushButton("新建模板")
        new_btn.setIcon(FluentIcon.ADD)
        toolbar.addWidget(new_btn)
        
        import_btn = PushButton("导入")
        import_btn.setIcon(FluentIcon.DOWNLOAD)
        toolbar.addWidget(import_btn)
        
        layout.addLayout(toolbar)
        
        # 模板列表
        self.template_list = ListWidget()
        
        templates_data = [
            ("民事案件模板(原告)", "适用于民事诉讼案件原告方", "8个变量", True),
            ("民事案件模板(被告)", "适用于民事诉讼案件被告方", "6个变量", True),
            ("刑事案件模板", "适用于刑事辩护案件", "5个变量", True),
            ("非诉案件模板", "适用于非诉讼法律事务", "4个变量", True),
            ("劳动仲裁模板(申请人)", "适用于劳动者申请仲裁", "7个变量", True),
            ("劳动仲裁模板(被申请人)", "适用于用人单位应诉", "6个变量", True),
            ("商事仲裁模板(申请人)", "适用于商事仲裁申请", "8个变量", True),
            ("商事仲裁模板(被申请人)", "适用于商事仲裁应诉", "7个变量", True),
        ]
        
        for name, desc, vars_text, is_default in templates_data:
            item_widget = self.create_template_item(name, desc, vars_text, is_default)
            list_item = self.template_list.addItem(item_widget)
        
        layout.addWidget(self.template_list)
        
    def create_template_item(self, name, desc, vars_text, is_default):
        """创建模板列表项"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # 图标
        icon_label = QLabel()
        icon_label.setPixmap(FluentIcon.LAYOUT.icon(color="#3b82f6").pixmap(40, 40))
        layout.addWidget(icon_label)
        
        # 信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name_layout = QHBoxLayout()
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #0f172a;")
        name_layout.addWidget(name_label)
        
        if is_default:
            default_tag = QLabel("默认")
            default_tag.setStyleSheet("""
                QLabel {
                    background-color: #1e3a5f;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 11px;
                }
            """)
            name_layout.addWidget(default_tag)
        
        name_layout.addStretch()
        info_layout.addLayout(name_layout)
        
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("font-size: 13px; color: #64748b;")
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # 变量数
        vars_label = QLabel(vars_text)
        vars_label.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(vars_label)
        
        # 操作按钮
        edit_btn = ToolButton(FluentIcon.EDIT)
        edit_btn.setToolTip("编辑")
        layout.addWidget(edit_btn)
        
        copy_btn = ToolButton(FluentIcon.COPY)
        copy_btn.setToolTip("复制")
        layout.addWidget(copy_btn)
        
        delete_btn = ToolButton(FluentIcon.DELETE)
        delete_btn.setToolTip("删除")
        layout.addWidget(delete_btn)
        
        return widget


class MainWindow(FluentWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("律师案卷自动化生成工具")
        self.resize(1400, 900)
        
        # 设置主题
        setTheme(Theme.LIGHT, save=False)
        setThemeColor("#1e3a5f")
        
        # 设置字体
        font = QFont("Microsoft YaHei UI", 10)
        setFont(font)
        
        # 初始化界面
        self.init_interface()
        
    def init_interface(self):
        """初始化子界面"""
        # 创建案卷界面
        self.create_case_interface = CreateCaseInterface(self)
        self.addSubInterface(
            self.create_case_interface,
            FluentIcon.FOLDER_ADD,
            "创建案卷",
            NavigationItemPosition.TOP
        )
        
        # OCR界面
        self.ocr_interface = OCRInterface(self)
        self.addSubInterface(
            self.ocr_interface,
            FluentIcon.SCAN,
            "信息识别",
            NavigationItemPosition.TOP
        )
        
        # 模板管理界面
        self.template_interface = TemplateManageInterface(self)
        self.addSubInterface(
            self.template_interface,
            FluentIcon.LAYOUT,
            "模板管理",
            NavigationItemPosition.TOP
        )
        
        # 设置导航栏
        self.navigationInterface.addSeparator(NavigationItemPosition.TOP)
        
        # 最近案卷（仅显示）
        self.navigationInterface.addItem(
            routeKey="recent1",
            icon=FluentIcon.HISTORY,
            text="最近: 浙01民初123号",
            onClick=lambda: print("打开最近案卷"),
            position=NavigationItemPosition.TOP
        )
        
        # 设置和帮助
        self.addSubInterface(
            QWidget(),  # 占位
            FluentIcon.SETTING,
            "设置",
            NavigationItemPosition.BOTTOM
        )
        
        self.addSubInterface(
            QWidget(),  # 占位
            FluentIcon.HELP,
            "帮助",
            NavigationItemPosition.BOTTOM
        )


def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
