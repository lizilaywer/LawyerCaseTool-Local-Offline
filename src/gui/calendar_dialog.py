# -*- coding: utf-8 -*-
"""期限日历对话框 - Modern UI v3

独立窗口，提供月视图概览与当天期限详情。
"""

from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QMessageBox,
    QComboBox,
)
from PySide6.QtCore import Qt, QRect, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics

from src.core.case_manager import get_case_manager
from src.gui.case_aux_dialogs import DeadlineEditorDialog
from src.gui.styles import APP_COLORS as COLORS, CHECK_ICON_PATH
from src.gui.window_metrics import APP_SURFACE_DEFAULT_SIZE, APP_SURFACE_MIN_SIZE
from src.utils.logger import get_logger
from src.utils.runtime_adapters import TimeProvider

DROPDOWN_ARROW_PATH = CHECK_ICON_PATH.replace("check.svg", "dropdown_arrow.svg")


def _deadline_target_datetime(deadline: Dict[str, Any]) -> Optional[datetime]:
    """构建期限对应的目标时间。"""
    date_text = str(deadline.get("date", "")).strip()
    if not date_text:
        return None
    time_text = str(deadline.get("time", "")).strip()
    try:
        if deadline.get("all_day", not time_text):
            return datetime.strptime(date_text, "%Y-%m-%d")
        return datetime.strptime(f"{date_text} {time_text[:5]}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _deadline_is_completed(deadline: Dict[str, Any]) -> bool:
    """判断期限是否已完成。"""
    return str(deadline.get("status", "pending")).strip() == "completed"


def _deadline_is_overdue(deadline: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """判断期限是否已过期。已完成事项不再视为过期。"""
    if _deadline_is_completed(deadline):
        return False

    target = _deadline_target_datetime(deadline)
    if target is None:
        return False

    current = now or datetime.now()
    if deadline.get("all_day", True):
        return target.date() < current.date()
    return target < current


def _deadline_days_until(deadline: Dict[str, Any], today: Optional[date] = None) -> Optional[int]:
    """返回期限距今天的天数。"""
    target = _deadline_target_datetime(deadline)
    if target is None:
        return None
    current_day = today or datetime.now().date()
    return (target.date() - current_day).days


def _deadline_date_value(deadline: Dict[str, Any]) -> Optional[date]:
    """返回期限对应的日期对象。"""
    target = _deadline_target_datetime(deadline)
    if target is not None:
        return target.date()

    date_text = str(deadline.get("date", "")).strip()
    if not date_text:
        return None
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize_tag_list(tags: Any) -> List[str]:
    """规范化标签列表。"""
    if not isinstance(tags, (list, tuple, set)):
        return []

    result: List[str] = []
    seen = set()
    for tag in tags:
        text = str(tag or "").strip().lstrip("#")
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


class DeadlineCalendarWidget(QWidget):
    """日历控件 - 在日期格中绘制期限预览卡片"""

    HEADER_HEIGHT = 32
    CELL_GAP = 6
    CARD_RADIUS = 12
    WEEK_TIME_RULER_WIDTH = 72
    WEEK_START_HOUR = 6
    WEEK_END_HOUR = 24
    WEEK_SNAP_MINUTES = 5

    # 期限类型颜色
    TYPE_COLORS = {
        "deadline": QColor("#f97316"),    # 橙色 - 普通期限
        "hearing": QColor("#dc2626"),     # 红色 - 开庭（最高优先）
        "custom": QColor("#f59e0b"),      # 黄色 - 自定义
    }

    def __init__(self, parent=None, time_provider: Optional[TimeProvider] = None):
        super().__init__(parent)
        self._logger = get_logger()
        self._time_provider = time_provider or TimeProvider()
        today = self._time_provider.today()
        self._year = today.year
        self._month = today.month
        self._view_mode = "month"
        self._week_start = today - timedelta(days=today.weekday())
        self._selected_date: Optional[date] = None
        self._deadlines: Dict[str, List[Dict]] = {}  # "YYYY-MM-DD" -> [deadline_dicts]
        self._card_hit_regions: List[tuple[QRect, date]] = []
        self._preview_hit_regions: List[tuple[QRect, Dict[str, Any]]] = []
        self._more_hit_regions: List[tuple[QRect, date]] = []
        self._expanded_more_date: Optional[date] = None
        self._expanded_card_region: Optional[QRect] = None
        self._deadline_drag_callback = None
        self._drag_candidate: Optional[Dict[str, Any]] = None
        self._drag_deadline: Optional[Dict[str, Any]] = None
        self._drag_start_point: Optional[QPoint] = None
        self._drag_offset_y = 0
        self._drag_hover_date: Optional[date] = None
        self._drag_hover_minutes: Optional[int] = None
        self._days_in_month = self._get_days_in_month()
        self._first_day_weekday = self._get_first_day_weekday()
        self.setMinimumSize(560, 420)
        self.setMouseTracking(True)
        self.date_clicked = None  # 将在 set_callbacks 后赋值
        self.date_double_clicked = None
        self.deadline_double_clicked = None

    def set_date_clicked_callback(self, callback) -> None:
        self.date_clicked = callback

    def set_date_double_clicked_callback(self, callback) -> None:
        self.date_double_clicked = callback

    def set_deadline_double_clicked_callback(self, callback) -> None:
        self.deadline_double_clicked = callback

    def set_deadline_drag_callback(self, callback) -> None:
        self._deadline_drag_callback = callback

    def set_selected_date(self, value: Optional[date]) -> None:
        """设置当前选中的日期。"""
        self._selected_date = value
        if value is not None:
            self._week_start = value - timedelta(days=value.weekday())
        self.update()

    def set_deadlines(self, deadlines: List[Dict]) -> None:
        """设置期限数据"""
        self._deadlines.clear()
        self._expanded_more_date = None
        for dl in deadlines:
            dl_date = dl.get("date", "")
            if dl_date in self._deadlines:
                self._deadlines[dl_date].append(dl)
            else:
                self._deadlines[dl_date] = [dl]
        for items in self._deadlines.values():
            items.sort(key=self._deadline_sort_key)
        self.update()

    def set_month(self, year: int, month: int) -> None:
        """设置显示的年月"""
        self._year = year
        self._month = month
        self._expanded_more_date = None
        self._days_in_month = self._get_days_in_month()
        self._first_day_weekday = self._get_first_day_weekday()
        if self._selected_date and (self._selected_date.year != year or self._selected_date.month != month):
            self._selected_date = date(year, month, 1)
            self._week_start = self._selected_date - timedelta(days=self._selected_date.weekday())
        elif self._selected_date is None:
            target = date(year, month, 1)
            self._week_start = target - timedelta(days=target.weekday())
        self.update()

    def set_view_mode(self, mode: str, anchor_date: Optional[date] = None) -> None:
        """设置日历显示模式。"""
        if mode not in {"month", "week"}:
            return
        self._view_mode = mode
        self._expanded_more_date = None
        target = anchor_date or self._selected_date or date(self._year, self._month, 1)
        self._week_start = target - timedelta(days=target.weekday())
        if self._selected_date is None:
            self._selected_date = target
        self.update()

    def get_view_mode(self) -> str:
        return self._view_mode

    def get_selected_date(self) -> Optional[date]:
        return self._selected_date

    def _is_selected_day(self, day: int) -> bool:
        """判断给定日期是否为当前选中日期。"""
        if self._selected_date is None:
            return False
        return (
            self._year == self._selected_date.year
            and self._month == self._selected_date.month
            and day == self._selected_date.day
        )

    def _is_selected_date(self, value: date) -> bool:
        return self._selected_date == value

    def _header_height(self) -> int:
        return 54 if self._view_mode == "week" else self.HEADER_HEIGHT

    def _row_count(self) -> int:
        if self._view_mode == "week":
            return 1
        return self._month_week_count()

    def _month_week_count(self) -> int:
        """按当月实际占用周数动态决定月视图行数。"""
        total_slots = self._first_day_weekday + self._days_in_month
        return max(4, (total_slots + 6) // 7)

    def _get_days_in_month(self) -> int:
        import calendar
        return calendar.monthrange(self._year, self._month)[1]

    def _get_first_day_weekday(self) -> int:
        """获取月份第一天是星期几（0=周一，6=周日）"""
        return date(self._year, self._month, 1).weekday()

    def _day_rect(self, row: int, col: int) -> QRect:
        """计算某天对应的矩形区域（用于点击检测），确保最后一列/行填满边界。"""
        w = self.width()
        h = self.height()
        cell_w = w / 7
        header_h = self._header_height()
        cell_h = (h - header_h) / self._row_count()
        x = int(col * cell_w)
        y = int(header_h + row * cell_h)
        # 最后一列/行用剩余空间，避免累积舍入误差导致空白
        if col == 6:
            width = max(1, w - x)
        else:
            width = max(1, int(cell_w))
        if row == self._row_count() - 1:
            height = max(1, h - y)
        else:
            height = max(1, int(cell_h))
        return QRect(x, y, width, height)

    def _card_rect(self, row: int, col: int) -> QRect:
        """返回可见的日期卡片区域。"""
        if min(self.width(), self.height()) >= 520:
            gap = self.CELL_GAP
        elif min(self.width(), self.height()) >= 400:
            gap = 4
        else:
            gap = 2
        return self._day_rect(row, col).adjusted(
            gap // 2,
            gap // 2,
            -gap // 2,
            -gap // 2,
        )

    def _date_at_pos(self, x: int, y: int) -> Optional[date]:
        """根据鼠标位置返回日期"""
        header_h = self._header_height()
        if y < header_h:
            if self._view_mode == "week":
                return self._week_day_at_x(x)
            return None
        if self._view_mode == "week":
            return self._week_day_at_x(x)
        cell_w = self.width() / 7
        cell_h = (self.height() - header_h) / self._row_count()
        col = min(6, max(0, int(x / cell_w)))
        row = min(self._row_count() - 1, max(0, int((y - header_h) / cell_h)))
        day = row * 7 + col - self._first_day_weekday + 1
        if day < 1 or day > self._days_in_month:
            return None
        try:
            return date(self._year, self._month, day)
        except ValueError:
            return None

    def _week_dates(self) -> List[date]:
        return [self._week_start + timedelta(days=index) for index in range(7)]

    def _week_grid_rect(self) -> QRect:
        return QRect(
            self.WEEK_TIME_RULER_WIDTH,
            self._header_height(),
            max(0, self.width() - self.WEEK_TIME_RULER_WIDTH - 2),
            max(0, self.height() - self._header_height() - 2),
        )

    def _week_day_column_width(self) -> float:
        grid = self._week_grid_rect()
        return grid.width() / 7 if grid.width() > 0 else 0.0

    def _week_day_at_x(self, x: int) -> Optional[date]:
        grid = self._week_grid_rect()
        if x < grid.left() or x >= grid.right():
            return None
        column_width = self._week_day_column_width()
        if column_width <= 0:
            return None
        col = int((x - grid.left()) / column_width)
        if col < 0 or col > 6:
            return None
        return self._week_start + timedelta(days=col)

    def _week_hour_height(self) -> float:
        grid = self._week_grid_rect()
        total_hours = self.WEEK_END_HOUR - self.WEEK_START_HOUR
        return grid.height() / total_hours if total_hours > 0 else 0.0

    def _week_minutes_for_deadline(self, deadline: Dict[str, Any]) -> int:
        time_text = str(deadline.get("time", "")).strip()
        if time_text:
            try:
                hours, minutes = time_text[:5].split(":")
                total = int(hours) * 60 + int(minutes)
                return max(self.WEEK_START_HOUR * 60, min(total, self.WEEK_END_HOUR * 60 - self.WEEK_SNAP_MINUTES))
            except (TypeError, ValueError):
                pass
        return 9 * 60

    def _week_snap_minutes(self, total_minutes: int) -> int:
        minimum = self.WEEK_START_HOUR * 60
        maximum = self.WEEK_END_HOUR * 60 - self.WEEK_SNAP_MINUTES
        snapped = round(total_minutes / self.WEEK_SNAP_MINUTES) * self.WEEK_SNAP_MINUTES
        return max(minimum, min(snapped, maximum))

    def _week_minutes_to_time_text(self, total_minutes: int) -> str:
        hours = max(0, total_minutes // 60)
        minutes = max(0, total_minutes % 60)
        return f"{hours:02d}:{minutes:02d}"

    def _week_y_to_minutes(self, y: int) -> int:
        grid = self._week_grid_rect()
        hour_height = self._week_hour_height()
        if hour_height <= 0:
            return self.WEEK_START_HOUR * 60
        clamped = max(grid.top(), min(y, grid.bottom()))
        offset_hours = (clamped - grid.top()) / hour_height
        raw_minutes = int(self.WEEK_START_HOUR * 60 + offset_hours * 60)
        return self._week_snap_minutes(raw_minutes)

    def _week_minutes_to_y(self, total_minutes: int) -> int:
        grid = self._week_grid_rect()
        hour_height = self._week_hour_height()
        total_minutes = max(self.WEEK_START_HOUR * 60, min(total_minutes, self.WEEK_END_HOUR * 60))
        offset_hours = (total_minutes - self.WEEK_START_HOUR * 60) / 60
        return int(grid.top() + offset_hours * hour_height)

    def _week_deadline_rect(self, deadline: Dict[str, Any]) -> Optional[QRect]:
        deadline_day = _deadline_date_value(deadline)
        if deadline_day is None or not (self._week_start <= deadline_day <= self._week_start + timedelta(days=6)):
            return None
        grid = self._week_grid_rect()
        column_width = self._week_day_column_width()
        if column_width <= 0:
            return None
        day_index = (deadline_day - self._week_start).days
        block_left = int(grid.left() + day_index * column_width + 6)
        block_width = int(max(56, column_width - 12))
        start_minutes = self._week_minutes_for_deadline(deadline)
        block_top = self._week_minutes_to_y(start_minutes)
        min_height = 34
        if str(deadline.get("type", "deadline")) == "hearing":
            block_height = max(42, int(self._week_hour_height() * 0.95))
        else:
            block_height = max(min_height, int(self._week_hour_height() * 0.72))
        bottom_limit = grid.bottom() - 4
        if block_top + block_height > bottom_limit:
            block_top = max(grid.top() + 2, bottom_limit - block_height)
        return QRect(block_left, block_top, block_width, block_height)

    def _deadline_at_pos(self, point: QPoint) -> Optional[Dict[str, Any]]:
        for rect, deadline in reversed(self._preview_hit_regions):
            if rect.contains(point):
                return deadline
        return None

    def _deadline_sort_key(self, deadline: Dict[str, Any]) -> tuple:
        """期限排序：未完成优先、开庭优先、再按具体时间。"""
        is_completed = 1 if _deadline_is_completed(deadline) else 0
        type_rank = {
            "hearing": 0,
            "deadline": 1,
            "custom": 2,
        }.get(str(deadline.get("type", "deadline")), 3)
        has_time = 0 if str(deadline.get("time", "")).strip() else 1
        time_text = str(deadline.get("time", "")).strip() or "99:99"
        priority_rank = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }.get(str(deadline.get("priority", "medium")), 1)
        return (
            is_completed,
            type_rank,
            priority_rank,
            has_time,
            time_text,
            str(deadline.get("title", "")).strip(),
        )

    @staticmethod
    def _same_deadline(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
        """判断两个期限是否指向同一条记录。"""
        left_id = str(left.get("id", "")).strip()
        right_id = str(right.get("id", "")).strip()
        if left_id and right_id:
            return (
                left_id == right_id
                and str(left.get("case_id", "")).strip() == str(right.get("case_id", "")).strip()
            )
        return (
            str(left.get("title", "")).strip() == str(right.get("title", "")).strip()
            and str(left.get("date", "")).strip() == str(right.get("date", "")).strip()
            and str(left.get("time", "")).strip() == str(right.get("time", "")).strip()
            and str(left.get("case_id", "")).strip() == str(right.get("case_id", "")).strip()
        )

    def _month_render_deadlines(self, day_value: date, deadlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """月视图拖拽时，返回包含拖拽预览的当日事项列表。"""
        if self._view_mode != "month" or self._drag_deadline is None:
            return list(deadlines)

        source_date = _deadline_date_value(self._drag_deadline)
        render_items = [item for item in deadlines if not self._same_deadline(item, self._drag_deadline)]
        if self._drag_hover_date == day_value:
            preview_deadline = dict(self._drag_deadline)
            preview_deadline["date"] = day_value.strftime("%Y-%m-%d")
            render_items.append(preview_deadline)
        elif source_date == day_value and self._drag_hover_date != day_value:
            # 已在上面移除源事项，用于预览“从原日期挪走”
            pass
        else:
            render_items = list(deadlines)

        render_items.sort(key=self._deadline_sort_key)
        return render_items

    def _type_base_color(self, deadline_type: str) -> QColor:
        return QColor(self.TYPE_COLORS.get(deadline_type, self.TYPE_COLORS["deadline"]))

    def _deadline_target_datetime(self, deadline: Dict[str, Any]) -> Optional[datetime]:
        return _deadline_target_datetime(deadline)

    def _deadline_visual_style(self, deadline: Dict[str, Any]) -> Dict[str, Any]:
        """返回期限预览在日历中的视觉样式。"""
        c = COLORS
        deadline_type = str(deadline.get("type", "deadline"))
        indicator_color = self._type_base_color(deadline_type)
        text_color = QColor(c['text_secondary'])
        background_alpha = 24

        if deadline_type == "hearing":
            text_color = QColor("#7f1d1d")
            background_alpha = 34

        style = {
            "state": "normal",
            "indicator_color": indicator_color,
            "text_color": text_color,
            "strike_out": False,
            "background_alpha": background_alpha,
        }

        if _deadline_is_completed(deadline):
            style.update({
                "state": "completed",
                "indicator_color": QColor(c['text_muted']),
                "text_color": QColor(c['text_muted']),
                "strike_out": True,
                "background_alpha": 30,
            })
            return style

        if _deadline_is_overdue(deadline):
            style.update({
                "state": "overdue",
                "indicator_color": QColor("#9ca3af"),
                "text_color": QColor(c['text_tertiary']),
                "background_alpha": 34,
            })

        return style

    def _day_visual_state(self, day_value: date, deadlines: List[Dict[str, Any]]) -> tuple[str, str]:
        """返回日期卡的视觉状态和右上角标签。"""
        pending = [item for item in deadlines if not _deadline_is_completed(item)]
        if not pending:
            return "normal", f"{len(deadlines)}项" if deadlines else ""

        today_value = self._time_provider.today()

        if any(str(item.get("type", "deadline")) == "hearing" for item in pending):
            return "hearing", "开庭"

        if any(_deadline_is_overdue(item, self._time_provider.now()) for item in pending):
            return "overdue", "已过期"

        if day_value == today_value:
            return "today", "今天"

        delta_days = (day_value - today_value).days
        if 0 < delta_days <= 7:
            return "upcoming", "近7天"

        return "normal", f"{len(deadlines)}项"

    def _time_label(self, deadline: Dict[str, Any]) -> str:
        """格式化期限时间文本。"""
        time_text = str(deadline.get("time", "")).strip()
        all_day = bool(deadline.get("all_day", not time_text))
        if all_day:
            return "全天"
        if time_text:
            return time_text[:5]
        return "待定"

    def _format_deadline_preview(self, deadline: Dict[str, Any]) -> str:
        """格式化日历格中的简要预览文本。"""
        title = str(deadline.get("title", "")).strip() or "未命名事项"
        case_name = str(deadline.get("case_name", "")).strip()
        case_short = case_name[:8] if case_name else ""
        is_hearing = str(deadline.get("type", "deadline")) == "hearing"
        type_label = "开庭" if is_hearing and case_short else title
        countdown = self._countdown_badge(deadline)
        parts = [self._time_label(deadline), type_label]
        if case_short:
            parts.append(case_short)
        if countdown:
            parts.append(countdown)
        return " · ".join(part for part in parts if part).strip()

    def _case_label(self, deadline: Dict[str, Any], limit: int = 10) -> str:
        """返回适合在日历中显示的案件简称。"""
        case_name = str(deadline.get("case_name", "")).strip()
        if not case_name:
            return ""
        if len(case_name) <= limit:
            return case_name
        return case_name[:limit] + "…"

    def _format_compact_deadline_preview(self, deadline: Dict[str, Any], card_width: int) -> str:
        """针对窄卡片生成更短的预览文本。"""
        title = str(deadline.get("title", "")).strip() or "未命名事项"
        time_label = self._time_label(deadline)
        countdown = self._countdown_badge(deadline)
        if str(deadline.get("type", "deadline")) == "hearing":
            case_short = self._case_label(deadline, 4 if card_width < 100 else (6 if card_width < 132 else 8))
            focus_text = "开庭"
            if card_width >= 112:
                return " ".join(part for part in [time_label, focus_text, case_short, countdown] if part).strip()
            if card_width >= 88:
                return " ".join(part for part in [focus_text, case_short or countdown] if part).strip()
            if card_width >= 72:
                return focus_text if not case_short else f"{focus_text} {case_short}"
            return focus_text
        if card_width >= 112:
            return f"{time_label} {title} {countdown}".strip()
        if card_width >= 88 and time_label not in {"全天", "待定"}:
            return f"{time_label} {title}".strip()
        if card_width >= 72 and time_label not in {"全天", "待定"}:
            return f"{time_label} {title[:6]}".strip()
        return title[:8] if len(title) > 8 else title

    def _week_preview_lines(self, deadline: Dict[str, Any], card_width: int) -> tuple[str, str]:
        """返回周视图中每条事项的主、副两行文案。"""
        title = str(deadline.get("title", "")).strip() or "未命名事项"
        time_label = self._time_label(deadline)
        countdown = self._countdown_badge(deadline)
        case_label = self._case_label(deadline, 10 if card_width < 180 else 14)
        deadline_type = str(deadline.get("type", "deadline"))

        if deadline_type == "hearing":
            primary_parts: List[str] = []
            if time_label and time_label not in {"全天", "待定"}:
                primary_parts.append(time_label)
            primary_parts.append("开庭")
            secondary_parts: List[str] = []
            if case_label:
                secondary_parts.append(case_label)
            elif title and title != "开庭安排":
                secondary_parts.append(title)
            if countdown:
                secondary_parts.append(countdown)
            return (
                " · ".join(primary_parts).strip(),
                " · ".join(part for part in secondary_parts if part).strip(),
            )

        primary = title
        secondary_parts = []
        if time_label:
            secondary_parts.append(time_label)
        if case_label:
            secondary_parts.append(case_label)
        if countdown:
            secondary_parts.append(countdown)
        return primary, " · ".join(part for part in secondary_parts if part).strip()

    def _countdown_badge(self, deadline: Dict[str, Any]) -> str:
        """返回期限倒计时标识。"""
        if _deadline_is_completed(deadline):
            return "已完成"

        days_until = _deadline_days_until(deadline)
        if days_until is None:
            return ""
        if days_until < 0:
            return "已逾期"
        if days_until == 0:
            return "今天"
        if days_until <= 7:
            return f"D-{days_until}"
        return ""

    def _preview_capacity(self, card_rect: QRect) -> int:
        """根据日期卡尺寸决定最多展示几条预览。"""
        if self._view_mode == "week":
            base_top = 54
            line_height = 34
            line_gap = 8
            footer_height = 28
            available = card_rect.height() - base_top - 12
            if available < line_height:
                return 0
            capacity = 1
            remaining = available - line_height
            while remaining >= (line_height + line_gap):
                capacity += 1
                remaining -= (line_height + line_gap)
            reserve = 1 if remaining < footer_height else 0
            return min(6, max(2, capacity - reserve))

        ultra_compact = card_rect.width() < 80
        compact_layout = card_rect.width() < 100
        base_top = 28 if ultra_compact else (32 if compact_layout else 38)
        line_height = 14 if ultra_compact else (16 if compact_layout else 18)
        line_gap = 2 if ultra_compact else (3 if compact_layout else 4)
        footer_height = 18
        available = card_rect.height() - base_top - 6
        if available < line_height:
            return 0
        if ultra_compact or (compact_layout and (card_rect.width() <= 84 or card_rect.height() <= 72)):
            return 1
        capacity = 1
        remaining = available - line_height
        while remaining >= (line_height + line_gap):
            capacity += 1
            remaining -= (line_height + line_gap)
        if self._view_mode == "month":
            return min(5, max(1, capacity))
        return min(8, max(2, capacity - (footer_height // max(1, line_height + line_gap))))

    def _show_top_badge(self, card_rect: QRect, visual_state: str, deadline_count: int) -> bool:
        """判断是否显示右上角状态/数量徽标。"""
        if self._view_mode == "week":
            return visual_state in {"overdue", "hearing", "today", "upcoming"} and card_rect.width() >= 140
        if card_rect.width() < 96:
            return False
        return visual_state != "normal" or deadline_count > 1

    def _extra_indicator_text(self, extra_count: int) -> str:
        return f"更多 {extra_count} 项" if extra_count > 0 else ""

    def _get_preview_items_from_list(self, items: List[Dict[str, Any]], max_items: int = 2) -> tuple[List[Dict[str, str]], int]:
        """从给定事项列表中生成预览项及额外数量。"""
        previews: List[Dict[str, Any]] = []
        for item in items[:max_items]:
            previews.append({
                "deadline": item,
                "type": str(item.get("type", "deadline")),
                "text": self._format_deadline_preview(item),
            })
        return previews, max(0, len(items) - max_items)

    def _get_preview_items(self, date_key: str, max_items: int = 2) -> tuple[List[Dict[str, str]], int]:
        """获取某天的预览项及额外数量。"""
        items = self._deadlines.get(date_key, [])
        return self._get_preview_items_from_list(items, max_items=max_items)

    def _paint_week_view(self, painter: QPainter) -> None:
        """绘制律师排期式周视图。"""
        c = COLORS
        self._card_hit_regions = []
        self._preview_hit_regions = []
        painter.fillRect(self.rect(), QColor(c['surface_1']))

        grid = self._week_grid_rect()
        time_width = self.WEEK_TIME_RULER_WIDTH
        header_h = self._header_height()
        column_width = self._week_day_column_width()
        hour_height = self._week_hour_height()
        week_dates = self._week_dates()
        today = datetime.now().date()

        header_font = QFont()
        header_font.setPointSize(10)
        header_font.setWeight(QFont.Weight.DemiBold)
        meta_font = QFont()
        meta_font.setPointSize(8)

        painter.setPen(QPen(QColor(c['border']), 1))
        painter.drawLine(time_width, header_h, self.width() - 8, header_h)

        for index, week_day in enumerate(week_dates):
            col_left = int(grid.left() + index * column_width)
            day_header_rect = QRect(col_left, 0, int(column_width), header_h)
            self._card_hit_regions.append((QRect(col_left, header_h, int(column_width), grid.height()), week_day))

            if self._is_selected_date(week_day):
                painter.fillRect(day_header_rect.adjusted(4, 4, -4, -6), QColor(c['accent_subtle']))
            elif week_day == today:
                painter.fillRect(day_header_rect.adjusted(4, 4, -4, -6), QColor("#eff6ff"))

            painter.setPen(QColor(c['text_primary']))
            painter.setFont(header_font)
            weekday_rect = QRect(col_left, 6, int(column_width), 18)
            painter.drawText(
                weekday_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][index],
            )
            painter.setPen(QColor(c['text_muted']))
            painter.setFont(meta_font)
            date_rect = QRect(col_left, 29, int(column_width), 14)
            painter.drawText(
                date_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                f"{week_day.month}/{week_day.day}",
            )

            painter.setPen(QPen(QColor(c['border']), 1))
            painter.drawLine(col_left, header_h, col_left, self.height() - 4)

        painter.drawLine(grid.right(), header_h, grid.right(), self.height() - 4)

        for hour in range(self.WEEK_START_HOUR, self.WEEK_END_HOUR + 1):
            y = self._week_minutes_to_y(hour * 60)
            line_color = QColor(c['border'])
            painter.setPen(QPen(line_color, 1))
            painter.drawLine(time_width, y, self.width() - 8, y)
            if hour < self.WEEK_END_HOUR:
                half_y = self._week_minutes_to_y(hour * 60 + 30)
                painter.setPen(QPen(QColor("#edf2f7"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(time_width, half_y, self.width() - 8, half_y)

            if hour < self.WEEK_END_HOUR:
                label_rect = QRect(0, y - 8, time_width - 8, 16)
                painter.setPen(QColor(c['text_muted']))
                painter.setFont(meta_font)
                painter.drawText(
                    label_rect,
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    f"{hour:02d}:00",
                )

        for day_offset, week_day in enumerate(week_dates):
            col_left = int(grid.left() + day_offset * column_width)
            day_rect = QRect(col_left, header_h, int(column_width), grid.height())
            if self._is_selected_date(week_day):
                painter.fillRect(day_rect.adjusted(1, 0, -1, -1), QColor("#f8fbff"))
            elif week_day == today:
                painter.fillRect(day_rect.adjusted(1, 0, -1, -1), QColor("#fbfdff"))

            day_items = list(self._deadlines.get(week_day.strftime("%Y-%m-%d"), []))
            day_items.sort(key=lambda item: (self._week_minutes_for_deadline(item), self._deadline_sort_key(item)))
            for deadline in day_items:
                rect = self._week_deadline_rect(deadline)
                if rect is None:
                    continue
                visual_style = self._deadline_visual_style(deadline)
                base_color = QColor(visual_style["indicator_color"])
                bg = QColor(base_color)
                bg.setAlpha(46 if str(deadline.get("type", "deadline")) == "hearing" else 30)
                if visual_style["state"] == "overdue":
                    bg = QColor("#f3f4f6")
                elif visual_style["state"] == "completed":
                    bg = QColor("#e2e8f0")

                painter.setPen(QPen(base_color if visual_style["state"] != "overdue" else QColor("#cbd5e1"), 1))
                painter.setBrush(QBrush(bg))
                painter.drawRoundedRect(rect, 10, 10)

                accent_rect = QRect(rect.left() + 3, rect.top() + 3, 4, rect.height() - 6)
                painter.fillRect(accent_rect, base_color)

                primary_text, secondary_text = self._week_preview_lines(deadline, rect.width())
                primary_font = QFont()
                primary_font.setPointSize(9)
                primary_font.setWeight(QFont.Weight.DemiBold)
                primary_font.setStrikeOut(bool(visual_style["strike_out"]))
                secondary_font = QFont()
                secondary_font.setPointSize(8)
                secondary_font.setStrikeOut(bool(visual_style["strike_out"]))

                primary_rect = QRect(rect.left() + 12, rect.top() + 5, rect.width() - 18, 16)
                secondary_rect = QRect(rect.left() + 12, rect.top() + 20, rect.width() - 18, 14)

                painter.setFont(primary_font)
                primary_metrics = QFontMetrics(primary_font)
                primary_draw = primary_metrics.elidedText(primary_text, Qt.TextElideMode.ElideRight, primary_rect.width())
                painter.setPen(QColor(visual_style["text_color"]))
                painter.drawText(primary_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, primary_draw)

                if secondary_text:
                    secondary_color = QColor(c['text_muted']) if visual_style["state"] == "normal" else QColor(visual_style["text_color"])
                    painter.setFont(secondary_font)
                    secondary_metrics = QFontMetrics(secondary_font)
                    secondary_draw = secondary_metrics.elidedText(
                        secondary_text, Qt.TextElideMode.ElideRight, secondary_rect.width()
                    )
                    painter.setPen(secondary_color)
                    painter.drawText(
                        secondary_rect,
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        secondary_draw,
                    )

                self._preview_hit_regions.append((QRect(rect), deadline))

        if self._drag_deadline and self._drag_hover_date and self._drag_hover_minutes is not None:
            preview_deadline = dict(self._drag_deadline)
            preview_deadline["date"] = self._drag_hover_date.strftime("%Y-%m-%d")
            preview_deadline["time"] = self._week_minutes_to_time_text(self._drag_hover_minutes)
            preview_deadline["all_day"] = False
            preview_rect = self._week_deadline_rect(preview_deadline)
            if preview_rect is not None:
                painter.setPen(QPen(QColor(c['accent']), 2, Qt.PenStyle.DashLine))
                painter.setBrush(QBrush(QColor(c['accent_subtle'])))
                painter.drawRoundedRect(preview_rect, 10, 10)
                painter.setFont(meta_font)
                painter.setPen(QColor(c['accent']))
                painter.drawText(
                    preview_rect.adjusted(12, 0, -8, 0),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    preview_deadline["time"],
                )

    def paintEvent(self, event) -> None:
        """绘制日历"""
        painter = QPainter(self)
        try:
            self._card_hit_regions = []
            self._preview_hit_regions = []
            self._more_hit_regions = []
            self._expanded_card_region = None
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            if self._view_mode == "week":
                self._paint_week_view(painter)
                return
            w = self.width()
            h = self.height()
            c = COLORS

            painter.fillRect(self.rect(), QColor(c['surface_1']))

            cell_w = w / 7
            header_h = self._header_height()
            cell_h = (h - header_h) / self._row_count()

            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            font = QFont()
            font.setPointSize(9 if self._view_mode == "week" else 10)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            painter.setPen(QColor(c['text_muted']))
            header_dates = self._week_dates() if self._view_mode == "week" else []
            for i, weekday_name in enumerate(weekdays):
                if self._view_mode == "week":
                    header_text = f"{weekday_name}\n{header_dates[i].month}/{header_dates[i].day}"
                else:
                    header_text = weekday_name[-1]
                x = int(i * cell_w)
                if i == 6:
                    width = max(1, w - x)
                else:
                    width = max(1, int(cell_w))
                rect = QRect(x, 2, width, header_h - 6)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, header_text)

            painter.setPen(QPen(QColor(c['border']), 1))
            painter.drawLine(8, header_h, w - 8, header_h)

            today = datetime.now().date()
            day_font = QFont()
            # 根据可用宽度动态调整日期数字字体
            day_font.setPointSize(10 if w >= 560 else 9)
            preview_font = QFont()
            preview_font.setPointSize(8 if w >= 480 else 7)
            preview_meta_font = QFont()
            preview_meta_font.setPointSize(7 if w >= 480 else 6)
            preview_meta_font.setWeight(QFont.Weight.Medium)

            if self._view_mode == "week":
                visible_cells = [(0, col, self._week_start + timedelta(days=col)) for col in range(7)]
            else:
                visible_cells = []
                for row in range(self._row_count()):
                    for col in range(7):
                        day = row * 7 + col - self._first_day_weekday + 1
                        if day < 1 or day > self._days_in_month:
                            continue
                        visible_cells.append((row, col, date(self._year, self._month, day)))
                if self._expanded_more_date is not None:
                    visible_cells = sorted(
                        visible_cells,
                        key=lambda cell: cell[2] == self._expanded_more_date,
                    )

            for row, col, d in visible_cells:
                    is_today = d == today
                    is_selected = self._is_selected_date(d)
                    date_key = d.strftime("%Y-%m-%d")
                    deadlines = self._deadlines.get(date_key, [])
                    render_deadlines = self._month_render_deadlines(d, deadlines)
                    card_rect = self._card_rect(row, col)
                    visual_state, badge_text = self._day_visual_state(d, render_deadlines)
                    ultra_compact = card_rect.width() < 80 and self._view_mode == "month"
                    compact_layout = card_rect.width() < 100 and self._view_mode == "month"
                    day_badge_width = 20 if ultra_compact else (24 if compact_layout else (52 if self._view_mode == "week" else 26))
                    badge_top = card_rect.top() + (4 if ultra_compact else 6)
                    day_badge_rect = QRect(card_rect.left() + (4 if ultra_compact else 6), badge_top, day_badge_width, 20 if ultra_compact else 22)
                    if self._view_mode == "week":
                        line_height = 34
                        line_gap = 8
                    else:
                        line_height = 14 if ultra_compact else (16 if compact_layout else 20)
                        line_gap = 2 if ultra_compact else (3 if compact_layout else 6)

                    normal_preview_slots = self._preview_capacity(card_rect)
                    is_expanded_more_card = (
                        self._view_mode == "month"
                        and self._expanded_more_date == d
                        and len(render_deadlines) > normal_preview_slots
                    )
                    if is_expanded_more_card:
                        preview_top_for_height = day_badge_rect.bottom() + (
                            4 if ultra_compact else (6 if compact_layout else 10)
                        )
                        item_count = len(render_deadlines)
                        desired_height = (
                            preview_top_for_height
                            - card_rect.top()
                            + item_count * line_height
                            + max(0, item_count - 1) * line_gap
                            + 10
                        )
                        available_height = max(card_rect.height(), self.height() - card_rect.top() - 4)
                        card_rect.setHeight(min(max(card_rect.height(), desired_height), available_height))
                        self._expanded_card_region = QRect(card_rect)
                    self._card_hit_regions.append((QRect(card_rect), d))

                    if is_selected:
                        card_bg = QColor(c['accent_subtle'])
                        card_border = QColor(c['accent'])
                        border_width = 2
                    elif visual_state == "overdue":
                        card_bg = QColor("#f3f4f6")
                        card_border = QColor("#d1d5db")
                        border_width = 1
                    elif visual_state == "hearing":
                        card_bg = QColor("#fff1f2")
                        card_border = QColor("#fca5a5")
                        border_width = 1
                    elif visual_state == "upcoming":
                        card_bg = QColor("#fffbeb")
                        card_border = QColor("#fde68a")
                        border_width = 1
                    elif is_today:
                        card_bg = QColor("#f8fbff")
                        card_border = QColor(c['accent_light'])
                        border_width = 1
                    elif render_deadlines:
                        card_bg = QColor(c['surface_0'])
                        card_border = QColor(c['border'])
                        border_width = 1
                    else:
                        card_bg = QColor(c['surface_0'])
                        card_border = QColor("#edf2f7")
                        border_width = 1

                    painter.setPen(QPen(card_border, border_width))
                    painter.setBrush(QBrush(card_bg))
                    painter.drawRoundedRect(card_rect, self.CARD_RADIUS, self.CARD_RADIUS)
                    if self._view_mode == "month" and self._drag_deadline is not None and self._drag_hover_date == d:
                        painter.setPen(QPen(QColor(c['accent']), 2, Qt.PenStyle.DashLine))
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                        painter.drawRoundedRect(card_rect.adjusted(1, 1, -1, -1), self.CARD_RADIUS, self.CARD_RADIUS)

                    painter.setFont(day_font)
                    if is_selected:
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(QBrush(QColor(c['accent'])))
                        painter.drawRoundedRect(day_badge_rect, 10, 10)
                        painter.setPen(QColor(c['surface_0']))
                    elif is_today:
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.setBrush(QBrush(QColor(c['accent_light'])))
                        painter.drawRoundedRect(day_badge_rect, 10, 10)
                        painter.setPen(QColor(c['accent']))
                    else:
                        painter.setPen(QColor(c['text_primary']))
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                    day_badge_text = f"{d.month}/{d.day}" if self._view_mode == "week" else str(d.day)
                    painter.drawText(day_badge_rect, Qt.AlignmentFlag.AlignCenter, day_badge_text)

                    if render_deadlines:
                        show_top_badge = self._show_top_badge(card_rect, visual_state, len(render_deadlines))
                        if show_top_badge:
                            badge_w = 40 if compact_layout else 48
                            badge_rect = QRect(card_rect.right() - badge_w - 4, badge_top, badge_w, 18)
                            badge_bg = QColor(c['surface_2'])
                            badge_fg = QColor(c['text_secondary'])
                            if visual_state == "overdue":
                                badge_bg = QColor("#e5e7eb")
                                badge_fg = QColor(c['text_tertiary'])
                            elif visual_state == "hearing":
                                badge_bg = QColor("#fee2e2")
                                badge_fg = QColor("#b91c1c")
                            elif visual_state == "upcoming":
                                badge_bg = QColor("#fef3c7")
                                badge_fg = QColor(c['warning'])
                            elif visual_state == "today":
                                badge_bg = QColor(c['accent_light'])
                                badge_fg = QColor(c['accent'])
                            painter.setPen(Qt.PenStyle.NoPen)
                            painter.setBrush(QBrush(badge_bg))
                            painter.drawRoundedRect(badge_rect, 10, 10)
                            painter.setFont(preview_meta_font)
                            painter.setPen(badge_fg)
                            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)
                        elif visual_state != "normal":
                            state_dot_color = QColor(c['accent'])
                            if visual_state == "overdue":
                                state_dot_color = QColor("#9ca3af")
                            elif visual_state == "hearing":
                                state_dot_color = QColor("#dc2626")
                            elif visual_state == "upcoming":
                                state_dot_color = QColor(c['warning'])
                            dot_rect = QRect(card_rect.right() - 14, badge_top + 4, 6, 6)
                            painter.setPen(Qt.PenStyle.NoPen)
                            painter.setBrush(QBrush(state_dot_color))
                            painter.drawEllipse(dot_rect)

                        preview_slots = len(render_deadlines) if is_expanded_more_card else self._preview_capacity(card_rect)
                        preview_items, extra_count = self._get_preview_items_from_list(render_deadlines, max_items=preview_slots)
                        if self._view_mode == "week":
                            line_height = 34
                            line_gap = 8
                        else:
                            line_height = 14 if ultra_compact else (16 if compact_layout else 20)
                            line_gap = 2 if ultra_compact else (3 if compact_layout else 6)
                        preview_top = day_badge_rect.bottom() + (4 if ultra_compact else (6 if compact_layout else 10))

                        for index, item in enumerate(preview_items):
                            line_rect = QRect(
                                card_rect.left() + (4 if ultra_compact else 8),
                                preview_top + index * (line_height + line_gap),
                                card_rect.width() - (8 if ultra_compact else 16),
                                line_height,
                            )
                            visual_style = self._deadline_visual_style(item["deadline"])
                            base_color = QColor(visual_style["indicator_color"])
                            line_bg = QColor(base_color)
                            line_bg.setAlpha(
                                visual_style["background_alpha"] + (10 if is_selected else 0)
                            )

                            painter.setPen(Qt.PenStyle.NoPen)
                            painter.setBrush(QBrush(line_bg))
                            painter.drawRoundedRect(line_rect, 6 if ultra_compact else 8, 6 if ultra_compact else 8)

                            if ultra_compact:
                                text_left_padding = 8
                            elif not compact_layout:
                                bar_rect = QRect(line_rect.left() + 3, line_rect.top() + 3, 3, line_rect.height() - 6)
                                painter.setBrush(QBrush(base_color))
                                painter.drawRoundedRect(bar_rect, 2, 2)
                                text_left_padding = 10
                            else:
                                bullet_rect = QRect(line_rect.left() + 5, line_rect.center().y() - 2, 4, 4)
                                painter.setBrush(QBrush(base_color))
                                painter.drawEllipse(bullet_rect)
                                text_left_padding = 10

                            if self._view_mode == "week":
                                primary_text, secondary_text = self._week_preview_lines(
                                    item["deadline"], card_rect.width()
                                )
                                primary_font = QFont(preview_font)
                                primary_font.setPointSize(9)
                                primary_font.setWeight(QFont.Weight.DemiBold)
                                primary_font.setStrikeOut(bool(visual_style["strike_out"]))
                                secondary_font = QFont(preview_meta_font)
                                secondary_font.setPointSize(8)
                                secondary_font.setStrikeOut(bool(visual_style["strike_out"]))

                                primary_rect = QRect(
                                    line_rect.left() + text_left_padding,
                                    line_rect.top() + 3,
                                    line_rect.width() - (text_left_padding + 6),
                                    14,
                                )
                                secondary_rect = QRect(
                                    line_rect.left() + text_left_padding,
                                    line_rect.top() + 16,
                                    line_rect.width() - (text_left_padding + 6),
                                    13,
                                )

                                painter.setFont(primary_font)
                                primary_metrics = QFontMetrics(primary_font)
                                primary_draw = primary_metrics.elidedText(
                                    primary_text,
                                    Qt.TextElideMode.ElideRight,
                                    primary_rect.width(),
                                )
                                painter.setPen(QColor(visual_style["text_color"]))
                                painter.drawText(
                                    primary_rect,
                                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                    primary_draw,
                                )

                                if secondary_text:
                                    secondary_color = QColor(visual_style["text_color"])
                                    if visual_style["state"] == "normal":
                                        secondary_color = QColor(COLORS['text_muted'])
                                    elif visual_style["state"] == "hearing":
                                        secondary_color = QColor("#b91c1c")
                                    painter.setFont(secondary_font)
                                    secondary_metrics = QFontMetrics(secondary_font)
                                    secondary_draw = secondary_metrics.elidedText(
                                        secondary_text,
                                        Qt.TextElideMode.ElideRight,
                                        secondary_rect.width(),
                                    )
                                    painter.setPen(secondary_color)
                                    painter.drawText(
                                        secondary_rect,
                                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                                        secondary_draw,
                                    )
                            else:
                                draw_font = QFont(preview_font)
                                draw_font.setStrikeOut(bool(visual_style["strike_out"]))
                                painter.setFont(draw_font)
                                metrics = QFontMetrics(draw_font)
                                preview_text = metrics.elidedText(
                                    self._format_compact_deadline_preview(item["deadline"], card_rect.width()),
                                    Qt.TextElideMode.ElideRight,
                                    line_rect.width() - (text_left_padding + 6),
                                )
                                painter.setPen(QColor(visual_style["text_color"]))
                                painter.drawText(
                                    line_rect.adjusted(text_left_padding, 0, -6, 0),
                                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                                    preview_text,
                                )
                            if item.get("deadline"):
                                self._preview_hit_regions.append((QRect(line_rect), item["deadline"]))

                        if extra_count > 0:
                            indicator_text = self._extra_indicator_text(extra_count)
                            more_rect = QRect(card_rect.left() + 8, card_rect.bottom() - 24, card_rect.width() - 16, 16)
                            painter.setPen(Qt.PenStyle.NoPen)
                            painter.setBrush(QBrush(QColor(c['surface_2'])))
                            painter.drawRoundedRect(more_rect, 8, 8)
                            painter.setFont(preview_meta_font)
                            painter.setPen(QColor(c['text_muted']))
                            painter.drawText(more_rect, Qt.AlignmentFlag.AlignCenter, indicator_text)
                            self._more_hit_regions.append((QRect(more_rect), d))
        except Exception as exc:
            self._logger.error(f"绘制期限日历失败: {exc}")
        finally:
            if painter.isActive():
                painter.end()

    def mousePressEvent(self, event) -> None:
        """鼠标点击选择日期"""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        point = event.position().toPoint()
        for rect, day_value in reversed(self._more_hit_regions):
            if rect.contains(point):
                self._expanded_more_date = day_value
                self.set_selected_date(day_value)
                if self.date_clicked:
                    self.date_clicked(day_value)
                self.update()
                return

        deadline = self._deadline_at_pos(point)
        if deadline is not None:
            self._drag_candidate = deadline
            self._drag_start_point = point
            if self._view_mode == "week":
                rect = self._week_deadline_rect(deadline)
                self._drag_offset_y = point.y() - rect.top() if rect is not None else 0
            else:
                self._drag_offset_y = 0
            deadline_day = _deadline_date_value(deadline)
            if deadline_day is not None:
                self.set_selected_date(deadline_day)
                if self.date_clicked:
                    self.date_clicked(deadline_day)
            return

        d = self._date_at_pos(point.x(), point.y())
        if d:
            self.set_selected_date(d)
            if self.date_clicked:
                self.date_clicked(d)

    def mouseMoveEvent(self, event) -> None:
        point = event.position().toPoint()
        if (
            self._expanded_more_date is not None
            and self._expanded_card_region is not None
            and not self._expanded_card_region.contains(point)
        ):
            self._expanded_more_date = None
            self._expanded_card_region = None
            self.update()

        if any(rect.contains(point) for rect, _ in self._more_hit_regions):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

        if self._drag_candidate and self._drag_start_point and self._drag_deadline is None:
            if (point - self._drag_start_point).manhattanLength() >= 6:
                self._drag_deadline = self._drag_candidate

        if self._drag_deadline is None:
            return super().mouseMoveEvent(event)

        if self._view_mode == "week":
            hover_date = self._week_day_at_x(point.x())
            if hover_date is None:
                hover_date = self._drag_hover_date or _deadline_date_value(self._drag_deadline)

            drop_y = point.y() - self._drag_offset_y + 14
            self._drag_hover_date = hover_date
            self._drag_hover_minutes = self._week_y_to_minutes(drop_y)
        else:
            self._drag_hover_date = self._date_at_pos(point.x(), point.y())
            self._drag_hover_minutes = None
        self.update()

    def leaveEvent(self, event) -> None:
        if self._expanded_more_date is not None:
            self._expanded_more_date = None
            self._expanded_card_region = None
            self.update()
        self.unsetCursor()
        return super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)

        if self._drag_deadline is not None:
            if self._view_mode == "week":
                if self._deadline_drag_callback and self._drag_hover_date and self._drag_hover_minutes is not None:
                    self._deadline_drag_callback(
                        self._drag_deadline,
                        self._drag_hover_date,
                        self._week_minutes_to_time_text(self._drag_hover_minutes),
                    )
            else:
                if self._deadline_drag_callback and self._drag_hover_date:
                    self._deadline_drag_callback(
                        self._drag_deadline,
                        self._drag_hover_date,
                        None,
                    )
            self._reset_drag_state()
            self.update()
            return

        self._reset_drag_state()
        return super().mouseReleaseEvent(event)

    def _reset_drag_state(self) -> None:
        self._drag_candidate = None
        self._drag_deadline = None
        self._drag_start_point = None
        self._drag_hover_date = None
        self._drag_hover_minutes = None

    def mouseDoubleClickEvent(self, event) -> None:
        """双击支持：双击事项编辑，双击空白日期卡新增。"""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        point = event.position().toPoint()
        for rect, deadline in self._preview_hit_regions:
            if rect.contains(point):
                deadline_date = deadline.get("date", "")
                try:
                    clicked_date = datetime.strptime(deadline_date, "%Y-%m-%d").date()
                    self.set_selected_date(clicked_date)
                    if self.date_clicked:
                        self.date_clicked(clicked_date)
                except ValueError:
                    pass
                if self.deadline_double_clicked:
                    self.deadline_double_clicked(deadline)
                return

        if self._view_mode == "week":
            day_value = self._date_at_pos(point.x(), point.y())
            if day_value:
                self.set_selected_date(day_value)
                if self.date_clicked:
                    self.date_clicked(day_value)
                if self.date_double_clicked:
                    self.date_double_clicked(day_value, self._week_minutes_to_time_text(self._week_y_to_minutes(point.y())))
                return

        for rect, day_value in self._card_hit_regions:
            if rect.contains(point):
                self.set_selected_date(day_value)
                if self.date_clicked:
                    self.date_clicked(day_value)
                if self.date_double_clicked:
                    self.date_double_clicked(day_value)
                return


class _ActionButton(QFrame):
    """自定义按钮：基于 QFrame 实现，完全绕过 QPushButton 的 macOS 原生绘制问题。"""

    clicked = Signal()

    def __init__(self, text: str, accent: bool = False, width: int = 40, height: int = 22, parent=None):
        super().__init__(parent)
        self._text = text
        self._accent = accent
        self._enabled = True
        self._hover = False
        self._pressed = False
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(label)

        self._update_style()

    def _update_style(self):
        c = COLORS
        bg = c['accent_subtle'] if self._accent else c['surface_1']
        fg = c['accent'] if self._accent else c['text_secondary']
        border = c['border']
        w, h = self.width(), self.height()
        is_square = abs(w - h) <= 4
        radius = 10 if is_square else 6
        font_size = 14 if is_square else 10

        if not self._enabled:
            fg = c['text_muted']
            border = c['surface_3']
        elif self._pressed:
            bg = c['accent_light'] if self._accent else c.get('surface_3', c['surface_2'])
            fg = c['accent'] if self._accent else c['text_primary']
            border = c['border_strong']
        elif self._hover:
            bg = c['accent_light'] if self._accent else c['surface_2']
            fg = c['accent'] if self._accent else c['text_primary']
            border = c['border_strong']

        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1px solid {border};
                border-radius: {radius}px;
            }}
            QLabel {{
                background: transparent;
                color: {fg};
                font-size: {font_size}px;
                font-weight: 600;
            }}
        """)

    def setEnabled(self, enabled: bool):
        self._enabled = enabled
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self._update_style()

    def enterEvent(self, event):
        if self._enabled:
            self._hover = True
            self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._enabled:
            self._pressed = True
            self._update_style()
            self.clicked.emit()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self._update_style()
        super().mouseReleaseEvent(event)


class DeadlineDetailRow(QFrame):
    """右侧当天事项卡片，支持编辑、完成/恢复、删除。"""

    def __init__(
        self,
        deadline: Dict[str, Any],
        edit_callback,
        toggle_callback,
        remove_callback,
        open_case_callback=None,
        postpone_callback=None,
        parent=None,
        show_date: bool = False,
        expanded: bool = True,
    ):
        super().__init__(parent)
        self._deadline = deadline
        self._edit_callback = edit_callback
        self._toggle_callback = toggle_callback
        self._remove_callback = remove_callback
        self._open_case_callback = open_case_callback
        self._postpone_callback = postpone_callback
        self._show_date = show_date
        self._expanded = expanded
        self._setup_ui()

    def _setup_ui(self) -> None:
        c = COLORS
        dl_type = self._deadline.get("type", "deadline")
        color_map = {
            "deadline": c['warning'],
            "hearing": "#dc2626",
            "custom": c['warning'],
        }
        visual_state = "normal"
        if _deadline_is_completed(self._deadline):
            visual_state = "completed"
        elif _deadline_is_overdue(self._deadline):
            visual_state = "overdue"

        dot_color = color_map.get(dl_type, c['danger'])
        card_bg = c['surface_0']
        card_border = c['border']
        title_color = c['text_primary']
        meta_color = c['text_muted']
        desc_color = c['text_secondary']
        if visual_state == "completed":
            dot_color = c['text_muted']
            card_bg = c['surface_1']
            card_border = c['surface_3']
            title_color = c['text_muted']
            meta_color = c['text_muted']
            desc_color = c['text_tertiary']
        elif visual_state == "overdue":
            dot_color = "#9ca3af"
            card_bg = "#f3f4f6"
            card_border = "#d1d5db"
            title_color = c['text_secondary']
            meta_color = c['text_tertiary']
            desc_color = c['text_tertiary']
        elif str(dl_type) == "hearing":
            card_bg = "#fff7f7"
            card_border = "#fecaca"
            title_color = "#7f1d1d"
            meta_color = "#b91c1c"

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("calendarDeadlineCard", True)
        self.setStyleSheet(f"""
            QFrame[calendarDeadlineCard="true"] {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 10px;
            }}
        """)

        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(12, 12, 12, 12)
        row_layout.setSpacing(10)

        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet(f"""
            background-color: {dot_color};
            border: none;
            border-radius: 2px;
        """)
        row_layout.addWidget(accent)

        body = QVBoxLayout()
        body.setSpacing(6)

        self._title_full_text = str(self._deadline.get("title", "未命名"))
        self._title_label = QLabel(self._title_full_text)
        self._title_label.setStyleSheet(f"""
            background: transparent;
            color: {title_color};
            font-size: 14px;
            font-weight: 600;
        """)
        self._title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        body.addWidget(self._title_label)

        meta_parts = []
        if self._show_date:
            deadline_date = str(self._deadline.get("date", "")).strip()
            if deadline_date:
                meta_parts.append(deadline_date)
        countdown_text = self._countdown_text()
        if countdown_text:
            meta_parts.append(countdown_text)
        time_label = str(self._deadline.get("time", "")).strip()
        if self._deadline.get("all_day", not time_label):
            meta_parts.append("全天")
        elif time_label:
            meta_parts.append(time_label[:5])
        case_name = str(self._deadline.get("case_name", "")).strip()
        if case_name:
            meta_parts.append(case_name)
        self._meta_full_text = " · ".join(meta_parts) if meta_parts else "未填写说明"
        self._meta_label = QLabel(self._meta_full_text)
        self._meta_label.setWordWrap(True)
        self._meta_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._meta_label.setStyleSheet(f"""
            background: transparent;
            color: {meta_color};
            font-size: 12px;
        """)
        body.addWidget(self._meta_label)

        self._chips_widget = QWidget()
        chips_row = QHBoxLayout(self._chips_widget)
        chips_row.setSpacing(6)
        chips_row.setContentsMargins(0, 0, 0, 0)
        chips_row.addWidget(self._create_chip(self._type_text(), dot_color, filled=True))

        priority_text = self._priority_text()
        if priority_text:
            chips_row.addWidget(self._create_chip(priority_text, c['text_secondary']))

        remind_text = self._remind_text()
        if remind_text:
            chips_row.addWidget(self._create_chip(remind_text, c['text_muted']))

        for tag in self._case_tags()[:3]:
            chips_row.addWidget(self._create_chip(f"#{tag}", c['accent']))

        extra_tags = len(self._case_tags()) - 3
        if extra_tags > 0:
            chips_row.addWidget(self._create_chip(f"+{extra_tags}", c['text_muted']))

        chips_row.addStretch()
        body.addWidget(self._chips_widget)

        description = str(self._deadline.get("description", "")).strip()
        self._desc_label: Optional[QLabel] = None
        if description:
            self._desc_label = QLabel(description)
            self._desc_label.setWordWrap(True)
            self._desc_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._desc_label.setStyleSheet(f"""
                background: transparent;
                color: {desc_color};
                font-size: 12px;
            """)
            body.addWidget(self._desc_label)

        if visual_state == "completed":
            self._apply_strikeout(self._title_label)
            self._apply_strikeout(self._meta_label)
            if self._desc_label is not None:
                self._apply_strikeout(self._desc_label)

        self._action_widget = QWidget()
        action_row = QHBoxLayout(self._action_widget)
        action_row.setSpacing(4)
        action_row.setContentsMargins(0, 0, 0, 0)

        status = str(self._deadline.get("status", "pending"))
        case_btn = self._create_action_button("案件")
        case_btn.clicked.connect(self._on_open_case)
        case_btn.setEnabled(bool(str(self._deadline.get("case_id", "")).strip()))
        action_row.addWidget(case_btn)

        edit_btn = self._create_action_button("编辑", accent=True)
        edit_btn.clicked.connect(self._on_edit)
        action_row.addWidget(edit_btn)

        toggle_btn = self._create_action_button("恢复" if status == "completed" else "完成")
        toggle_btn.clicked.connect(self._on_toggle)
        action_row.addWidget(toggle_btn)

        if status != "completed":
            postpone_btn = self._create_action_button("顺延")
            postpone_btn.clicked.connect(self._on_postpone)
            action_row.addWidget(postpone_btn)

        del_btn = self._create_action_button("删除")
        del_btn.clicked.connect(self._on_remove)
        action_row.addWidget(del_btn)
        action_row.addStretch()

        body.addWidget(self._action_widget)
        row_layout.addLayout(body, 1)
        self._apply_expanded_state()

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._apply_expanded_state()

    def is_expanded(self) -> bool:
        return self._expanded

    @staticmethod
    def _apply_strikeout(label: QLabel) -> None:
        """为标签应用删除线。"""
        font = QFont(label.font())
        font.setStrikeOut(True)
        label.setFont(font)

    def _apply_expanded_state(self) -> None:
        title_metrics = QFontMetrics(self._title_label.font())
        meta_metrics = QFontMetrics(self._meta_label.font())
        if self._expanded:
            self._title_label.setWordWrap(True)
            self._meta_label.setWordWrap(True)
            self._title_label.setText(self._title_full_text)
            self._meta_label.setText(self._meta_full_text)
            self._title_label.setMaximumHeight(16777215)
            self._meta_label.setMaximumHeight(16777215)
            self._chips_widget.setVisible(True)
            if self._desc_label is not None:
                self._desc_label.setVisible(True)
                self._desc_label.setMaximumHeight(16777215)
            return

        self._title_label.setWordWrap(False)
        self._meta_label.setWordWrap(False)
        self._title_label.setMaximumHeight(title_metrics.lineSpacing() + 4)
        self._meta_label.setMaximumHeight(meta_metrics.lineSpacing() + 4)
        self._chips_widget.setVisible(False)
        if self._desc_label is not None:
            self._desc_label.setVisible(False)
            self._desc_label.setMaximumHeight(0)
        self._refresh_compact_texts()

    def _refresh_compact_texts(self) -> None:
        if self._expanded:
            return
        self._title_label.setText(self._elided_label_text(self._title_label, self._title_full_text))
        self._meta_label.setText(self._elided_label_text(self._meta_label, self._meta_full_text))

    @staticmethod
    def _elided_label_text(label: QLabel, text: str) -> str:
        metrics = QFontMetrics(label.font())
        width = label.width()
        if width <= 0 and label.parentWidget() is not None:
            width = label.parentWidget().width()
        if width <= 0:
            return text
        return metrics.elidedText(text, Qt.TextElideMode.ElideRight, max(48, width - 2))

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._refresh_compact_texts()

    def _create_action_button(self, text: str, accent: bool = False) -> '_ActionButton':
        return _ActionButton(text, accent=accent)

    def _create_chip(self, text: str, color: str, filled: bool = False) -> QLabel:
        c = COLORS
        label = QLabel(text)
        background = "transparent"
        border = color
        text_color = color
        if filled:
            background = color
            border = color
            text_color = c['surface_0']
        label.setStyleSheet(
            f"""
            background: {background};
            color: {text_color};
            border: 1px solid {border};
            border-radius: 9px;
            padding: 1px 8px;
            font-size: 11px;
            font-weight: 600;
        """
        )
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        return label

    def _type_text(self) -> str:
        return {
            "deadline": "期限",
            "hearing": "开庭",
            "custom": "提醒",
        }.get(str(self._deadline.get("type", "deadline")), "事项")

    def _priority_text(self) -> str:
        return {
            "high": "高优先",
            "medium": "中优先",
            "low": "低优先",
        }.get(str(self._deadline.get("priority", "medium")), "")

    def _remind_text(self) -> str:
        remind_before = self._deadline.get("remind_before", [])
        if isinstance(remind_before, list) and remind_before:
            return "提前 " + "/".join(str(item) for item in remind_before) + " 天"
        return ""

    def _case_tags(self) -> List[str]:
        return _normalize_tag_list(self._deadline.get("case_tags", []))

    def _countdown_text(self) -> str:
        if _deadline_is_completed(self._deadline):
            return "已完成"
        if _deadline_is_overdue(self._deadline):
            return "已逾期"
        days_until = _deadline_days_until(self._deadline)
        if days_until is None:
            return ""
        if days_until == 0:
            return "今天处理"
        if 0 < days_until <= 7:
            return f"D-{days_until}"
        return ""

    def _on_edit(self) -> None:
        if self._edit_callback:
            self._edit_callback(self._deadline)

    def _on_toggle(self) -> None:
        if self._toggle_callback:
            self._toggle_callback(self._deadline)

    def _on_remove(self) -> None:
        if self._remove_callback:
            self._remove_callback(self._deadline)

    def _on_open_case(self) -> None:
        if self._open_case_callback:
            self._open_case_callback(self._deadline)

    def _on_postpone(self) -> None:
        if self._postpone_callback:
            self._postpone_callback(self._deadline)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._edit_callback:
            self._edit_callback(self._deadline)
        super().mouseDoubleClickEvent(event)


class CalendarDialog(QDialog):
    """期限日历对话框

    布局：
    ┌──────────────────────────────────────────────────────────┐
    │  期限日历                                   [_] [X]     │
    ├──────────────────────────────────────────────────────────┤
    │  [◀] 2026年 4月 [▶]  [今天]  [+期限]  [+开庭]          │
    ├──────────────────────────────────────────────────────────┤
    │  ┌──────────────────┐  ┌────────────────────────────┐   │
    │  │    日历控件        │  │ 4月15日 (周二)              │   │
    │  │  (日期卡片预览)    │  │ ┌────────────────────────┐ │   │
    │  │                   │  │ │ 🔴 举证期限             │ │   │
    │  │                   │  │ │    张三_合同纠纷        │ │   │
    │  │                   │  │ └────────────────────────┘ │   │
    │  └──────────────────┘  └────────────────────────────┘   │
    └──────────────────────────────────────────────────────────┘
    """

    navigate_to_deadline_requested = Signal(str, str)

    def __init__(self, parent=None, embed_mode: bool = False):
        super().__init__(parent)
        self._embed_mode = embed_mode
        if embed_mode:
            self.setWindowFlags(Qt.Widget)
        self._logger = __import__('src.utils.logger', fromlist=['get_logger']).get_logger()
        self._cm = get_case_manager()
        today = datetime.now().date()
        self._current_year = today.year
        self._current_month = today.month
        self._current_week_start = today - timedelta(days=today.weekday())
        self._calendar_view_mode = "month"
        self._detail_mode = "day"
        self._risk_filter = "none"
        self._detail_rows_expanded = True
        self._all_deadlines_cache: List[Dict[str, Any]] = []
        self._setup_ui()
        self._load_deadlines()
        self._calendar.set_selected_date(today)
        self._refresh_detail_panel()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._load_deadlines()

    def _setup_ui(self) -> None:
        """设置界面"""
        c = COLORS
        today = datetime.now().date()

        if not self._embed_mode:
            self.setWindowTitle("期限日历")
            self.setMinimumSize(*APP_SURFACE_MIN_SIZE)
            self.resize(*APP_SURFACE_DEFAULT_SIZE)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['surface_0']};
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 6, 12, 10)
        main_layout.setSpacing(6)

        # ── 顶部导航栏 ──
        nav = QHBoxLayout()
        nav.setSpacing(6)

        prev_btn = _ActionButton("◀", width=36, height=36)
        prev_btn.clicked.connect(self._on_prev_month)
        nav.addWidget(prev_btn)

        self._month_label = QLabel(f"{self._current_year}年 {self._current_month}月")
        self._month_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 16px;
            font-weight: 600;
        """)
        nav.addWidget(self._month_label)

        next_btn = _ActionButton("▶", width=36, height=36)
        next_btn.clicked.connect(self._on_next_month)
        nav.addWidget(next_btn)

        nav.addSpacing(8)

        self._month_view_btn = QPushButton("月视图")
        self._month_view_btn.setFixedHeight(26)
        self._month_view_btn.clicked.connect(lambda: self._set_calendar_view_mode("month"))
        nav.addWidget(self._month_view_btn)

        self._week_view_btn = QPushButton("周视图")
        self._week_view_btn.setFixedHeight(26)
        self._week_view_btn.clicked.connect(lambda: self._set_calendar_view_mode("week"))
        nav.addWidget(self._week_view_btn)

        today_btn = QPushButton("今天")
        today_btn.setFixedHeight(28)
        today_btn.setStyleSheet(self._action_btn_style(c))
        today_btn.clicked.connect(self._on_today)
        nav.addWidget(today_btn)

        tool_center_btn = QPushButton("工具中心")
        tool_center_btn.setFixedHeight(28)
        tool_center_btn.setStyleSheet(self._action_btn_style(c))
        tool_center_btn.clicked.connect(self._on_tool_center)
        nav.addWidget(tool_center_btn)

        self._btn_case_manager = QPushButton("案件管理")
        self._btn_case_manager.setFixedHeight(28)
        self._btn_case_manager.setStyleSheet(self._action_btn_style(c))
        self._btn_case_manager.clicked.connect(self._on_case_manager)
        nav.addWidget(self._btn_case_manager)

        nav.addStretch()

        # 快捷新增按钮合并到导航栏右侧
        for text, key in [
            ("+期限", "add_deadline"),
            ("+开庭", "add_hearing"),
            ("+举证", "evidence"),
            ("+答辩", "defense"),
            ("+上诉", "appeal"),
            ("+缴费", "payment"),
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(24)
            btn.setStyleSheet(self._compact_action_btn_style(c))
            btn.clicked.connect(lambda checked=False, template_key=key: self._on_quick_add_template(template_key))
            nav.addWidget(btn)
        main_layout.addLayout(nav)

        # ── 顶部概览统计 ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stats_value_labels: Dict[str, QLabel] = {}
        self._stats_hint_labels: Dict[str, QLabel] = {}
        stat_defs = [
            ("today", "今日待办", "当天需要处理的事项"),
            ("week", "近7天", "未来一周内的安排"),
            ("overdue", "已逾期", "尚未完成且已过期"),
            ("hearing", "待开庭", "当前未完成开庭事项"),
        ]
        for key, title, hint in stat_defs:
            card = QFrame()
            card.setProperty("summaryStatCard", True)
            card.setStyleSheet(self._summary_card_style(c))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 5, 10, 5)
            card_layout.setSpacing(2)

            title_label = QLabel(title)
            title_label.setStyleSheet(
                f"background: transparent; color: {c['text_muted']}; font-size: 10px; font-weight: 600;"
            )
            card_layout.addWidget(title_label)

            value_label = QLabel("0")
            value_label.setStyleSheet(
                f"background: transparent; color: {c['text_primary']}; font-size: 18px; font-weight: 700;"
            )
            card_layout.addWidget(value_label)
            self._stats_value_labels[key] = value_label

            hint_label = QLabel(hint)
            hint_label.setStyleSheet(
                f"background: transparent; color: {c['text_tertiary']}; font-size: 10px;"
            )
            card_layout.addWidget(hint_label)
            self._stats_hint_labels[key] = hint_label

            stats_row.addWidget(card, 1)

        main_layout.addLayout(stats_row)

        # ── 内容区：日历 + 详情 ──
        content = QHBoxLayout()
        content.setSpacing(10)

        # 日历
        calendar_frame = QFrame()
        calendar_frame.setProperty("calendarSurfaceCard", True)
        calendar_frame.setStyleSheet(f"""
            QFrame[calendarSurfaceCard="true"] {{
                background-color: {c['surface_0']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
        """)
        cal_layout = QVBoxLayout(calendar_frame)
        cal_layout.setContentsMargins(6, 6, 6, 6)
        cal_layout.setSpacing(0)

        self._calendar = DeadlineCalendarWidget()
        self._calendar.set_date_clicked_callback(self._on_date_clicked)
        self._calendar.set_date_double_clicked_callback(self._on_date_double_clicked)
        self._calendar.set_deadline_double_clicked_callback(self._on_deadline_preview_double_clicked)
        self._calendar.set_deadline_drag_callback(self._on_drag_deadline_from_calendar)
        self._calendar.set_month(self._current_year, self._current_month)
        self._calendar.set_view_mode(self._calendar_view_mode, today)
        cal_layout.addWidget(self._calendar)

        content.addWidget(calendar_frame, 8)

        # 右侧详情面板
        detail_frame = QFrame()
        detail_frame.setProperty("calendarSurfaceCard", True)
        detail_frame.setStyleSheet(f"""
            QFrame[calendarSurfaceCard="true"] {{
                background-color: {c['surface_1']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
        """)
        detail_frame.setMinimumWidth(320)
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(6)

        self._detail_title = QLabel("选择日期查看期限")
        self._detail_title.setStyleSheet(f"""
            background: transparent;
            color: {c['text_primary']};
            font-size: 15px;
            font-weight: 600;
        """)
        title_row.addWidget(self._detail_title, 1)

        self._view_day_btn = QPushButton("当天事项")
        self._view_day_btn.setFixedHeight(26)
        self._view_day_btn.clicked.connect(lambda: self._set_detail_mode("day"))
        title_row.addWidget(self._view_day_btn)

        self._view_all_btn = QPushButton("全部事项")
        self._view_all_btn.setFixedHeight(26)
        self._view_all_btn.clicked.connect(lambda: self._set_detail_mode("all"))
        title_row.addWidget(self._view_all_btn)
        detail_layout.addLayout(title_row)

        filter_grid = QGridLayout()
        filter_grid.setSpacing(8)
        filter_grid.setContentsMargins(0, 0, 0, 0)
        filter_grid.setColumnStretch(0, 1)
        filter_grid.setColumnStretch(1, 1)

        self._tag_filter_combo = QComboBox()
        self._tag_filter_combo.setObjectName("calendarFilterCombo")
        self._tag_filter_combo.setMinimumWidth(100)
        self._tag_filter_combo.setStyleSheet(self._filter_combo_style(c))
        self._tag_filter_combo.currentIndexChanged.connect(self._refresh_detail_panel)
        filter_grid.addWidget(self._tag_filter_combo, 0, 0)

        self._case_filter_combo = QComboBox()
        self._case_filter_combo.setObjectName("calendarFilterCombo")
        self._case_filter_combo.setMinimumWidth(100)
        self._case_filter_combo.setStyleSheet(self._filter_combo_style(c))
        self._case_filter_combo.currentIndexChanged.connect(self._refresh_detail_panel)
        filter_grid.addWidget(self._case_filter_combo, 0, 1)

        self._status_filter_combo = QComboBox()
        self._status_filter_combo.setObjectName("calendarFilterCombo")
        self._status_filter_combo.setMinimumWidth(100)
        self._status_filter_combo.setStyleSheet(self._filter_combo_style(c))
        self._status_filter_combo.addItem("全部状态", "all")
        self._status_filter_combo.addItem("仅未完成", "pending")
        self._status_filter_combo.addItem("仅已逾期", "overdue")
        self._status_filter_combo.addItem("仅已完成", "completed")
        self._status_filter_combo.currentIndexChanged.connect(self._refresh_detail_panel)
        filter_grid.addWidget(self._status_filter_combo, 1, 0)

        self._type_filter_combo = QComboBox()
        self._type_filter_combo.setObjectName("calendarFilterCombo")
        self._type_filter_combo.setMinimumWidth(100)
        self._type_filter_combo.setStyleSheet(self._filter_combo_style(c))
        self._type_filter_combo.addItem("全部类型", "all")
        self._type_filter_combo.addItem("仅开庭", "hearing")
        self._type_filter_combo.addItem("仅期限", "deadline")
        self._type_filter_combo.addItem("仅提醒", "custom")
        self._type_filter_combo.currentIndexChanged.connect(self._refresh_detail_panel)
        filter_grid.addWidget(self._type_filter_combo, 1, 1)
        detail_layout.addLayout(filter_grid)

        self._detail_context_label = QLabel("当天事项会按风险高低排序展示。")
        self._detail_context_label.setWordWrap(True)
        self._detail_context_label.setStyleSheet(
            f"background: transparent; color: {c['text_muted']}; font-size: 11px;"
        )
        detail_layout.addWidget(self._detail_context_label)

        queue_row = QHBoxLayout()
        queue_row.setSpacing(6)
        self._queue_buttons: Dict[str, QPushButton] = {}
        queue_defs = [
            ("default", "全部"),
            ("overdue", "逾期"),
            ("next3", "3天"),
            ("hearing_week", "开庭"),
        ]
        for key, text in queue_defs:
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked=False, value=key: self._apply_risk_filter(value))
            self._queue_buttons[key] = btn
            queue_row.addWidget(btn)
        self._detail_expand_toggle_btn = QPushButton("收缩")
        self._detail_expand_toggle_btn.setFixedHeight(26)
        self._detail_expand_toggle_btn.clicked.connect(self._toggle_detail_rows_expanded)
        queue_row.addWidget(self._detail_expand_toggle_btn)
        queue_row.addStretch()
        detail_layout.addLayout(queue_row)

        # 期限列表（滚动区域）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['surface_3']};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self._detail_container = QWidget()
        self._detail_container.setStyleSheet("background: transparent;")
        self._detail_list_layout = QVBoxLayout(self._detail_container)
        self._detail_list_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_list_layout.setSpacing(6)
        self._detail_list_layout.addStretch()

        scroll.setWidget(self._detail_container)
        detail_layout.addWidget(scroll)

        content.addWidget(detail_frame, 3)
        main_layout.addLayout(content)
        self._refresh_mode_buttons()
        self._refresh_calendar_view_buttons()
        self._update_period_label()

    def _nav_btn_style(self, c: dict) -> str:
        return f"""
            QPushButton {{
                background-color: {c['surface_1']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {c['surface_2']};
                color: {c['text_primary']};
            }}
        """

    def _summary_card_style(self, c: dict) -> str:
        return f"""
            QFrame[summaryStatCard="true"] {{
                background-color: {c['surface_1']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
        """

    def _filter_combo_style(self, c: dict) -> str:
        return f"""
            QComboBox#calendarFilterCombo {{
                background-color: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 38px 0 10px;
                min-height: 32px;
                font-size: 12px;
            }}
            QComboBox#calendarFilterCombo:hover {{
                border-color: {c['border_strong']};
            }}
            QComboBox#calendarFilterCombo:focus {{
                border-color: {c['accent']};
            }}
            QComboBox#calendarFilterCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                background: {c['surface_1']};
                border-left: 1px solid {c['border']};
                border-top-right-radius: 9px;
                border-bottom-right-radius: 9px;
                margin: 1px 1px 1px 0;
            }}
            QComboBox#calendarFilterCombo::drop-down:hover {{
                background: {c['surface_2']};
                border-left-color: {c['accent_light']};
            }}
            QComboBox#calendarFilterCombo::down-arrow {{
                image: url({DROPDOWN_ARROW_PATH});
                width: 10px;
                height: 6px;
            }}
        """

    def _refresh_mode_buttons(self) -> None:
        c = COLORS
        active_style = f"""
            QPushButton {{
                background-color: {c['accent_subtle']};
                color: {c['accent']};
                border: 1px solid {c['accent_light']};
                border-radius: 9px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 700;
            }}
        """
        normal_style = f"""
            QPushButton {{
                background-color: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 9px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {c['surface_2']};
                color: {c['text_primary']};
            }}
        """
        self._view_day_btn.setStyleSheet(active_style if self._detail_mode == "day" else normal_style)
        self._view_all_btn.setStyleSheet(active_style if self._detail_mode == "all" else normal_style)
        self._refresh_queue_buttons()

    def _refresh_calendar_view_buttons(self) -> None:
        c = COLORS
        active_style = f"""
            QPushButton {{
                background-color: {c['accent_subtle']};
                color: {c['accent']};
                border: 1px solid {c['accent_light']};
                border-radius: 9px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 700;
            }}
        """
        normal_style = f"""
            QPushButton {{
                background-color: {c['surface_1']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 9px;
                padding: 0 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {c['surface_2']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """
        self._month_view_btn.setStyleSheet(
            active_style if self._calendar_view_mode == "month" else normal_style
        )
        self._week_view_btn.setStyleSheet(
            active_style if self._calendar_view_mode == "week" else normal_style
        )

    def _update_period_label(self) -> None:
        if self._calendar_view_mode == "month":
            self._month_label.setText(f"{self._current_year}年 {self._current_month}月")
            return

        start = self._current_week_start
        end = start + timedelta(days=6)
        if start.year == end.year:
            if start.month == end.month:
                text = f"{start.year}年 {start.month}月 {start.day}日 - {end.day}日"
            else:
                text = f"{start.year}年 {start.month}月 {start.day}日 - {end.month}月 {end.day}日"
        else:
            text = (
                f"{start.year}年 {start.month}月 {start.day}日 - "
                f"{end.year}年 {end.month}月 {end.day}日"
            )
        self._month_label.setText(text)

    def _set_calendar_view_mode(self, mode: str) -> None:
        if mode not in {"month", "week"}:
            return

        anchor = self._calendar.get_selected_date() or datetime.now().date()
        self._calendar_view_mode = mode

        if mode == "month":
            self._current_year = anchor.year
            self._current_month = anchor.month
            self._calendar.set_month(self._current_year, self._current_month)
            self._calendar.set_view_mode("month", anchor)
            self._calendar.set_selected_date(anchor)
        else:
            self._current_week_start = anchor - timedelta(days=anchor.weekday())
            self._current_year = anchor.year
            self._current_month = anchor.month
            self._calendar.set_view_mode("week", anchor)
            self._calendar.set_selected_date(anchor)

        self._refresh_calendar_view_buttons()
        self._update_period_label()
        self._load_deadlines()

    def _refresh_queue_buttons(self) -> None:
        c = COLORS
        active_style = f"""
            QPushButton {{
                background-color: {c['accent_subtle']};
                color: {c['accent']};
                border: 1px solid {c['accent_light']};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 700;
            }}
        """
        normal_style = f"""
            QPushButton {{
                background-color: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {c['surface_2']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """
        for key, button in getattr(self, "_queue_buttons", {}).items():
            active = (key == "default" and self._risk_filter == "none") or key == self._risk_filter
            button.setStyleSheet(active_style if active else normal_style)
        self._detail_expand_toggle_btn.setStyleSheet(normal_style)
        self._detail_expand_toggle_btn.setText("收缩" if self._detail_rows_expanded else "展开")

    def _action_btn_style(self, c: dict) -> str:
        return f"""
            QPushButton {{
                background-color: {c['surface_1']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 10px;
                padding: 0 14px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['surface_2']};
                color: {c['text_primary']};
            }}
        """

    def _compact_action_btn_style(self, c: dict) -> str:
        return f"""
            QPushButton {{
                background-color: {c['surface_1']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {c['surface_2']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
        """

    # ── 数据加载 ──

    def _cases_for_dialog(self) -> List[Dict[str, Any]]:
        return self._cm.get_all_cases()

    def _ensure_cases_available(self) -> List[Dict[str, Any]]:
        cases = self._cases_for_dialog()
        if not cases:
            QMessageBox.information(self, "提示", "请先添加案件")
            return []
        return cases

    def _build_all_deadlines_cache(self) -> List[Dict[str, Any]]:
        """构建带案件标签的期限缓存。"""
        results: List[Dict[str, Any]] = []
        for case in self._cases_for_dialog():
            case_id = str(case.get("id", "")).strip()
            case_name = str(case.get("name", "")).strip()
            case_tags = _normalize_tag_list(case.get("tags", []))
            for deadline in case.get("deadlines", []):
                results.append({
                    **deadline,
                    "case_id": case_id,
                    "case_name": case_name,
                    "case_tags": case_tags,
                })
        for deadline in self._cm.get_global_deadlines():
            results.append({
                **deadline,
                "case_id": "",
                "case_name": "未关联案件",
                "case_tags": [],
            })
        results.sort(key=self._detail_sort_key)
        return results

    def _available_case_tags(self) -> List[str]:
        tags = set()
        for item in self._all_deadlines_cache:
            for tag in _normalize_tag_list(item.get("case_tags", [])):
                tags.add(tag)
        return sorted(tags)

    def _refresh_tag_filter_options(self) -> None:
        selected = str(self._tag_filter_combo.currentData() or "").strip()
        self._tag_filter_combo.blockSignals(True)
        self._tag_filter_combo.clear()
        self._tag_filter_combo.addItem("全部标签", "")
        for tag in self._available_case_tags():
            self._tag_filter_combo.addItem(f"标签：{tag}", tag)
        index = self._tag_filter_combo.findData(selected)
        self._tag_filter_combo.setCurrentIndex(index if index >= 0 else 0)
        self._tag_filter_combo.blockSignals(False)

    def _refresh_case_filter_options(self) -> None:
        selected = str(self._case_filter_combo.currentData() or "").strip()
        self._case_filter_combo.blockSignals(True)
        self._case_filter_combo.clear()
        self._case_filter_combo.addItem("全部案件", "")
        has_unassigned = False
        seen = set()
        for item in self._all_deadlines_cache:
            case_id = str(item.get("case_id", "")).strip()
            case_name = str(item.get("case_name", "")).strip()
            if not case_id:
                has_unassigned = True
                continue
            if not case_id or case_id in seen:
                continue
            seen.add(case_id)
            self._case_filter_combo.addItem(case_name or case_id, case_id)
        if has_unassigned:
            self._case_filter_combo.addItem("未关联案件", "__unassigned__")
        index = self._case_filter_combo.findData(selected)
        self._case_filter_combo.setCurrentIndex(index if index >= 0 else 0)
        self._case_filter_combo.blockSignals(False)

    def _calculate_summary_stats(self, deadlines: Optional[List[Dict[str, Any]]] = None) -> Dict[str, int]:
        items = deadlines if deadlines is not None else self._all_deadlines_cache
        pending = [item for item in items if not _deadline_is_completed(item)]
        today_value = datetime.now().date()
        week_end = today_value + timedelta(days=7)
        return {
            "today": sum(1 for item in pending if str(item.get("date", "")) == today_value.strftime("%Y-%m-%d")),
            "week": sum(
                1
                for item in pending
                if item.get("date")
                and today_value.strftime("%Y-%m-%d") <= str(item.get("date", "")) <= week_end.strftime("%Y-%m-%d")
            ),
            "overdue": sum(1 for item in pending if _deadline_is_overdue(item)),
            "hearing": sum(1 for item in pending if str(item.get("type", "deadline")) == "hearing"),
        }

    def _refresh_summary_cards(self) -> None:
        stats = self._calculate_summary_stats()
        for key, label in self._stats_value_labels.items():
            label.setText(str(stats.get(key, 0)))

        hearing_today = sum(
            1
            for item in self._all_deadlines_cache
            if not _deadline_is_completed(item)
            and str(item.get("type", "deadline")) == "hearing"
            and _deadline_days_until(item) == 0
        )
        self._stats_hint_labels["today"].setText("含开庭事项" if hearing_today else "当天需要处理的事项")
        self._stats_hint_labels["week"].setText("未来一周内的安排")
        self._stats_hint_labels["overdue"].setText("尚未完成且已过期")
        self._stats_hint_labels["hearing"].setText("开庭事项始终红色高亮")

    def _detail_sort_key(self, deadline: Dict[str, Any]) -> tuple:
        completed = _deadline_is_completed(deadline)
        overdue = _deadline_is_overdue(deadline)
        deadline_type = str(deadline.get("type", "deadline"))
        days_until = _deadline_days_until(deadline)
        priority_rank = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }.get(str(deadline.get("priority", "medium")), 1)
        if not completed and overdue:
            bucket = 0
        elif not completed and deadline_type == "hearing":
            bucket = 1
        elif not completed and days_until is not None and 0 <= days_until <= 7:
            bucket = 2
        elif not completed:
            bucket = 3
        else:
            bucket = 4
        return (
            bucket,
            days_until if days_until is not None else 99999,
            str(deadline.get("date", "")),
            str(deadline.get("time", "") or "99:99"),
            priority_rank,
            str(deadline.get("title", "")),
        )

    def _selected_tag(self) -> str:
        return str(self._tag_filter_combo.currentData() or "").strip()

    def _selected_status_filter(self) -> str:
        return str(self._status_filter_combo.currentData() or "all").strip()

    def _selected_type_filter(self) -> str:
        return str(self._type_filter_combo.currentData() or "all").strip()

    def _selected_case_filter(self) -> str:
        return str(self._case_filter_combo.currentData() or "").strip()

    def _base_deadlines_for_current_view(self) -> List[Dict[str, Any]]:
        if self._detail_mode == "all":
            return list(self._all_deadlines_cache)

        selected = self._calendar.get_selected_date()
        if selected is None:
            return []
        date_key = selected.strftime("%Y-%m-%d")
        return [item for item in self._all_deadlines_cache if str(item.get("date", "")) == date_key]

    def _filtered_deadlines_for_current_view(self) -> List[Dict[str, Any]]:
        items = self._base_deadlines_for_current_view()
        selected_tag = self._selected_tag()
        selected_case = self._selected_case_filter()
        status_filter = self._selected_status_filter()
        type_filter = self._selected_type_filter()
        filtered: List[Dict[str, Any]] = []
        for item in items:
            if selected_tag and selected_tag not in _normalize_tag_list(item.get("case_tags", [])):
                continue
            item_case_id = str(item.get("case_id", "")).strip()
            if selected_case == "__unassigned__":
                if item_case_id:
                    continue
            elif selected_case and item_case_id != selected_case:
                continue
            if type_filter != "all" and str(item.get("type", "deadline")) != type_filter:
                continue
            if status_filter == "pending" and _deadline_is_completed(item):
                continue
            if status_filter == "completed" and not _deadline_is_completed(item):
                continue
            if status_filter == "overdue" and not _deadline_is_overdue(item):
                continue
            days_until = _deadline_days_until(item)
            if self._risk_filter == "overdue" and not _deadline_is_overdue(item):
                continue
            if self._risk_filter == "next3":
                if _deadline_is_completed(item) or days_until is None or days_until < 0 or days_until > 3:
                    continue
            if self._risk_filter == "hearing_week":
                if (
                    _deadline_is_completed(item)
                    or str(item.get("type", "deadline")) != "hearing"
                    or days_until is None
                    or days_until < 0
                    or days_until > 7
                ):
                    continue
            filtered.append(item)
        filtered.sort(key=self._detail_sort_key)
        return filtered

    def _apply_risk_filter(self, filter_key: str) -> None:
        self._risk_filter = "none" if filter_key == "default" else filter_key
        self._detail_mode = "all"
        self._refresh_mode_buttons()
        self._refresh_detail_panel()

    def _set_detail_mode(self, mode: str) -> None:
        if mode not in {"day", "all"}:
            return
        self._detail_mode = mode
        if mode == "day":
            self._risk_filter = "none"
        self._refresh_mode_buttons()
        self._refresh_detail_panel()

    def _clear_detail_list(self) -> None:
        while self._detail_list_layout.count():
            item = self._detail_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _refresh_detail_panel(self) -> None:
        c = COLORS
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        selected = self._calendar.get_selected_date()
        items = self._filtered_deadlines_for_current_view()
        self._clear_detail_list()

        if self._detail_mode == "all":
            self._detail_title.setText(f"全部事项  ·  {len(items)} 项")
            filter_notes = []
            if self._selected_tag():
                filter_notes.append(f"标签：{self._selected_tag()}")
            if self._selected_case_filter():
                filter_notes.append(f"案件：{self._case_filter_combo.currentText()}")
            if self._selected_status_filter() != "all":
                filter_notes.append(self._status_filter_combo.currentText())
            if self._selected_type_filter() != "all":
                filter_notes.append(self._type_filter_combo.currentText())
            if self._risk_filter == "overdue":
                filter_notes.append("风险：已逾期")
            elif self._risk_filter == "next3":
                filter_notes.append("风险：未来3天")
            elif self._risk_filter == "hearing_week":
                filter_notes.append("风险：本周开庭")
            note_text = "，".join(filter_notes) if filter_notes else "按风险优先排序，优先显示逾期、开庭和近 7 天事项。"
            self._detail_context_label.setText(note_text)
            empty_text = "当前筛选下暂无事项"
        else:
            if selected is None:
                self._detail_title.setText("选择日期查看期限")
                self._detail_context_label.setText("当天事项会按风险高低排序展示。")
                empty_text = "暂无期限"
            else:
                self._detail_title.setText(
                    f"{selected.month}月{selected.day}日 ({weekday_names[selected.weekday()]})"
                    + (f"  ·  {len(items)} 项安排" if items else "")
                )
                self._detail_context_label.setText("双击事项可直接跳回案件期限页面，全部事项可切换到右上角查看。")
                empty_text = "该日暂无事项"

        if not items:
            no_label = QLabel(empty_text)
            no_label.setStyleSheet(f"""
                background: transparent;
                color: {c['text_muted']};
                font-size: 13px;
                padding: 32px 0;
            """)
            no_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._detail_list_layout.addWidget(no_label)
            self._detail_list_layout.addStretch()
            self._detail_expand_toggle_btn.setEnabled(False)
            return

        self._detail_expand_toggle_btn.setEnabled(True)
        for dl in items:
            row = DeadlineDetailRow(
                dl,
                edit_callback=self._on_edit_deadline_from_detail,
                toggle_callback=self._on_toggle_deadline_from_detail,
                remove_callback=self._on_remove_deadline_item,
                open_case_callback=self._on_open_case_from_detail,
                postpone_callback=self._on_postpone_deadline_from_detail,
                parent=self._detail_container,
                show_date=self._detail_mode == "all",
                expanded=self._detail_rows_expanded,
            )
            self._detail_list_layout.addWidget(row)

        self._detail_list_layout.addStretch()

    def _toggle_detail_rows_expanded(self) -> None:
        self._set_detail_rows_expanded(not self._detail_rows_expanded)

    def _set_detail_rows_expanded(self, expanded: bool) -> None:
        self._detail_rows_expanded = expanded
        self._refresh_queue_buttons()
        for row in self._detail_container.findChildren(DeadlineDetailRow):
            row.set_expanded(expanded)

    def _jump_to_date(self, target_date: date) -> None:
        """切换到指定日期所在周期并刷新详情。"""
        self._current_year = target_date.year
        self._current_month = target_date.month
        self._current_week_start = target_date - timedelta(days=target_date.weekday())
        if self._calendar_view_mode == "month":
            self._calendar.set_month(self._current_year, self._current_month)
            self._calendar.set_view_mode("month", target_date)
        else:
            self._calendar.set_view_mode("week", target_date)
        self._calendar.set_selected_date(target_date)
        self._update_period_label()
        self._load_deadlines()

    def focus_date(self, target_date: date, *, detail_mode: Optional[str] = None) -> None:
        """公开入口：定位到指定日期，并可选切换右侧事项模式。"""
        self._jump_to_date(target_date)
        if detail_mode in {"day", "all"}:
            self._set_detail_mode(detail_mode)

    def focus_date_text(self, date_text: str, *, detail_mode: Optional[str] = None) -> bool:
        """公开入口：按字符串日期定位到指定日期。"""
        try:
            target_date = datetime.strptime(str(date_text or "").strip(), "%Y-%m-%d").date()
        except ValueError:
            return False
        self.focus_date(target_date, detail_mode=detail_mode)
        return True

    def _open_deadline_dialog(
        self,
        *,
        deadline: Optional[Dict[str, Any]] = None,
        preset_date: Optional[date] = None,
        default_type: str = "deadline",
        initial_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """打开新版期限弹窗。"""
        cases = self._cases_for_dialog()

        initial = dict(deadline or {})
        if initial_data:
            initial.update(initial_data)
        if preset_date:
            initial["date"] = preset_date.strftime("%Y-%m-%d")
        if "type" not in initial:
            initial["type"] = default_type
        if not deadline:
            if default_type == "hearing":
                initial.setdefault("time", "09:00")
                initial.setdefault("all_day", False)
            else:
                initial.setdefault("time", "")
                initial.setdefault("all_day", True)

        selected_case_id = str(initial.get("case_id", "")).strip()
        dialog = DeadlineEditorDialog(
            initial,
            self,
            cases=cases,
            selected_case_id=selected_case_id,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False

        data = dialog.get_deadline_data()
        case_id = dialog.get_selected_case_id()
        if not data:
            return False

        edited_date_text = str(data.get("date", "")).strip()
        edited_date = datetime.strptime(edited_date_text, "%Y-%m-%d").date()

        if deadline and deadline.get("id"):
            original_case_id = str(deadline.get("case_id", "")).strip()
            deadline_id = str(deadline.get("id", "")).strip()
            if original_case_id and case_id and original_case_id == case_id:
                self._cm.update_deadline(case_id, deadline_id, data)
            elif original_case_id and case_id:
                self._cm.remove_deadline(original_case_id, deadline_id)
                self._cm.add_deadline(case_id, {**data, "id": deadline_id})
            elif original_case_id and not case_id:
                self._cm.remove_deadline(original_case_id, deadline_id)
                self._cm.add_global_deadline({**data, "id": deadline_id})
            elif not original_case_id and case_id:
                self._cm.remove_global_deadline(deadline_id)
                self._cm.add_deadline(case_id, {**data, "id": deadline_id})
            else:
                self._cm.update_global_deadline(deadline_id, data)
        else:
            if case_id:
                self._cm.add_deadline(case_id, data)
            else:
                self._cm.add_global_deadline(data)

        self._jump_to_date(edited_date)
        return True

    def _quick_template_defaults(self, template_key: str) -> Dict[str, Any]:
        templates = {
            "evidence": {
                "title": "举证期限",
                "type": "deadline",
                "priority": "high",
                "remind_before": [7, 3, 1, 0],
                "all_day": True,
                "time": "",
            },
            "defense": {
                "title": "答辩期限",
                "type": "deadline",
                "priority": "high",
                "remind_before": [7, 3, 1, 0],
                "all_day": True,
                "time": "",
            },
            "appeal": {
                "title": "上诉期限",
                "type": "deadline",
                "priority": "high",
                "remind_before": [7, 3, 1, 0],
                "all_day": True,
                "time": "",
            },
            "payment": {
                "title": "缴费期限",
                "type": "deadline",
                "priority": "medium",
                "remind_before": [3, 1, 0],
                "all_day": True,
                "time": "",
            },
        }
        return dict(templates.get(template_key, {}))

    def _on_quick_add_template(self, template_key: str) -> None:
        if template_key == "add_deadline":
            self._on_add_deadline("deadline")
            return
        if template_key == "add_hearing":
            self._on_add_deadline("hearing")
            return
        target_date = self._calendar.get_selected_date() or datetime.now().date()
        defaults = self._quick_template_defaults(template_key)
        self._open_deadline_dialog(
            preset_date=target_date,
            default_type=str(defaults.get("type", "deadline")),
            initial_data=defaults,
        )

    def _load_deadlines(self) -> None:
        """加载当前视图范围内的期限。"""
        self._all_deadlines_cache = self._build_all_deadlines_cache()
        if self._calendar_view_mode == "week":
            week_end = self._current_week_start + timedelta(days=6)
            visible_deadlines = []
            for deadline in self._all_deadlines_cache:
                deadline_day = _deadline_date_value(deadline)
                if deadline_day is None:
                    continue
                if self._current_week_start <= deadline_day <= week_end:
                    visible_deadlines.append(deadline)
            self._calendar.set_view_mode("week", self._calendar.get_selected_date() or self._current_week_start)
        else:
            month_prefix = f"{self._current_year}-{self._current_month:02d}"
            visible_deadlines = [
                deadline
                for deadline in self._all_deadlines_cache
                if str(deadline.get("date", "")).startswith(month_prefix)
            ]
            self._calendar.set_month(self._current_year, self._current_month)
            self._calendar.set_view_mode("month", self._calendar.get_selected_date() or date(self._current_year, self._current_month, 1))

        self._calendar.set_deadlines(visible_deadlines)
        self._refresh_tag_filter_options()
        self._refresh_case_filter_options()
        self._refresh_summary_cards()
        self._refresh_detail_panel()

    # ── 事件处理 ──

    def _on_tool_center(self) -> None:
        """打开工具中心。"""
        from src.gui.tool_center_dialog import ToolCenterDialog
        dialog = ToolCenterDialog(self)
        dialog.exec()

    def _find_case_manager_owner(self):
        from src.gui.case_manager_dialog import CaseManagerDialog

        parent = self.parentWidget()
        visited = 0
        while parent is not None and visited < 8:
            if isinstance(parent, CaseManagerDialog):
                return parent
            parent = parent.parentWidget()
            visited += 1
        return None

    def _on_case_manager(self) -> None:
        """打开案件管理，若当前已在案件管理上下文中则直接返回。"""
        owner = self._find_case_manager_owner()
        if owner is not None:
            self.accept()
            owner.show()
            owner.raise_()
            owner.activateWindow()
            return

        from src.gui.case_manager_dialog import CaseManagerDialog

        dialog = CaseManagerDialog(self.parentWidget() or self)
        dialog.exec()

    def _on_prev_month(self) -> None:
        if self._calendar_view_mode == "week":
            selected = self._calendar.get_selected_date()
            offset = max(0, min(6, (selected - self._current_week_start).days)) if selected else 0
            self._current_week_start -= timedelta(days=7)
            self._current_year = self._current_week_start.year
            self._current_month = self._current_week_start.month
            self._calendar.set_view_mode("week", self._current_week_start)
            self._calendar.set_selected_date(self._current_week_start + timedelta(days=offset))
        else:
            self._current_month -= 1
            if self._current_month < 1:
                self._current_month = 12
                self._current_year -= 1
        self._update_month()

    def _on_next_month(self) -> None:
        if self._calendar_view_mode == "week":
            selected = self._calendar.get_selected_date()
            offset = max(0, min(6, (selected - self._current_week_start).days)) if selected else 0
            self._current_week_start += timedelta(days=7)
            self._current_year = self._current_week_start.year
            self._current_month = self._current_week_start.month
            self._calendar.set_view_mode("week", self._current_week_start)
            self._calendar.set_selected_date(self._current_week_start + timedelta(days=offset))
        else:
            self._current_month += 1
            if self._current_month > 12:
                self._current_month = 1
                self._current_year += 1
        self._update_month()

    def _on_today(self) -> None:
        today = datetime.now().date()
        self._current_year = today.year
        self._current_month = today.month
        self._current_week_start = today - timedelta(days=today.weekday())
        if self._calendar_view_mode == "week":
            self._calendar.set_view_mode("week", today)
        else:
            self._calendar.set_month(self._current_year, self._current_month)
            self._calendar.set_view_mode("month", today)
        self._calendar.set_selected_date(today)
        self._update_month()

    def _update_month(self) -> None:
        """更新当前周期显示。"""
        if self._calendar_view_mode == "week":
            selected = self._calendar.get_selected_date()
            if selected is None or not (self._current_week_start <= selected <= self._current_week_start + timedelta(days=6)):
                self._calendar.set_selected_date(self._current_week_start)
            self._calendar.set_view_mode("week", self._calendar.get_selected_date() or self._current_week_start)
        else:
            self._calendar.set_month(self._current_year, self._current_month)
            selected = self._calendar.get_selected_date()
            if selected is None or selected.year != self._current_year or selected.month != self._current_month:
                self._calendar.set_selected_date(date(self._current_year, self._current_month, 1))
            self._calendar.set_view_mode("month", self._calendar.get_selected_date() or date(self._current_year, self._current_month, 1))
        self._update_period_label()
        self._refresh_calendar_view_buttons()
        self._load_deadlines()

    def _on_date_clicked(self, d: date) -> None:
        """日期点击"""
        self._refresh_detail_panel()

    def _on_date_double_clicked(self, d: date, preset_time: Optional[str] = None) -> None:
        """双击空白日期卡：新增当天提醒。"""
        initial_data = None
        if preset_time:
            initial_data = {
                "time": preset_time,
                "all_day": False,
            }
        self._open_deadline_dialog(preset_date=d, default_type="deadline", initial_data=initial_data)

    def _on_deadline_preview_double_clicked(self, deadline: Dict[str, Any]) -> None:
        """双击月视图事项预览：跳转案件期限编辑。"""
        self._on_edit_deadline_from_detail(deadline)

    def _on_edit_deadline_from_detail(self, deadline: Dict[str, Any]) -> None:
        """在当前日历界面内直接编辑期限。"""
        self._open_deadline_dialog(deadline=deadline)

    def _on_open_case_from_detail(self, deadline: Dict[str, Any]) -> None:
        """从日历直接打开对应案件。"""
        case_id = str(deadline.get("case_id", "")).strip()
        if not case_id:
            return
        self.navigate_to_deadline_requested.emit(case_id, "")
        self.accept()

    def _on_toggle_deadline_from_detail(self, deadline: Dict[str, Any]) -> None:
        """切换右侧详情中的期限状态。"""
        case_id = str(deadline.get("case_id", "")).strip()
        deadline_id = str(deadline.get("id", "")).strip()
        if not deadline_id:
            return

        completed = str(deadline.get("status", "pending")) != "completed"
        updates = {
            "status": "completed" if completed else "pending",
            "completed_at": datetime.now().isoformat() if completed else "",
        }
        if case_id:
            changed = self._cm.update_deadline(case_id, deadline_id, updates)
        else:
            changed = self._cm.update_global_deadline(deadline_id, updates)
        if changed:
            self._load_deadlines()

    def _on_drag_deadline_from_calendar(
        self,
        deadline: Dict[str, Any],
        target_date: date,
        target_time: Optional[str] = None,
    ) -> None:
        """月/周视图拖拽事项后，直接回写日期，并在周视图下同步时间。"""
        case_id = str(deadline.get("case_id", "")).strip()
        deadline_id = str(deadline.get("id", "")).strip()
        if not deadline_id:
            return

        updates = {
            "date": target_date.strftime("%Y-%m-%d"),
        }
        if target_time is not None:
            updates.update({
                "time": target_time,
                "all_day": False,
            })
        if case_id:
            changed = self._cm.update_deadline(case_id, deadline_id, updates)
        else:
            changed = self._cm.update_global_deadline(deadline_id, updates)
        if changed:
            self._jump_to_date(target_date)

    def _on_drag_deadline_from_week_view(
        self,
        deadline: Dict[str, Any],
        target_date: date,
        target_time: str,
    ) -> None:
        """兼容旧调用：周视图拖拽事项后回写日期和时间。"""
        self._on_drag_deadline_from_calendar(deadline, target_date, target_time)

    def _on_postpone_deadline_from_detail(self, deadline: Dict[str, Any]) -> None:
        """快速顺延一天，便于律师滚动处理待办。"""
        case_id = str(deadline.get("case_id", "")).strip()
        deadline_id = str(deadline.get("id", "")).strip()
        date_text = str(deadline.get("date", "")).strip()
        if not deadline_id or not date_text:
            return

        try:
            current_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        except ValueError:
            return

        new_date = current_date + timedelta(days=1)
        updates = {
            "date": new_date.strftime("%Y-%m-%d"),
            "status": "pending",
            "completed_at": "",
        }
        if case_id:
            changed = self._cm.update_deadline(case_id, deadline_id, updates)
        else:
            changed = self._cm.update_global_deadline(deadline_id, updates)
        if changed:
            self._jump_to_date(new_date)

    def _on_add_deadline(self, dl_type: str) -> None:
        """从顶部工具栏新增期限。"""
        target_date = self._calendar.get_selected_date() or datetime.now().date()
        self._open_deadline_dialog(preset_date=target_date, default_type=dl_type)

    def _on_remove_deadline_item(self, deadline: Dict[str, Any]) -> None:
        """删除右侧详情中的期限。"""
        self._on_remove_deadline(str(deadline.get("case_id", "")), str(deadline.get("id", "")))

    def _on_remove_deadline(self, case_id: str, deadline_id: str) -> None:
        """删除期限"""
        if deadline_id:
            if case_id:
                self._cm.remove_deadline(case_id, deadline_id)
            else:
                self._cm.remove_global_deadline(deadline_id)
            self._load_deadlines()
