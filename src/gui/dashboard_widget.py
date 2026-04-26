# -*- coding: utf-8 -*-
"""工作台主页 - Dashboard Widget

展示 KPI 卡片、可视化图表、工作队列和快捷操作。
"""

import math
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QGridLayout,
)
from PySide6.QtCore import Qt, QRect, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics, QPainterPath, QCursor
from PySide6.QtWidgets import QApplication, QMessageBox

from src.core.case_manager import get_case_manager
from src.core.ocr import format_ocr_setup_message, get_ocr_dependency_status
from src.gui.styles import APP_COLORS as COLORS
from src.gui.widgets.ocr_worker import OcrWorker
from src.gui.widgets.screenshot_tool import ScreenshotTool
from src.utils.logger import get_logger


def _deadline_target_date(deadline: Dict[str, Any]) -> Optional[date]:
    """解析期限的目标日期。"""
    date_text = str(deadline.get("date", "")).strip()
    if not date_text:
        return None
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _deadline_is_completed(deadline: Dict[str, Any]) -> bool:
    return str(deadline.get("status", "pending")).strip() == "completed"


class DashboardWidget(QWidget):
    """工作台主页 Widget"""

    # 导航请求信号
    navigate_to_cases_requested = Signal()
    navigate_to_calendar_requested = Signal()
    navigate_to_documents_requested = Signal()
    navigate_to_tools_requested = Signal()
    navigate_to_archive_requested = Signal()
    new_case_requested = Signal()
    new_deadline_requested = Signal()
    open_case_deadline_requested = Signal(str, str)  # case_id, deadline_id
    filter_cases_by_status_requested = Signal(str)     # status_value
    filter_cases_by_category_requested = Signal(str)   # filter_value
    open_tools_tab_requested = Signal(str)             # tab_key: court_sms | screenshot_merge
    import_case_requested = Signal()
    open_ocr_requested = Signal()
    show_directory_abnormal_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger()
        self._cm = get_case_manager()
        self._screenshot_tool = ScreenshotTool(self)
        self._screenshot_tool.screenshot_captured.connect(self._on_ocr_screenshot_captured)
        self._screenshot_tool.screenshot_cancelled.connect(self._on_ocr_cancelled)
        self._ocr_worker: Optional[OcrWorker] = None
        self._setup_ui()
        self.refresh_data()

    def refresh_data(self):
        """从 CaseManager 刷新所有展示数据。"""
        try:
            self._load_kpi_data()
            self._load_chart_data()
            self._load_task_queue()
        except Exception as exc:
            self._logger.error(f"刷新工作台数据失败: {exc}")

    # ------------------------------------------------------------------
    # OCR 截图识别（与案件详情页一致：截图 → 识别 → 复制到剪贴板）
    # ------------------------------------------------------------------
    def _on_ocr_click(self) -> None:
        """快捷操作：OCR 截图识别入口。"""
        status = get_ocr_dependency_status()
        if not status.available:
            QMessageBox.information(
                self, "OCR 增强能力说明", format_ocr_setup_message(status)
            )
            return
        self._screenshot_tool.start_screenshot()

    def _on_ocr_screenshot_captured(self, pixmap) -> None:
        """截图完成后启动 OCR。"""
        if pixmap.isNull():
            self._on_ocr_cancelled()
            return
        self._ocr_worker = OcrWorker(pixmap, self)
        self._ocr_worker.ocr_completed.connect(self._on_ocr_completed)
        self._ocr_worker.ocr_failed.connect(self._on_ocr_failed)
        self._ocr_worker.start()

    def _on_ocr_cancelled(self) -> None:
        """用户取消截图。"""
        pass

    def _on_ocr_completed(self, text: str, text_blocks: List[Any]) -> None:
        """OCR 识别完成：结果复制到剪贴板。"""
        if self._ocr_worker is not None:
            self._ocr_worker.deleteLater()
            self._ocr_worker = None

        text = text.strip()
        if not text:
            QMessageBox.information(
                self, "OCR识别", "未能识别到文字，请尝试截取更清晰的区域。"
            )
            return

        QApplication.clipboard().setText(text)
        preview = text.replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:80] + "..."
        QMessageBox.information(
            self,
            "OCR识别完成",
            f"识别结果已复制到剪贴板，可直接粘贴到笔记或案件信息中。\n\n{preview}",
        )

    def _on_ocr_failed(self, error: str) -> None:
        """OCR 识别失败。"""
        self._logger.error(f"工作台 OCR 识别失败: {error}")
        if self._ocr_worker is not None:
            self._ocr_worker.deleteLater()
            self._ocr_worker = None
        QMessageBox.warning(
            self, "OCR识别失败", f"无法识别截图内容：\n{error}"
        )

    def _setup_ui(self):
        c = COLORS
        self.setStyleSheet(f"background: {c['surface_1']};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # === KPI Cards ===
        self._kpi_layout = QHBoxLayout()
        self._kpi_layout.setSpacing(12)
        self._kpi_cards: Dict[str, QFrame] = {}
        self._kpi_labels: Dict[str, QLabel] = {}

        kpi_defs = [
            ("total", "案件总数", "kpi-accent", "+5 本月新增"),
            ("active", "进行中", "kpi-success", ""),
            ("overdue", "已逾期", "kpi-danger", "需立即处理"),
            ("upcoming", "近7天到期", "kpi-warning", ""),
            ("today", "今日待办", "kpi-info", ""),
            ("abnormal", "目录异常", "kpi-purple", "路径缺失或变更"),
        ]

        for key, label, style_class, hint in kpi_defs:
            card = self._create_kpi_card(key, label, style_class, hint)
            self._kpi_layout.addWidget(card, 1)

        layout.addLayout(self._kpi_layout)

        # === Middle Grid: Charts + Task Queue ===
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        # Left: Status Donut Chart
        self._status_chart = _DonutChartWidget()
        self._status_chart.setMinimumSize(280, 280)
        mid_row.addWidget(self._status_chart, 1)

        # Center: Category Bar Chart
        self._category_chart = _BarChartWidget()
        self._category_chart.setMinimumSize(280, 280)
        self._category_chart.bar_clicked.connect(self._on_category_bar_clicked)
        mid_row.addWidget(self._category_chart, 1)

        # Right: Today's Tasks
        self._task_queue = _TaskQueueWidget()
        self._task_queue.setMinimumWidth(340)
        self._task_queue.setMaximumWidth(420)
        self._task_queue.setMinimumHeight(280)
        self._task_queue.task_clicked.connect(self.open_case_deadline_requested.emit)
        mid_row.addWidget(self._task_queue, 1)

        layout.addLayout(mid_row)

        # === Bottom Grid: Trend + Quick Actions ===
        bot_row = QHBoxLayout()
        bot_row.setSpacing(16)

        # Trend Chart
        self._trend_chart = _TrendChartWidget()
        self._trend_chart.setMinimumHeight(240)
        bot_row.addWidget(self._trend_chart, 2)

        # Quick Actions
        quick_actions = self._create_quick_actions()
        quick_actions.setMinimumWidth(340)
        quick_actions.setMaximumWidth(420)
        bot_row.addWidget(quick_actions, 1)

        layout.addLayout(bot_row)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_kpi_card(self, key: str, label: str, style_class: str, hint: str) -> QFrame:
        c = COLORS
        card = QFrame()
        card.setProperty("dashboardKpiCard", True)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        color_map = {
            "kpi-accent": c["accent"],
            "kpi-success": c["success"],
            "kpi-danger": c["danger"],
            "kpi-warning": c["warning"],
            "kpi-info": c["text_muted"],
            "kpi-purple": "#8b5cf6",
        }
        top_color = color_map.get(style_class, c["accent"])

        card.setStyleSheet(f"""
            QFrame[dashboardKpiCard="true"] {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(4)

        # Top colored line
        line = QFrame()
        line.setFixedHeight(3)
        line.setStyleSheet(f"background: {top_color}; border-radius: 2px;")
        layout.addWidget(line)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px; font-weight: 600;")
        layout.addWidget(label_widget)

        value_widget = QLabel("0")
        value_widget.setStyleSheet(f"color: {c['text_primary']}; font-size: 28px; font-weight: 800;")
        self._kpi_labels[key] = value_widget
        layout.addWidget(value_widget)

        if hint:
            hint_widget = QLabel(hint)
            hint_widget.setStyleSheet(f"color: {c['text_muted']}; font-size: 11px; font-weight: 500;")
            layout.addWidget(hint_widget)
        else:
            # 保持所有卡片行数一致，数字位置对齐
            spacer = QLabel("")
            spacer.setFixedHeight(16)
            layout.addWidget(spacer)

        # 点击跳转：案件相关 → 案件中心，期限相关 → 日历
        def _on_card_click(event, k=key):
            if k in ("total", "active", "abnormal"):
                self.navigate_to_cases_requested.emit()
            else:
                self.navigate_to_calendar_requested.emit()
        card.mousePressEvent = _on_card_click

        self._kpi_cards[key] = card
        return card

    def _create_quick_actions(self) -> QFrame:
        c = COLORS
        card = QFrame()
        card.setProperty("dashboardCard", True)
        card.setStyleSheet(f"""
            QFrame[dashboardCard="true"] {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("快捷操作")
        header.setStyleSheet(f"color: {c['text_primary']}; font-size: 14px; font-weight: 700;")
        layout.addWidget(header)

        sub = QLabel("常用功能入口")
        sub.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px; font-weight: 500;")
        layout.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(10)

        unified_bg = c["surface_1"]
        unified_fg = c["text_primary"]
        actions = [
            ("📁 导入案件", unified_bg, unified_fg, self.import_case_requested.emit),
            ("+ 新建期限", unified_bg, unified_fg, self.new_deadline_requested.emit),
            ("📨 法院短信", unified_bg, unified_fg, lambda: self.open_tools_tab_requested.emit("court_sms")),
            ("🔍 OCR识别", unified_bg, unified_fg, self._on_ocr_click),
            ("🖼️ 截图合并", unified_bg, unified_fg, lambda: self.open_tools_tab_requested.emit("screenshot_merge")),
            ("⚠️ 目录异常", unified_bg, unified_fg, self.show_directory_abnormal_requested.emit),
        ]

        for idx, (text, bg, fg, callback) in enumerate(actions):
            btn = QPushButton(text)
            btn.setFixedHeight(60)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    color: {fg};
                    border: 1px solid {c['border']};
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background: {c['surface_2']};
                    border-color: {c['border_strong']};
                }}
            """)
            btn.clicked.connect(callback)
            grid.addWidget(btn, idx // 2, idx % 2)

        layout.addLayout(grid)
        layout.addStretch()
        return card

    def _load_kpi_data(self):
        """加载 KPI 数据。"""
        try:
            cases = self._cm.get_all_cases()
            total = len(cases)
            active = sum(1 for c in cases if c.get("status") == "active")
            abnormal = sum(1 for c in cases if c.get("folder_status") != "available")

            # 统计期限
            overdue = 0
            upcoming = 0
            today_count = 0
            today = datetime.now().date()

            for case in cases:
                for dl in case.get("deadlines", []):
                    if _deadline_is_completed(dl):
                        continue
                    dl_date = _deadline_target_date(dl)
                    if dl_date is None:
                        continue
                    days = (dl_date - today).days
                    if days < 0:
                        overdue += 1
                    elif days <= 7:
                        upcoming += 1
                    if days == 0:
                        today_count += 1

            values = {
                "total": str(total),
                "active": str(active),
                "overdue": str(overdue),
                "upcoming": str(upcoming),
                "today": str(today_count),
                "abnormal": str(abnormal),
            }

            for key, val in values.items():
                if key in self._kpi_labels:
                    self._kpi_labels[key].setText(val)

        except Exception as exc:
            self._logger.error(f"加载 KPI 数据失败: {exc}")

    def _load_chart_data(self):
        """加载图表数据。"""
        try:
            cases = self._cm.get_all_cases()

            # 状态分布（与案件中心同步：推进中、未完结、待归档）
            status_counts = {}
            for case in cases:
                status = case.get("status", "active")
                status_counts[status] = status_counts.get(status, 0) + 1

            status_data = [
                (status_counts.get("active", 0), "#2563eb", "推进中"),
                (status_counts.get("pending", 0), "#f59e0b", "未完结"),
                (status_counts.get("closed", 0), "#10b981", "待归档"),
            ]
            self._status_chart.set_data(status_data)

            # 类型分布（只统计推进中案件，与案件中心分类同步）
            cat_counts = {}
            for case in cases:
                cat = case.get("category", "").strip()
                if not cat:
                    cat = ""
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

            all_cats = [
                ("", "未分类", "#94a3b8"),
                ("civil", "民事", "#2563eb"),
                ("criminal", "刑事", "#ef4444"),
                ("administrative", "行政", "#f59e0b"),
                ("non_litigation", "非诉", "#10b981"),
                ("labor_arbitration", "劳动仲裁", "#8b5cf6"),
                ("commercial_arbitration", "商事仲裁", "#06b6d4"),
            ]
            bar_data = []
            for cat_key, cat_name, cat_color in all_cats:
                count = cat_counts.get(cat_key, 0)
                bar_data.append((cat_name, count, cat_color))
            self._category_chart.set_data(bar_data)

            # 近30天期限密度（趋势图）
            today = datetime.now().date()
            trend_data = [0] * 30

            def _count_deadline(dl):
                if _deadline_is_completed(dl):
                    return
                dl_date = _deadline_target_date(dl)
                if dl_date is None:
                    return
                days = (dl_date - today).days
                if 0 <= days < 30:
                    trend_data[days] += 1

            # 关联案件的期限
            for case in cases:
                for dl in case.get("deadlines", []):
                    _count_deadline(dl)

            # 未关联案件的全局期限
            for dl in self._cm.get_global_deadlines():
                _count_deadline(dl)

            self._trend_chart.set_data(trend_data)

        except Exception as exc:
            self._logger.error(f"加载图表数据失败: {exc}")

    def _load_task_queue(self):
        """加载今日待办队列（包含关联案件和未关联案件的全局期限）。"""
        try:
            today = datetime.now().date()
            tasks = []

            def _process_deadline(dl, case_name, case_id):
                if _deadline_is_completed(dl):
                    return
                dl_date = _deadline_target_date(dl)
                if dl_date is None:
                    return
                days = (dl_date - today).days
                if days > 7:
                    return
                dl_type = dl.get("type", "deadline")
                if days < 0:
                    badge = "已逾期"
                    badge_class = "overdue"
                elif days == 0:
                    badge = "今天"
                    badge_class = "today"
                else:
                    badge = f"D-{days}"
                    badge_class = "d3"
                tasks.append({
                    "title": dl.get("title", "未命名"),
                    "case_name": case_name,
                    "case_id": case_id,
                    "deadline_id": str(dl.get("id", "")),
                    "type": dl_type,
                    "badge": badge,
                    "badge_class": badge_class,
                    "days": days,
                })

            # 关联案件的期限
            for case in self._cm.get_all_cases():
                case_name = case.get("name", "未命名")
                case_id = str(case.get("id", ""))
                for dl in case.get("deadlines", []):
                    _process_deadline(dl, case_name, case_id)

            # 未关联案件的全局期限
            for dl in self._cm.get_global_deadlines():
                _process_deadline(dl, "未关联案件", "")

            tasks.sort(key=lambda x: x["days"])
            self._task_queue.set_tasks(tasks)

        except Exception as exc:
            self._logger.error(f"加载任务队列失败: {exc}")

    def _on_abnormal(self):
        self.navigate_to_cases_requested.emit()

    def _on_category_bar_clicked(self, label: str):
        """条形图条形点击：按分类筛选案件。"""
        mapping = {
            "未分类": "",
            "民事": "civil",
            "刑事": "criminal",
            "行政": "administrative",
            "非诉": "non_litigation",
            "劳动仲裁": "labor_arbitration",
            "商事仲裁": "commercial_arbitration",
        }
        value = mapping.get(label)
        if value is not None:
            self.filter_cases_by_category_requested.emit(value)


# =============================================================================
# 自绘图表组件
# =============================================================================

class _DonutChartWidget(QWidget):
    """环形图组件（QPainter 自绘）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[tuple] = []
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    def set_data(self, data: List[tuple]):
        """data: [(value, color, label), ...]"""
        self._data = data
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        radius = min(cx, cy) - 50
        thickness = 22

        total = sum(item[0] for item in self._data)
        if total == 0:
            return

        start_angle = -90  # 12 o'clock

        for value, color_str, label in self._data:
            angle = (value / total) * 360
            pen = QPen(QColor(color_str))
            pen.setWidth(thickness)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(
                QRect(cx - radius, cy - radius, radius * 2, radius * 2),
                start_angle * 16,
                int(angle * 16)
            )
            start_angle += angle

        # Center text
        painter.setPen(QColor(COLORS["text_primary"]))
        font = QFont()
        font.setPointSize(18)
        font.setWeight(QFont.Weight.Black)
        painter.setFont(font)
        painter.drawText(QRect(cx - 40, cy - 20, 80, 30), Qt.AlignmentFlag.AlignCenter, str(total))

        painter.setPen(QColor(COLORS["text_muted"]))
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(QRect(cx - 40, cy + 8, 80, 20), Qt.AlignmentFlag.AlignCenter, "案件")

        # Legend — 与圆环底部保持间距
        legend_margin_bottom = 16
        legend_dot_size = 8
        legend_y = h - legend_margin_bottom - legend_dot_size
        x = 20
        for value, color_str, label in self._data:
            if value == 0:
                continue
            painter.setBrush(QBrush(QColor(color_str)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(x, legend_y, legend_dot_size, legend_dot_size)
            painter.setPen(QColor(COLORS["text_secondary"]))
            font.setPointSize(9)
            painter.setFont(font)
            text_rect = QRect(x + 14, legend_y - 2, 80, legend_dot_size + 4)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{label} {value}")
            x += 70


class _BarChartWidget(QWidget):
    """横向条形图组件"""

    bar_clicked = Signal(str)  # label

    MARGIN = 20
    LABEL_W = 60
    BAR_H = 20
    GAP = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[tuple] = []
        self._hover_idx = -1
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # macOS 上 mouseMoveEvent 不可靠，用 QTimer 轮询鼠标位置
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_hover)
        self._timer.start(50)
        self.setMouseTracking(True)

    def set_data(self, data: List[tuple]):
        """data: [(label, value, color), ...]"""
        self._data = data
        self.update()

    def _hit_bar_idx(self, y: int) -> int:
        start_y = self.MARGIN + 10
        for idx in range(len(self._data)):
            bar_top = start_y + idx * (self.BAR_H + self.GAP)
            if bar_top <= y < bar_top + self.BAR_H:
                return idx
        return -1

    def _update_hover(self):
        pos = self.mapFromGlobal(QCursor.pos())
        if self.rect().contains(pos):
            idx = self._hit_bar_idx(pos.y())
            if idx != self._hover_idx:
                self._hover_idx = idx
                self.setCursor(
                    Qt.CursorShape.PointingHandCursor
                    if idx >= 0
                    else Qt.CursorShape.ArrowCursor
                )
                self.update()
        else:
            if self._hover_idx != -1:
                self._hover_idx = -1
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.update()

    def mousePressEvent(self, event):
        idx = self._hit_bar_idx(event.pos().y())
        if 0 <= idx < len(self._data):
            self.bar_clicked.emit(self._data[idx][0])
            event.accept()

    def paintEvent(self, event):
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        max_val = max(item[1] for item in self._data) if self._data else 1
        if max_val == 0:
            max_val = 1

        margin = 20
        label_w = 60
        bar_h = 20
        gap = 14
        start_y = margin + 10

        for idx, (label, value, color_str) in enumerate(self._data):
            is_hovered = (idx == self._hover_idx)

            # Label — 使用 fontMetrics 精确定位，避免 QRect 裁剪
            painter.setPen(QColor(COLORS["text_secondary"]))
            font = QFont()
            font.setPointSize(10)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label)
            th = fm.height()
            tx = max(0, label_w - 8 - tw)
            ty = start_y + bar_h // 2 + th // 4
            painter.drawText(tx, ty, label)

            # Bar track
            track_x = label_w
            track_w = self.width() - label_w - margin
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(COLORS["surface_2"])))
            painter.drawRoundedRect(track_x, start_y + 2, track_w, bar_h - 4, 8, 8)

            # Bar fill
            fill_w = int((value / max_val) * track_w)
            if fill_w > 0:
                if is_hovered:
                    # hover 时先设置 clip，防止小 fill 的圆角溢出 border 内边缘
                    painter.save()
                    path = QPainterPath()
                    path.addRoundedRect(track_x + 1, start_y + 3, track_w - 2, bar_h - 6, 7, 7)
                    painter.setClipPath(path)

                painter.setBrush(QBrush(QColor(color_str)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(track_x, start_y + 2, fill_w, bar_h - 4, 8, 8)

                if is_hovered:
                    painter.restore()

            # Hover highlight — 悬停时绘制高亮边框（与 track 同大小，避免白边）
            if is_hovered:
                painter.setPen(QPen(QColor(COLORS["accent"]), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(track_x, start_y + 2, track_w, bar_h - 4, 8, 8)

            # Value text — 始终显示在条形右侧外部
            painter.setPen(QColor(COLORS["text_primary"]))
            font.setPointSize(9)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            fm = painter.fontMetrics()
            value_text = str(value)
            vw = fm.horizontalAdvance(value_text)
            vh = fm.height()
            value_x = track_x + fill_w + 8
            value_y = start_y + bar_h // 2 + vh // 4
            painter.drawText(value_x, value_y, value_text)

            start_y += bar_h + gap


class _TrendChartWidget(QWidget):
    """折线图组件（近30天期限密度）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[int] = []
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: List[int]):
        self._data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        padding = {"top": 48, "right": 20, "bottom": 35, "left": 35}
        cw = w - padding["left"] - padding["right"]
        ch = h - padding["top"] - padding["bottom"]

        data = self._data if self._data else [0] * 30
        max_val = max(data) + 1 if data else 5
        if max_val < 1:
            max_val = 1

        # Title
        painter.setOpacity(0.85)
        painter.setPen(QColor(COLORS["text_primary"]))
        font = QFont()
        font.setPointSize(12)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            QRect(padding["left"], 6, w - padding["left"] - padding["right"], 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Deadline趋势图"
        )

        painter.setOpacity(0.6)
        painter.setPen(QColor(COLORS["text_muted"]))
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(
            QRect(padding["left"], 26, w - padding["left"] - padding["right"], 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "近30天案件期限分布"
        )
        painter.setOpacity(1.0)

        # Grid lines
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        for i in range(5):
            y = padding["top"] + (ch / 4) * i
            painter.drawLine(int(padding["left"]), int(y), int(w - padding["right"]), int(y))

        # Y axis labels
        painter.setPen(QColor(COLORS["text_muted"]))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        for i in range(5):
            val = int(max_val - (max_val / 4) * i)
            y = padding["top"] + (ch / 4) * i
            painter.drawText(
                QRect(0, int(y) - 8, padding["left"] - 6, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(val)
            )

        # X axis labels
        for idx in [0, 9, 19, 29]:
            x = padding["left"] + (idx / 29) * cw
            painter.drawText(
                QRect(int(x) - 15, h - padding["bottom"] + 6, 30, 16),
                Qt.AlignmentFlag.AlignCenter,
                f"{idx + 1}日"
            )

        # Fill area
        if len(data) > 1:
            path = QPainterPath()
            x0 = padding["left"]
            y0 = padding["top"] + ch - (data[0] / max_val) * ch
            path.moveTo(x0, y0)

            for idx, val in enumerate(data):
                x = padding["left"] + (idx / (len(data) - 1)) * cw
                y = padding["top"] + ch - (val / max_val) * ch
                path.lineTo(x, y)

            path.lineTo(padding["left"] + cw, padding["top"] + ch)
            path.lineTo(padding["left"], padding["top"] + ch)
            path.closeSubpath()

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#2563eb"), Qt.BrushStyle.SolidPattern))
            painter.setOpacity(0.08)
            painter.drawPath(path)
            painter.setOpacity(1.0)

        # Line
        painter.setPen(QPen(QColor("#2563eb"), 2.5))
        for idx in range(len(data) - 1):
            x1 = padding["left"] + (idx / (len(data) - 1)) * cw
            y1 = padding["top"] + ch - (data[idx] / max_val) * ch
            x2 = padding["left"] + ((idx + 1) / (len(data) - 1)) * cw
            y2 = padding["top"] + ch - (data[idx + 1] / max_val) * ch
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Dots
        for idx, val in enumerate(data):
            if val == 0:
                continue
            x = padding["left"] + (idx / (len(data) - 1)) * cw
            y = padding["top"] + ch - (val / max_val) * ch
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#2563eb")))
            painter.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(int(x) - 2, int(y) - 2, 4, 4)


class _TaskQueueWidget(QFrame):
    """今日待办队列 Widget"""

    task_clicked = Signal(str, str)  # case_id, deadline_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        c = COLORS
        self.setProperty("dashboardCard", True)
        self.setStyleSheet(f"""
            QFrame[dashboardCard="true"] {{
                background: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("待办/提醒")
        title.setStyleSheet(f"color: {c['text_primary']}; font-size: 14px; font-weight: 700;")
        header.addWidget(title)

        self._count_badge = QLabel("0 项")
        self._count_badge.setStyleSheet(f"""
            color: {c['danger']};
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            background: #fef2f2;
            border-radius: 999px;
        """)
        header.addWidget(self._count_badge)
        layout.addLayout(header)

        sub = QLabel(datetime.now().strftime("%m月%d日 · %a"))
        sub.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px; font-weight: 500;")
        layout.addWidget(sub)

        # Task list container (带滚动条)
        self._task_container = QWidget()
        self._task_layout = QVBoxLayout(self._task_container)
        self._task_layout.setContentsMargins(0, 0, 0, 0)
        self._task_layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['surface_3']};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)
        scroll.setWidget(self._task_container)
        layout.addWidget(scroll, 1)

        layout.addStretch()

    def set_tasks(self, tasks: List[Dict]):
        # Clear existing
        while self._task_layout.count():
            item = self._task_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._count_badge.setText(f"{len(tasks)} 项")

        for task in tasks:
            row = self._create_task_row(task)
            self._task_layout.addWidget(row)

        self._task_layout.addStretch()

    def _create_task_row(self, task: Dict) -> QFrame:
        c = COLORS
        row = QFrame()
        row.setObjectName("taskRow")
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.setStyleSheet(f"""
            QFrame#taskRow {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
            }}
            QFrame#taskRow:hover {{
                background: {c['surface_1']};
                border-color: {c['border']};
            }}
        """)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Type dot
        dl_type = task.get("type", "deadline")
        dot_color = {
            "hearing": c["danger"],
            "deadline": c["warning"],
            "custom": c["accent"],
        }.get(dl_type, c["warning"])

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {dot_color}; border-radius: 4px;")
        layout.addWidget(dot)

        # Content
        content_widget = QWidget()
        content_widget.setMaximumWidth(max(150, self.minimumWidth() - 140))
        content = QVBoxLayout(content_widget)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(2)

        title = QLabel(task.get("title", ""))
        title.setStyleSheet(f"color: {c['text_primary']}; font-size: 13px; font-weight: 600;")
        title.setWordWrap(True)
        content.addWidget(title)

        meta = QLabel(f"{task.get('case_name', '')}")
        meta.setStyleSheet(f"color: {c['text_muted']}; font-size: 11px; font-weight: 500;")
        meta.setWordWrap(True)
        content.addWidget(meta)

        layout.addWidget(content_widget, 1)

        # Badge
        badge_class = task.get("badge_class", "")
        badge_text = task.get("badge", "")
        if not badge_text:
            badge_text = ""
        badge_style = {
            "overdue": f"background: #fef2f2; color: {c['danger']};",
            "today": f"background: {c['accent_subtle']}; color: {c['accent']};",
            "d3": "background: #fffbeb; color: #b45309;",
        }.get(badge_class, f"background: {c['surface_2']}; color: {c['text_secondary']};")

        badge = QLabel(badge_text)
        badge.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            {badge_style}
        """)
        layout.addWidget(badge)

        # 点击跳转：关联案件 → 案件中心期限签页；未关联 → 日历
        case_id = task.get("case_id", "")
        deadline_id = task.get("deadline_id", "")
        row.mousePressEvent = lambda event, cid=case_id, did=deadline_id: self.task_clicked.emit(cid, did)

        return row
