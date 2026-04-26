# -*- coding: utf-8 -*-
"""测试新的分割器布局"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QLabel
from PySide6.QtCore import Qt

from src.gui.widgets.image_list_widget import ImageListWidget


class TestDialog(QDialog):
    """测试对话框"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("测试图片列表布局 - 分割器版")
        self.setMinimumSize(500, 700)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 顶部说明
        hint = QLabel("✅ 左侧布局已更新：\n• 上方预览区域放大\n• 下方文件列表缩小\n• 中间有可拖动调节的分隔条")
        hint.setStyleSheet("""
            background-color: #e8f5e9;
            color: #2e7d32;
            padding: 12px;
            border-radius: 4px;
            font-size: 13px;
        """)
        layout.addWidget(hint)
        
        # 创建左右分割器（模拟主对话框布局）
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：图片列表控件
        self.image_list = ImageListWidget()
        main_splitter.addWidget(self.image_list)
        
        # 右侧：占位区域（模拟识别结果）
        right_placeholder = QLabel("右侧：识别结果展示区域\n\n（此处为占位符）")
        right_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_placeholder.setStyleSheet("""
            background-color: #f5f5f5;
            border: 2px dashed #ccc;
            border-radius: 4px;
            color: #666;
            font-size: 14px;
        """)
        main_splitter.addWidget(right_placeholder)
        
        # 设置左右比例
        main_splitter.setSizes([350, 550])
        
        layout.addWidget(main_splitter, 1)
        
        # 底部说明
        bottom_hint = QLabel("💡 提示：\n• 可以拖动左侧两个区域之间的分隔条调节大小\n• 上方预览区域默认更大，方便查看证件细节\n• 下方文件列表缩小，但仍可拖动调节")
        bottom_hint.setStyleSheet("color: #666; font-size: 12px; padding: 8px;")
        layout.addWidget(bottom_hint)


def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    dialog = TestDialog()
    dialog.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
