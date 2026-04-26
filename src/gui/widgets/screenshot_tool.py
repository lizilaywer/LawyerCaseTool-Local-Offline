# -*- coding: utf-8 -*-
"""截图工具 - 支持全屏截图和区域选择"""

from PySide6.QtWidgets import (
    QWidget, QApplication, QRubberBand, QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt, QRect, QPoint, Signal, QSize
from PySide6.QtGui import QScreen, QPixmap, QMouseEvent, QKeyEvent, QPainter, QColor

from src.utils.logger import get_logger
from src.gui.styles import hint_banner_style


class ScreenshotTool(QWidget):
    """全屏截图工具

    使用方法：
    1. 调用 start_screenshot() 开始截图
    2. 用户拖拽鼠标选择区域
    3. 释放鼠标完成截图，发出 screenshot_captured 信号
    4. 按 ESC 取消截图

    信号：
    - screenshot_captured(QPixmap): 截图完成，返回 QPixmap
    - screenshot_cancelled(): 用户取消截图
    """

    screenshot_captured = Signal(QPixmap)  # 截图完成
    screenshot_cancelled = Signal()         # 取消截图

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger()

        self._rubber_band: QRubberBand = None
        self._origin: QPoint = None
        self._screenshot: QPixmap = None
        self._screenshot_offset: QPoint = QPoint(0, 0)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置界面"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 提示标签
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # OCR提示
        self._ocr_hint_label = QLabel("放大后识别更清楚，建议 PDF 比例调到 100%")
        self._ocr_hint_label.setStyleSheet(hint_banner_style("info"))
        layout.addWidget(self._ocr_hint_label)

        self._hint_label = QLabel("拖拽鼠标选择截图区域，按 ESC 取消")
        self._hint_label.setStyleSheet("""
            QLabel {
                background: rgba(15, 23, 42, 210);
                color: white;
                padding: 8px 16px;
                border-radius: 12px;
                font-size: 13px;
                margin-top: 8px;
                font-weight: 600;
            }
        """)
        layout.addWidget(self._hint_label)

    def start_screenshot(self) -> None:
        """开始截图 - 捕获全屏并显示遮罩"""
        try:
            # 捕获所有屏幕的全屏图像
            screens = QApplication.screens()
            if not screens:
                self._logger.error("没有可用屏幕")
                return

            # 计算所有屏幕的并集区域
            total_rect = QRect()
            for screen in screens:
                total_rect = total_rect.united(screen.geometry())

            # 创建一个大的 QPixmap 来存储所有屏幕的内容
            self._screenshot = QPixmap(total_rect.size())
            self._screenshot.fill(Qt.GlobalColor.black)

            # 在每个屏幕的位置绘制其截图
            painter = QPainter(self._screenshot)
            for screen in screens:
                screen_geom = screen.geometry()
                # 计算相对位置（相对于 total_rect 的左上角）
                rel_x = screen_geom.x() - total_rect.x()
                rel_y = screen_geom.y() - total_rect.y()
                # 捕获该屏幕
                screen_shot = screen.grabWindow(0)
                # 绘制到总截图中
                painter.drawPixmap(rel_x, rel_y, screen_shot)
            painter.end()

            # 保存截图偏移量，用于后续计算
            self._screenshot_offset = QPoint(total_rect.x(), total_rect.y())

            # 设置窗口覆盖所有屏幕
            self.setGeometry(total_rect)

            # 显示遮罩层（半透明黑）
            self.show()
            self.raise_()
            self.activateWindow()

            self._logger.debug(f"截图工具已启动，捕获 {len(screens)} 个屏幕，总尺寸: {total_rect.width()}x{total_rect.height()}")

        except Exception as e:
            self._logger.error(f"启动截图工具失败: {e}")
            self.screenshot_cancelled.emit()

    def paintEvent(self, event) -> None:
        """绘制半透明遮罩"""
        with QPainter(self) as painter:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 80))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """鼠标按下 - 开始选择"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            if self._rubber_band is None:
                self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self._rubber_band.setGeometry(QRect(self._origin, QSize()))
            self._rubber_band.show()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动 - 更新选区"""
        if self._rubber_band is not None and self._origin is not None:
            self._rubber_band.setGeometry(
                QRect(self._origin, event.pos()).normalized()
            )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """鼠标释放 - 完成截图"""
        if event.button() == Qt.MouseButton.LeftButton and self._rubber_band:
            self._rubber_band.hide()

            # 获取选区
            rect = self._rubber_band.geometry()
            if rect.width() > 10 and rect.height() > 10:  # 最小尺寸限制
                # 调整选区坐标，考虑截图偏移量
                adjusted_rect = QRect(
                    rect.x() - self._screenshot_offset.x(),
                    rect.y() - self._screenshot_offset.y(),
                    rect.width(),
                    rect.height()
                )
                # 从全屏截图中裁剪选区
                captured = self._screenshot.copy(adjusted_rect)
                self._logger.debug(f"截图完成: {adjusted_rect.width()}x{adjusted_rect.height()}")

                self.hide()
                self.screenshot_captured.emit(captured)
            else:
                # 选区太小，取消
                self._logger.debug("选区太小，取消截图")
                self.hide()
                self.screenshot_cancelled.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """按键事件"""
        if event.key() == Qt.Key.Key_Escape:
            self._logger.debug("用户取消截图")
            self.hide()
            self.screenshot_cancelled.emit()

