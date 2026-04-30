# -*- coding: utf-8 -*-
"""案件管理辅助对话框"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from PySide6.QtCore import QDate, QEvent, QStringListModel, QTime, QTimer, Qt
from PySide6.QtWidgets import (
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    # QFormLayout — 使用 TransparentFormLayout 替代
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.case_manager import CORE_INFO_FIELD_DEFINITIONS
from src.gui.styles import APP_COLORS as COLORS, CHECK_ICON_PATH

DROPDOWN_ARROW_PATH = CHECK_ICON_PATH.replace("check.svg", "dropdown_arrow.svg")


_FULLWIDTH_TRANSLATION = str.maketrans({
    "０": "0",
    "１": "1",
    "２": "2",
    "３": "3",
    "４": "4",
    "５": "5",
    "６": "6",
    "７": "7",
    "８": "8",
    "９": "9",
    "：": ":",
    "，": ",",
    "／": "/",
    "－": "-",
    "　": " ",
})

_PM_HINTS = ("下午", "晚上", "傍晚", "pm", "p.m", "中午")
_AM_HINTS = ("上午", "凌晨", "早上", "am", "a.m")

DEADLINE_TYPE_LABELS = {
    "deadline": "普通期限",
    "hearing": "开庭/庭前",
    "custom": "自定义提醒",
}

DEADLINE_PRIORITY_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
}

CASE_CATEGORY_OPTIONS = [
    ("民事", "civil"),
    ("刑事", "criminal"),
    ("行政", "administrative"),
    ("非诉", "non_litigation"),
    ("劳动仲裁", "labor_arbitration"),
    ("商事仲裁", "commercial_arbitration"),
]

CASE_STATUS_OPTIONS = [
    ("推进中", "active"),
    ("未完结", "pending"),
    ("待归档", "closed"),
]

_HEARING_TITLE_RULES = [
    ("庭前会议", "庭前会议"),
    ("开庭审理", "开庭安排"),
    ("开庭", "开庭安排"),
    ("庭审", "庭审安排"),
    ("听证", "听证安排"),
    ("宣判", "宣判安排"),
    ("询问", "询问安排"),
]

_DEADLINE_TITLE_RULES = [
    ("举证", "举证期限"),
    ("答辩", "答辩期限"),
    ("上诉", "上诉期限"),
    ("补正", "补正期限"),
    ("提交证据", "提交证据期限"),
    ("提交材料", "提交材料期限"),
    ("提交", "材料提交提醒"),
    ("缴费", "缴费期限"),
    ("截止", "截止提醒"),
    ("到期", "到期提醒"),
]

_CUSTOM_TITLE_RULES = [
    ("会见", "会见安排"),
    ("会谈", "会谈安排"),
    ("沟通", "沟通安排"),
    ("签约", "签约安排"),
    ("签署", "签署安排"),
    ("会议", "会议安排"),
]

_SMART_DATETIME_RE = re.compile(
    r"(?:(?:\d{2}|\d{4})[年/-]\d{1,2}[月/-]\d{1,2}(?:[日号])?|20\d{6}(?:\d{2}(?:\d{2})?)?)"
    r"(?:(?:\s+|[/-]|，|,)?(?:上午|下午|晚上|傍晚|中午|凌晨|早上|am|pm|a\.m|p\.m)?\s*\d{1,2}(?:[:：时点]\d{1,2}|点半|时半|点|时)?\s*分?)?"
    r"|(?:上午|下午|晚上|傍晚|中午|凌晨|早上|am|pm|a\.m|p\.m)?\s*\d{1,2}(?:[:：]\d{1,2}|[时点]\d{1,2}\s*分?|[时点]半|[时点])",
    re.IGNORECASE,
)


def normalize_tags(tags: Iterable[str]) -> List[str]:
    """规范化标签列表，去重并保留原顺序。"""
    result: List[str] = []
    seen = set()

    for tag in tags:
        value = str(tag or "").strip().lstrip("#")
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)

    return result


def _normalize_year(year_text: str) -> int:
    """将两位或四位年份统一为四位年份。"""
    year = int(year_text)
    if year < 100:
        return 2000 + year
    return year


def _extract_date_parts(text: str) -> tuple[Optional[int], Optional[int], Optional[int], str]:
    """从文本中提取日期部分，并返回剔除日期后的剩余文本。"""
    translated = str(text or "").translate(_FULLWIDTH_TRANSLATION)

    compact_match = re.search(r"(?<!\d)(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})(?P<time>\d{2,4})?(?!\d)", translated)
    if compact_match:
        year = int(compact_match.group("year"))
        month = int(compact_match.group("month"))
        day = int(compact_match.group("day"))
        remaining = translated[:compact_match.start()] + (compact_match.group("time") or "") + translated[compact_match.end():]
        return year, month, day, remaining

    patterns = [
        re.compile(r"(?P<year>\d{2,4})\s*[年/-]\s*(?P<month>\d{1,2})\s*[月/-]\s*(?P<day>\d{1,2})(?:\s*[日号])?", re.IGNORECASE),
        re.compile(r"(?P<month>\d{1,2})\s*[月/-]\s*(?P<day>\d{1,2})(?:\s*[日号])?", re.IGNORECASE),
    ]
    for pattern in patterns:
        match = pattern.search(translated)
        if not match:
            continue
        year_text = match.groupdict().get("year")
        year = _normalize_year(year_text) if year_text else datetime.now().year
        month = int(match.group("month"))
        day = int(match.group("day"))
        remaining = translated[:match.start()] + " " + translated[match.end():]
        return year, month, day, remaining

    return None, None, None, translated


def _extract_time_parts(text: str) -> tuple[Optional[int], Optional[int]]:
    """从文本中提取时间部分。"""
    translated = str(text or "").translate(_FULLWIDTH_TRANSLATION)

    colon_match = re.search(r"(?<!\d)(?P<hour>\d{1,2})\s*[:：]\s*(?P<minute>\d{1,2})(?!\d)", translated)
    if colon_match:
        return int(colon_match.group("hour")), int(colon_match.group("minute"))

    half_match = re.search(r"(?<!\d)(?P<hour>\d{1,2})\s*(?:点|时)\s*半(?!\d)", translated)
    if half_match:
        return int(half_match.group("hour")), 30

    hm_match = re.search(r"(?<!\d)(?P<hour>\d{1,2})\s*(?:点|时)\s*(?P<minute>\d{1,2})\s*(?:分)?(?!\d)", translated)
    if hm_match:
        return int(hm_match.group("hour")), int(hm_match.group("minute"))

    hour_match = re.search(r"(?<!\d)(?P<hour>\d{1,2})\s*(?:点|时)(?!\d)", translated)
    if hour_match:
        return int(hour_match.group("hour")), 0

    pure_digits = re.sub(r"\D", "", translated)
    stripped = re.sub(r"\s+", "", translated)
    if stripped.isdigit():
        if len(pure_digits) == 4:
            return int(pure_digits[0:2]), int(pure_digits[2:4])
        if len(pure_digits) == 2:
            return int(pure_digits), 0
        if len(pure_digits) in (10, 12):
            hour = int(pure_digits[8:10])
            minute = int(pure_digits[10:12]) if len(pure_digits) == 12 else 0
            return hour, minute

    return None, None


def parse_deadline_input_text(
    text: str,
    *,
    default_time: str = "",
    default_all_day: bool = True,
) -> Dict[str, Any]:
    """解析自然输入的期限日期时间。"""
    raw_text = str(text or "").strip()
    if not raw_text:
        raise ValueError("请输入日期时间。")

    translated = raw_text.translate(_FULLWIDTH_TRANSLATION)
    lowered = translated.lower()
    has_pm_hint = any(token in lowered for token in _PM_HINTS)
    has_am_hint = any(token in lowered for token in _AM_HINTS)
    explicit_all_day = "全天" in raw_text

    year, month, day, remaining = _extract_date_parts(translated)
    hour, minute = _extract_time_parts(remaining)

    if year is None or month is None or day is None:
        if hour is None:
            raise ValueError("无法识别日期时间，请输入类似 2024-04-03 16:20、23年2月17、上午9点 的格式。")
        today = datetime.now()
        year, month, day = today.year, today.month, today.day

    if hour is not None:
        if has_pm_hint and hour < 12:
            hour += 12
        if has_am_hint and hour == 12:
            hour = 0

    if hour is None:
        if explicit_all_day:
            all_day = True
            time_text = ""
        elif default_time:
            all_day = False
            time_text = default_time
            hour, minute = [int(item) for item in default_time.split(":", 1)]
        else:
            all_day = bool(default_all_day)
            time_text = ""
    else:
        all_day = False
        time_text = f"{hour:02d}:{minute:02d}"

    try:
        if all_day:
            parsed_dt = datetime(year, month, day)
        else:
            parsed_dt = datetime(year, month, day, hour, minute)
    except ValueError as exc:
        raise ValueError(f"日期时间无效：{exc}") from exc

    return {
        "date": parsed_dt.strftime("%Y-%m-%d"),
        "time": "" if all_day else time_text,
        "all_day": all_day,
        "display_text": (
            parsed_dt.strftime("%Y-%m-%d 全天")
            if all_day else
            parsed_dt.strftime("%Y-%m-%d %H:%M")
        ),
    }


def _find_smart_datetime_span(text: str) -> Optional[tuple[int, int]]:
    """找到文本中的日期时间片段范围。"""
    translated = str(text or "").translate(_FULLWIDTH_TRANSLATION)
    match = _SMART_DATETIME_RE.search(translated)
    if not match:
        return None
    return match.start(), match.end()


def _clean_deadline_context_text(text: str) -> str:
    """移除文本中的日期时间，只保留事项上下文。"""
    raw_text = str(text or "").strip()
    if not raw_text:
        return ""

    span = _find_smart_datetime_span(raw_text)
    if span:
        start, end = span
        raw_text = f"{raw_text[:start]} {raw_text[end:]}"

    cleaned = re.sub(r"\s+", " ", raw_text).strip(" ，,。；;、")
    cleaned = re.sub(r"^(前|后)\s*", "", cleaned)
    return cleaned


def _detect_deadline_type(text: str) -> str:
    """根据文本内容推断期限类型。"""
    lowered = str(text or "").translate(_FULLWIDTH_TRANSLATION).lower()
    if any(keyword in lowered for keyword, _ in _HEARING_TITLE_RULES):
        return "hearing"
    if any(keyword in lowered for keyword, _ in _DEADLINE_TITLE_RULES):
        return "deadline"
    return "custom"


def _strip_leading_location(text: str) -> str:
    """去掉开头地点前缀，便于生成更短标题。"""
    cleaned = str(text or "").strip(" ，,。；;：:")
    cleaned = re.sub(
        r"^(在|于)[^，。；;]{0,36}?(法院|法庭|仲裁委|仲裁庭|检察院|公安局|派出所|看守所|会议室|调解室)",
        "",
        cleaned,
    )
    return cleaned.strip(" ，,。；;：:")


def _shorten_title_suffix(text: str, limit: int = 20) -> str:
    """截断附加标题文本，保持标题紧凑。"""
    cleaned = str(text or "").strip(" ，,。；;：:")
    cleaned = re.sub(r"\s+", "", cleaned)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip("，,。；;：:")


def _extract_title_subject(text: str, keywords: Iterable[str]) -> str:
    """从上下文里提取事项主体。"""
    context = _strip_leading_location(text)
    translated = context.translate(_FULLWIDTH_TRANSLATION)
    for keyword in keywords:
        index = translated.find(keyword)
        if index < 0:
            continue
        subject = context[index + len(keyword):]
        subject = re.sub(r"^[：:，,、\s]*(审理|处理|办理|召开|进行|安排)?", "", subject)
        subject = subject.strip(" ，,。；;：:")
        if subject:
            return _shorten_title_suffix(subject)
    return _shorten_title_suffix(context, limit=18)


def _guess_deadline_title(text: str, deadline_type: str) -> str:
    """推断事项标题。"""
    context = str(text or "").strip()
    if not context:
        return {
            "hearing": "开庭安排",
            "deadline": "普通期限",
            "custom": "自定义提醒",
        }.get(deadline_type, "事项提醒")

    if deadline_type == "hearing":
        for keyword, base_title in _HEARING_TITLE_RULES:
            if keyword in context:
                subject = _extract_title_subject(context, [keyword])
                if subject and subject != base_title:
                    return f"{base_title} - {subject}"
                return base_title
        return "开庭安排"

    if deadline_type == "deadline":
        for keyword, base_title in _DEADLINE_TITLE_RULES:
            if keyword in context:
                return base_title
        return "普通期限"

    for keyword, base_title in _CUSTOM_TITLE_RULES:
        if keyword in context:
            return base_title
    return "自定义提醒"


def _guess_deadline_priority(text: str, deadline_type: str) -> str:
    """根据语义粗略推断优先级。"""
    lowered = str(text or "").translate(_FULLWIDTH_TRANSLATION).lower()
    if any(keyword in lowered for keyword in ("紧急", "立即", "马上", "尽快", "今天", "今日", "明天", "明日", "截止", "到期")):
        return "high"
    if deadline_type == "hearing":
        return "high"
    if any(keyword in lowered for keyword in ("举证", "答辩", "上诉", "补正", "提交", "缴费")):
        return "medium"
    return "medium"


def parse_deadline_smart_input_text(text: str) -> Dict[str, Any]:
    """从完整事项句子中智能提取期限结构信息。"""
    raw_text = str(text or "").strip()
    if not raw_text:
        raise ValueError("请输入要识别的完整事项。")

    deadline_type = _detect_deadline_type(raw_text)
    default_time = "09:00" if deadline_type == "hearing" else ""
    default_all_day = deadline_type != "hearing"
    parsed = parse_deadline_input_text(
        raw_text,
        default_time=default_time,
        default_all_day=default_all_day,
    )
    description = _clean_deadline_context_text(raw_text)
    title = _guess_deadline_title(description or raw_text, deadline_type)
    priority = _guess_deadline_priority(description or raw_text, deadline_type)

    return {
        **parsed,
        "title": title,
        "type": deadline_type,
        "priority": priority,
        "description": description,
        "type_label": DEADLINE_TYPE_LABELS.get(deadline_type, "自定义提醒"),
        "priority_label": DEADLINE_PRIORITY_LABELS.get(priority, "中"),
    }


class TagEditorDialog(QDialog):
    """案件标签编辑对话框"""

    def __init__(
        self,
        current_tags: List[str],
        suggested_tags: List[str],
        parent=None,
        *,
        current_category: str = "",
        current_status: str = "active",
    ):
        super().__init__(parent)
        self._tags = normalize_tags(current_tags)
        self._suggested_tags = normalize_tags(suggested_tags)
        self._category = str(current_category or "").strip()
        self._status = str(current_status or "active").strip() or "active"
        self._category_buttons: Dict[str, QPushButton] = {}
        self._status_buttons: Dict[str, QPushButton] = {}
        self._setup_ui()
        self._refresh_status_buttons()
        self._refresh_category_buttons()
        self._refresh_current_tags()
        self._refresh_suggestions()

    def _setup_ui(self) -> None:
        c = COLORS
        self.setWindowTitle("标签/分类")
        self.setMinimumSize(560, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        hint = QLabel("标签用于快速归类、搜索和筛选。案件类型与办理状态也可在这里手动修正，保存后会同步到左侧列表与筛选。")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px;")
        layout.addWidget(hint)

        status_title = QLabel("办理状态")
        status_title.setStyleSheet(f"color: {c['text_primary']}; font-size: 13px; font-weight: 600;")
        layout.addWidget(status_title)

        self._status_widget = QWidget()
        self._status_layout = QGridLayout(self._status_widget)
        self._status_layout.setContentsMargins(0, 0, 0, 0)
        self._status_layout.setHorizontalSpacing(6)
        self._status_layout.setVerticalSpacing(6)
        layout.addWidget(self._status_widget)

        category_title = QLabel("案件类型")
        category_title.setStyleSheet(f"color: {c['text_primary']}; font-size: 13px; font-weight: 600;")
        layout.addWidget(category_title)

        self._category_widget = QWidget()
        self._category_layout = QGridLayout(self._category_widget)
        self._category_layout.setContentsMargins(0, 0, 0, 0)
        self._category_layout.setHorizontalSpacing(6)
        self._category_layout.setVerticalSpacing(6)
        layout.addWidget(self._category_widget)

        add_row = QHBoxLayout()
        add_row.setSpacing(6)

        self._tag_input = QLineEdit()
        self._tag_input.setPlaceholderText("输入标签后回车，例如：合同、仲裁、紧急")
        self._tag_input.returnPressed.connect(self._add_tag_from_input)
        add_row.addWidget(self._tag_input, 1)

        add_btn = QPushButton("添加标签")
        add_btn.clicked.connect(self._add_tag_from_input)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        current_title = QLabel("当前标签")
        current_title.setStyleSheet(f"color: {c['text_primary']}; font-size: 13px; font-weight: 600;")
        layout.addWidget(current_title)

        self._current_tags_widget = QWidget()
        self._current_tags_layout = QGridLayout(self._current_tags_widget)
        self._current_tags_layout.setContentsMargins(0, 0, 0, 0)
        self._current_tags_layout.setHorizontalSpacing(6)
        self._current_tags_layout.setVerticalSpacing(6)
        layout.addWidget(self._current_tags_widget)

        suggestion_title = QLabel("常用标签")
        suggestion_title.setStyleSheet(f"color: {c['text_primary']}; font-size: 13px; font-weight: 600;")
        layout.addWidget(suggestion_title)

        self._suggestions_widget = QWidget()
        self._suggestions_layout = QGridLayout(self._suggestions_widget)
        self._suggestions_layout.setContentsMargins(0, 0, 0, 0)
        self._suggestions_layout.setHorizontalSpacing(6)
        self._suggestions_layout.setVerticalSpacing(6)
        layout.addWidget(self._suggestions_widget)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _style_choice_button(self, button: QPushButton, active: bool) -> None:
        c = COLORS
        if active:
            button.setStyleSheet(f"""
                QPushButton {{
                    background: {c['accent_light']};
                    color: {c['accent']};
                    border: none;
                    border-radius: 8px;
                    padding: 4px 8px;
                    min-height: 28px;
                    max-height: 28px;
                    font-size: 11px;
                    font-weight: 700;
                }}
            """)
            return

        button.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_1']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 4px 8px;
                min-height: 28px;
                max-height: 28px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
            }}
        """)

    def _refresh_status_buttons(self) -> None:
        self._clear_layout(self._status_layout)
        self._status_buttons = {}
        for index, (label, value) in enumerate(CASE_STATUS_OPTIONS):
            button = QPushButton(label)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, current=value: self._set_status(current))
            self._style_choice_button(button, self._status == value)
            self._status_buttons[value] = button
            row, col = divmod(index, 3)
            self._status_layout.addWidget(button, row, col)

    def _refresh_category_buttons(self) -> None:
        self._clear_layout(self._category_layout)
        self._category_buttons = {}
        for index, (label, value) in enumerate(CASE_CATEGORY_OPTIONS):
            button = QPushButton(label)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, current=value: self._set_category(current))
            self._style_choice_button(button, self._category == value)
            self._category_buttons[value] = button
            row, col = divmod(index, 3)
            self._category_layout.addWidget(button, row, col)

    def _set_status(self, value: str) -> None:
        self._status = value
        self._refresh_status_buttons()

    def _set_category(self, value: str) -> None:
        self._category = value
        self._refresh_category_buttons()

    def _add_tag_from_input(self) -> None:
        value = self._tag_input.text().strip()
        if not value:
            return
        self._tag_input.clear()
        self._add_tag(value)

    def _add_tag(self, tag: str) -> None:
        normalized = normalize_tags([tag])
        if not normalized:
            return
        value = normalized[0]
        if value.lower() not in {item.lower() for item in self._suggested_tags}:
            self._suggested_tags.append(value)
        if value.lower() in {item.lower() for item in self._tags}:
            self._refresh_suggestions()
            return
        self._tags.append(value)
        self._refresh_current_tags()
        self._refresh_suggestions()

    def _remove_suggestion_tag(self, tag: str) -> None:
        self._suggested_tags = [item for item in self._suggested_tags if item.lower() != tag.lower()]
        self._refresh_suggestions()

    def _remove_tag(self, tag: str) -> None:
        self._tags = [item for item in self._tags if item.lower() != tag.lower()]
        self._refresh_current_tags()
        self._refresh_suggestions()

    def _refresh_current_tags(self) -> None:
        c = COLORS
        self._clear_layout(self._current_tags_layout)

        if not self._tags:
            empty = QLabel("暂无标签")
            empty.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px;")
            self._current_tags_layout.addWidget(empty, 0, 0)
            return

        for index, tag in enumerate(self._tags):
            chip = QPushButton(f"#{tag}  ×")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setStyleSheet(f"""
                QPushButton {{
                    background: {c['accent_light']};
                    color: {c['accent']};
                    border: none;
                    border-radius: 8px;
                    padding: 4px 8px;
                    min-height: 26px;
                    max-height: 26px;
                    font-size: 11px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {c['accent_subtle']};
                }}
            """)
            chip.clicked.connect(lambda checked=False, t=tag: self._remove_tag(t))
            row, col = divmod(index, 4)
            self._current_tags_layout.addWidget(chip, row, col)

    def _refresh_suggestions(self) -> None:
        c = COLORS
        self._clear_layout(self._suggestions_layout)
        current_keys = {item.lower() for item in self._tags}
        if not self._suggested_tags:
            empty = QLabel("暂无可推荐标签")
            empty.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px;")
            self._suggestions_layout.addWidget(empty, 0, 0)
            return

        for index, tag in enumerate(self._suggested_tags[:24]):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {c['surface_1']};
                    border: 1px solid {c['border']};
                    border-radius: 8px;
                }}
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(8, 4, 6, 4)
            card_layout.setSpacing(4)

            btn = QPushButton(f"#{tag}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_active = tag.lower() in current_keys
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {c['accent']};
                        border: none;
                        padding: 0;
                        font-size: 11px;
                        font-weight: 700;
                        text-align: left;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {c['text_secondary']};
                        border: none;
                        padding: 0;
                        font-size: 11px;
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        color: {c['text_primary']};
                    }}
                """)
            btn.clicked.connect(lambda checked=False, t=tag: self._add_tag(t))
            card_layout.addWidget(btn, 1)

            remove_btn = QPushButton("×")
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.setFixedSize(16, 16)
            remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {c['text_muted']};
                    border: none;
                    border-radius: 8px;
                    padding: 0;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {c['surface_2']};
                    color: {c['danger']};
                }}
            """)
            remove_btn.clicked.connect(lambda checked=False, t=tag: self._remove_suggestion_tag(t))
            card_layout.addWidget(remove_btn, 0, Qt.AlignmentFlag.AlignTop)

            row, col = divmod(index, 4)
            self._suggestions_layout.addWidget(card, row, col)

    def get_tags(self) -> List[str]:
        return normalize_tags(self._tags)

    def get_category(self) -> str:
        return self._category

    def get_status(self) -> str:
        return self._status

    def get_common_tags(self) -> List[str]:
        return normalize_tags(self._suggested_tags)


class DeadlineEditorDialog(QDialog):
    """期限编辑对话框"""

    TYPE_OPTIONS = [
        ("普通期限", "deadline"),
        ("开庭/庭前", "hearing"),
        ("自定义提醒", "custom"),
    ]

    PRIORITY_OPTIONS = [
        ("高", "high"),
        ("中", "medium"),
        ("低", "low"),
    ]

    def __init__(
        self,
        deadline: Optional[Dict[str, Any]] = None,
        parent=None,
        *,
        cases: Optional[List[Dict[str, Any]]] = None,
        selected_case_id: str = "",
    ):
        super().__init__(parent)
        self._deadline = deadline or {}
        self._cases = list(cases or [])
        self._selected_case_id = selected_case_id or str(self._deadline.get("case_id", ""))
        self._result: Optional[Dict[str, Any]] = None
        self._time_mode_user_changed = False
        self._case_search_model = QStringListModel(self)
        self._case_options: List[Dict[str, str]] = []
        self._case_combo: Optional[QComboBox] = None
        self._case_hint_label: Optional[QLabel] = None
        self._setup_ui()
        self._load_deadline()
        self._refresh_parse_preview()

    def _setup_ui(self) -> None:
        c = COLORS
        self.setWindowTitle("期限提醒")
        self.setMinimumSize(680, 500)
        self.resize(700, 500)
        self.setStyleSheet(f"""
            QDialog {{
                background: {c['surface_1']};
            }}
            QFrame#deadlineSmartCard, QFrame#deadlineFormCard {{
                background: {c['surface_0']};
                border: 1px solid rgba(226, 232, 240, 0.92);
                border-radius: 14px;
            }}
            QLabel#deadlineCardTitle {{
                background: transparent;
                color: {c['text_primary']};
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#deadlineCardHint {{
                background: transparent;
                color: {c['text_muted']};
                font-size: 10px;
                line-height: 1.5;
            }}
            QLabel#deadlineFieldLabel {{
                background: transparent;
                color: {c['text_secondary']};
                font-size: 11px;
                font-weight: 700;
            }}
            QFrame#deadlineInlineField {{
                background: {c['surface_1']};
                border: 1px solid rgba(226, 232, 240, 0.92);
                border-radius: 12px;
            }}
            QSplitter::handle {{
                background: transparent;
            }}
            QSplitter::handle:horizontal {{
                width: 12px;
            }}
            QLineEdit, QComboBox, QDateEdit, QTimeEdit, QTextEdit {{
                background: #ffffff;
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 9px;
                padding: 3px 10px;
                font-size: 12px;
                min-height: 26px;
            }}
            QComboBox::drop-down, QDateEdit::drop-down {{
                border: none;
                width: 26px;
                background: transparent;
            }}
            QComboBox#deadlineCaseCombo {{
                padding-right: 38px;
            }}
            QComboBox#deadlineCaseCombo::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 34px;
                background: {c['surface_1']};
                border-left: 1px solid {c['border']};
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                margin: 1px 1px 1px 0;
            }}
            QComboBox#deadlineCaseCombo::drop-down:hover {{
                background: {c['surface_2']};
                border-left-color: {c['accent_light']};
            }}
            QComboBox#deadlineCaseCombo::down-arrow {{
                image: url({DROPDOWN_ARROW_PATH});
                width: 10px;
                height: 6px;
            }}
            QTimeEdit::up-button, QTimeEdit::down-button {{
                subcontrol-origin: border;
                width: 17px;
                background: {c['surface_1']};
                border-left: 1px solid {c['border']};
                margin: 1px 1px 1px 0;
            }}
            QTimeEdit::up-button {{
                subcontrol-position: top right;
                border-top-right-radius: 8px;
                border-bottom: 1px solid {c['border']};
            }}
            QTimeEdit::down-button {{
                subcontrol-position: bottom right;
                border-bottom-right-radius: 8px;
            }}
            QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {{
                background: {c['surface_2']};
            }}
            QWidget#deadlineDateTimeField,
            QWidget#deadlineTypePriorityField,
            QWidget#deadlineRemindField,
            QWidget#deadlineRemindBlock {{
                background: transparent;
                border: none;
            }}
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QTextEdit:focus {{
                border-color: {c['accent']};
            }}
            QCheckBox {{
                background: transparent;
                color: {c['text_secondary']};
                font-size: 12px;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {c['border_strong']};
                border-radius: 5px;
                background: #ffffff;
            }}
            QCheckBox::indicator:checked {{
                background: {c['accent']};
                border-color: {c['accent']};
                image: url({CHECK_ICON_PATH});
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(3)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        smart_card = QFrame()
        smart_card.setObjectName("deadlineSmartCard")
        self._smart_card = smart_card
        smart_card.setMinimumWidth(210)
        smart_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        smart_layout = QVBoxLayout(smart_card)
        smart_layout.setContentsMargins(10, 10, 10, 10)
        smart_layout.setSpacing(6)

        self._smart_title = QLabel("智能识别")
        self._smart_title.setObjectName("deadlineCardTitle")
        self._smart_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        smart_layout.addWidget(self._smart_title)

        self._smart_hint_label = QLabel(
            "把整句话直接写进来，系统会优先拆出任务名称、日期、时间、类型和说明。地点、法院、案由等上下文会自动并入说明。"
        )
        self._smart_hint_label.setObjectName("deadlineCardHint")
        self._smart_hint_label.setWordWrap(True)
        self._smart_hint_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        smart_layout.addWidget(self._smart_hint_label)

        self._smart_input = QTextEdit()
        self._smart_input.setPlaceholderText(
            "例如：2024年3月14日上午9时30分在池州市贵池区人民法院开庭审理牛先生民间借贷纠纷案件"
        )
        self._smart_input.setMinimumHeight(88)
        self._smart_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        smart_layout.addWidget(self._smart_input, 2)

        self._smart_actions_widget = QWidget()
        self._smart_actions_widget.setFixedHeight(36)
        self._smart_actions_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        smart_actions = QHBoxLayout(self._smart_actions_widget)
        smart_actions.setContentsMargins(0, 0, 0, 0)
        smart_actions.setSpacing(8)

        self._btn_smart_recognize = QPushButton("智能识别")
        self._style_dialog_button(self._btn_smart_recognize, primary=True)
        self._btn_smart_recognize.clicked.connect(self._on_smart_recognize)
        smart_actions.addWidget(self._btn_smart_recognize)

        self._btn_clear_smart = QPushButton("清空")
        self._style_dialog_button(self._btn_clear_smart, primary=False)
        self._btn_clear_smart.clicked.connect(self._smart_input.clear)
        smart_actions.addWidget(self._btn_clear_smart)
        smart_actions.addStretch()
        smart_layout.addWidget(self._smart_actions_widget)

        self._smart_result_label = QLabel("识别后会自动填充下方字段，你仍然可以继续手动修正。")
        self._smart_result_label.setWordWrap(True)
        self._smart_result_label.setMinimumHeight(118)
        self._smart_result_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._smart_result_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._smart_result_label.setStyleSheet(f"""
            background: {c['surface_1']};
            color: {c['text_secondary']};
            border: none;
            border-radius: 10px;
            padding: 8px 10px;
            font-size: 11px;
            line-height: 1.6;
        """)
        smart_layout.addWidget(self._smart_result_label, 3)
        form_card = QFrame()
        form_card.setObjectName("deadlineFormCard")
        form_card.setMinimumWidth(360)
        form_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_card_layout = QVBoxLayout(form_card)
        form_card_layout.setContentsMargins(10, 10, 10, 10)
        form_card_layout.setSpacing(6)
        form_card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        form_header = QVBoxLayout()
        form_header.setContentsMargins(0, 0, 0, 0)
        form_header.setSpacing(3)

        form_title = QLabel("添加期限任务")
        form_title.setObjectName("deadlineCardTitle")
        form_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        form_header.addWidget(form_title)

        self._parse_result_label = QLabel("")
        self._parse_result_label.setWordWrap(True)
        self._parse_result_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._parse_result_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 11px;
            line-height: 1.5;
        """)
        form_header.addWidget(self._parse_result_label)
        form_card_layout.addLayout(form_header)

        from src.gui.widgets.transparent_form_layout import TransparentFormLayout
        form = TransparentFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(5)
        form.setHorizontalSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("例如：举证期限、开庭时间、补正截止日")
        self._title_edit.setFixedHeight(38)
        form.addRow("任务名称", self._title_edit)

        if self._cases:
            self._case_combo = QComboBox()
            self._case_combo.setObjectName("deadlineCaseCombo")
            self._case_combo.setEditable(True)
            self._case_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            self._case_combo.setMaxVisibleItems(12)
            self._case_combo.setFixedHeight(38)
            self._case_combo.currentIndexChanged.connect(self._select_case_from_combo)
            line_edit = self._case_combo.lineEdit()
            if line_edit:
                line_edit.setPlaceholderText("可留空；输入案件名、标签或字段内容搜索")
                line_edit.installEventFilter(self)
                line_edit.textEdited.connect(self._handle_case_search_input)
                line_edit.returnPressed.connect(self._commit_case_search_text)

            completer = QCompleter(self._case_search_model, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.activated[str].connect(self._select_case_from_text)
            self._case_combo.setCompleter(completer)
            self._rebuild_case_options()
            self._populate_case_combo(self._selected_case_id)
            form.addRow("关联案件", self._case_combo)
            self._case_hint_label = QLabel("可留空。点击输入框会清空当前匹配，直接搜索案件。")
            self._case_hint_label.setWordWrap(True)
            self._case_hint_label.setStyleSheet(f"""
                background: transparent;
                color: {c['text_muted']};
                font-size: 10px;
                line-height: 1.5;
            """)
            form.addRow("", self._case_hint_label)

        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-M-d")
        self._date_edit.setDate(QDate.currentDate())
        self._date_edit.setFixedHeight(36)
        self._date_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._date_edit.dateChanged.connect(self._refresh_parse_preview)
        self._date_popup: Optional[QDialog] = None

        time_wrap = QWidget()
        time_wrap.setObjectName("deadlineDateTimeField")
        time_wrap_layout = QVBoxLayout()
        time_wrap_layout.setSpacing(5)
        time_wrap_layout.setContentsMargins(0, 0, 0, 0)
        time_wrap.setLayout(time_wrap_layout)
        time_wrap.setMinimumHeight(77)
        time_wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        date_row = QHBoxLayout()
        date_row.setSpacing(5)
        date_row.setContentsMargins(0, 0, 0, 0)
        self._date_edit.setToolTip("日期")
        date_row.addWidget(self._date_edit, 1)

        self._btn_pick_date = QPushButton("选择")
        self._btn_pick_date.setToolTip("选择日期")
        self._btn_pick_date.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_pick_date.setFixedSize(52, 36)
        self._style_icon_button(self._btn_pick_date)
        self._btn_pick_date.clicked.connect(self._show_date_popup)
        date_row.addWidget(self._btn_pick_date, 0)
        time_wrap_layout.addLayout(date_row)

        time_row = QHBoxLayout()
        time_row.setSpacing(5)
        time_row.setContentsMargins(0, 0, 0, 0)

        self._time_edit = QTimeEdit()
        self._time_edit.setDisplayFormat("HH:mm")
        self._time_edit.setTime(QTime(9, 0))
        self._time_edit.setFixedHeight(36)
        self._time_edit.setMinimumWidth(84)
        self._time_edit.setMaximumWidth(92)
        self._time_edit.setToolTip("时间")
        self._time_edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._time_edit.timeChanged.connect(self._on_time_changed)
        time_row.addWidget(self._time_edit, 0)

        self._all_day_checkbox = QPushButton("全天任务")
        self._all_day_checkbox.setCheckable(True)
        self._all_day_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self._all_day_checkbox.setFixedWidth(78)
        self._style_time_mode_button(self._all_day_checkbox)
        self._all_day_checkbox.setChecked(True)
        self._all_day_checkbox.toggled.connect(self._on_all_day_toggled)
        time_row.addWidget(self._all_day_checkbox)
        time_row.addStretch(1)
        time_wrap_layout.addLayout(time_row)

        self._type_combo = QComboBox()
        for label, value in self.TYPE_OPTIONS:
            self._type_combo.addItem(label, value)
        self._type_combo.setFixedHeight(36)
        self._type_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)

        self._priority_combo = QComboBox()
        for label, value in self.PRIORITY_OPTIONS:
            self._priority_combo.addItem(label, value)
        self._priority_combo.setFixedHeight(36)
        self._priority_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        type_priority_wrap = QWidget()
        type_priority_wrap.setObjectName("deadlineTypePriorityField")
        type_priority_layout = QHBoxLayout(type_priority_wrap)
        type_priority_layout.setContentsMargins(0, 0, 0, 0)
        type_priority_layout.setSpacing(8)
        type_priority_layout.addWidget(self._type_combo, 3)
        type_priority_layout.addWidget(self._priority_combo, 1)

        self._remind_edit = QLineEdit()
        self._remind_edit.setPlaceholderText("")
        self._remind_edit.setFixedHeight(36)
        self._remind_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        remind_wrap = QWidget()
        remind_wrap.setObjectName("deadlineRemindField")
        remind_layout = QVBoxLayout(remind_wrap)
        remind_layout.setContentsMargins(0, 0, 0, 0)
        remind_layout.setSpacing(0)
        remind_layout.addWidget(self._remind_edit)

        self._description_edit = QTextEdit()
        self._description_edit.setPlaceholderText("补充记录依据、地点、注意事项等")
        self._description_edit.setMinimumHeight(96)
        self._description_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        remind_hint_label = QLabel("留空表示不提醒。可输入 7,3,1,0，表示提前 7 天、3 天、1 天和当天提醒。")
        remind_hint_label.setWordWrap(True)
        remind_hint_label.setStyleSheet(f"""
            background: transparent;
            color: {c['text_muted']};
            font-size: 10px;
            line-height: 1.45;
        """)
        remind_block = QWidget()
        remind_block.setObjectName("deadlineRemindBlock")
        remind_block_layout = QVBoxLayout(remind_block)
        remind_block_layout.setContentsMargins(0, 0, 0, 0)
        remind_block_layout.setSpacing(3)
        remind_block_layout.addWidget(remind_hint_label)
        remind_block_layout.addWidget(remind_wrap)

        form.addRow("时间", time_wrap)
        form.addRow("类型 / 优先级", type_priority_wrap)
        form.addRow("提前提醒", remind_block)
        form.addRow("详细内容", self._description_edit)
        form_card_layout.addLayout(form, 1)

        self._cards_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._cards_splitter.setObjectName("deadlineCardsSplitter")
        self._cards_splitter.setChildrenCollapsible(False)
        self._cards_splitter.setHandleWidth(12)
        self._cards_splitter.addWidget(smart_card)
        self._cards_splitter.addWidget(form_card)
        self._cards_splitter.setStretchFactor(0, 4)
        self._cards_splitter.setStretchFactor(1, 5)
        self._cards_splitter.setSizes([280, 392])
        content_layout.addWidget(self._cards_splitter)
        layout.addWidget(content, 1)

        button_bar = QHBoxLayout()

        # 删除按钮（仅在编辑已有期限时显示，置于最左侧）
        has_deadline_id = bool(str(self._deadline.get("id", "")).strip())
        if has_deadline_id:
            delete_btn = QPushButton("删除")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._style_delete_button(delete_btn)
            delete_btn.clicked.connect(self._on_delete)
            button_bar.addWidget(delete_btn)

        button_bar.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button:
            ok_button.setText("保存期限")
            self._style_dialog_button(ok_button, primary=True)
        if cancel_button:
            cancel_button.setText("取消")
            self._style_dialog_button(cancel_button, primary=False)
        button_bar.addWidget(buttons)
        layout.addLayout(button_bar)

        self._set_time_mode("all_day", refresh=False)
        self._refresh_smart_panel_metrics()
        self._resize_smart_fields()

    def _style_dialog_button(self, button: QPushButton, primary: bool) -> None:
        c = COLORS
        if primary:
            button.setStyleSheet(f"""
                QPushButton {{
                    background: {c['accent']};
                    color: white;
                    border: none;
                    border-radius: 9px;
                    padding: 0 14px;
                    min-height: 32px;
                    font-size: 12px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {c['accent_hover']};
                }}
            """)
            return

        button.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 9px;
                padding: 0 14px;
                min-height: 32px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
            }}
        """)

    def _on_delete(self) -> None:
        """删除当前期限任务（无二次确认）。"""
        self._result = {"deleted": True, "id": str(self._deadline.get("id", "")).strip()}
        self.accept()

    def _style_delete_button(self, button: QPushButton) -> None:
        c = COLORS
        button.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: #ef4444;
                border: 1px solid #fca5a5;
                border-radius: 9px;
                padding: 0 14px;
                min-height: 32px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #fee2e2;
                color: #dc2626;
                border-color: #f87171;
            }}
        """)

    def _style_time_mode_button(self, button: QPushButton) -> None:
        c = COLORS
        button.setFixedHeight(36)
        button.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 9px;
                padding: 0 11px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['text_primary']};
                border-color: {c['border_strong']};
            }}
            QPushButton:checked {{
                background: {c['accent_subtle']};
                color: {c['accent']};
                border: 1px solid {c['accent_light']};
            }}
        """)

    def _style_icon_button(self, button: QPushButton) -> None:
        c = COLORS
        button.setStyleSheet(f"""
            QPushButton {{
                background: {c['surface_0']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 9px;
                padding: 0;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {c['surface_2']};
                color: {c['accent']};
                border-color: {c['accent_light']};
            }}
            QPushButton:pressed {{
                background: {c['accent_subtle']};
                color: {c['accent']};
            }}
        """)

    def _show_date_popup(self) -> None:
        if self._date_popup is not None and self._date_popup.isVisible():
            self._date_popup.close()
            return

        popup = QDialog(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        popup.setObjectName("deadlineDatePopup")
        popup.setStyleSheet(f"""
            QDialog#deadlineDatePopup {{
                background: {COLORS['surface_0']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
            QCalendarWidget {{
                background: {COLORS['surface_0']};
                color: {COLORS['text_primary']};
                border: none;
            }}
        """)
        popup_layout = QVBoxLayout(popup)
        popup_layout.setContentsMargins(8, 8, 8, 8)
        calendar = QCalendarWidget(popup)
        calendar.setSelectedDate(self._date_edit.date())
        calendar.setGridVisible(False)
        calendar.clicked.connect(lambda date: self._apply_popup_date(popup, date))
        popup_layout.addWidget(calendar)

        button_bottom_left = self._btn_pick_date.mapToGlobal(self._btn_pick_date.rect().bottomLeft())
        popup.move(button_bottom_left)
        popup.resize(320, 250)
        self._date_popup = popup
        popup.show()

    def _apply_popup_date(self, popup: QDialog, date: QDate) -> None:
        self._date_edit.setDate(date)
        popup.close()

    def _create_inline_field(
        self,
        title: str,
        widget: QWidget,
        hint: str = "",
        *,
        expand_body: bool = False,
    ) -> QFrame:
        field = QFrame()
        field.setObjectName("deadlineInlineField")
        field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(field)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        label = QLabel(title)
        label.setObjectName("deadlineFieldLabel")
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout.addWidget(label)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("deadlineCardHint")
            hint_label.setWordWrap(True)
            hint_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
            layout.addWidget(hint_label)

        layout.addWidget(widget, 1 if expand_body else 0)
        return field

    def _load_deadline(self) -> None:
        if not self._deadline:
            self._priority_combo.setCurrentIndex(1)
            self._remind_edit.clear()
            self._set_time_mode("all_day", refresh=False)
            if self._case_combo and self._selected_case_id:
                self._populate_case_combo(self._selected_case_id)
            return

        self._time_mode_user_changed = True
        self._title_edit.setText(str(self._deadline.get("title", "")))
        if self._case_combo:
            case_id = self._selected_case_id or str(self._deadline.get("case_id", ""))
            self._populate_case_combo(case_id)
        date_text = str(self._deadline.get("date", "")).strip()
        if date_text:
            date_value = QDate.fromString(date_text, "yyyy-MM-dd")
            if date_value.isValid():
                self._date_edit.setDate(date_value)

        time_text = str(self._deadline.get("time", "")).strip()
        all_day = bool(self._deadline.get("all_day", not bool(time_text)))
        if time_text:
            time_value = QTime.fromString(time_text, "HH:mm")
            if time_value.isValid():
                self._time_edit.setTime(time_value)
            self._set_time_mode("specific", refresh=False)
        else:
            self._set_time_mode("all_day" if all_day else "specific", refresh=False)

        self._select_combo_value(self._type_combo, str(self._deadline.get("type", "deadline")))
        self._select_combo_value(self._priority_combo, str(self._deadline.get("priority", "medium")))

        remind_before = self._deadline.get("remind_before", [])
        if isinstance(remind_before, list) and remind_before:
            self._remind_edit.setText(",".join(str(item) for item in remind_before))
        else:
            self._remind_edit.clear()

        self._description_edit.setPlainText(str(self._deadline.get("description", "")))

    def _select_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def eventFilter(self, watched, event):  # type: ignore[override]
        case_combo = getattr(self, "_case_combo", None)
        line_edit = case_combo.lineEdit() if case_combo else None
        if line_edit and watched is line_edit and event.type() == QEvent.Type.MouseButtonPress:
            self._begin_case_search()
        return super().eventFilter(watched, event)

    def _rebuild_case_options(self) -> None:
        self._case_options = []
        for case in self._cases:
            case_id = str(case.get("id", "")).strip()
            if not case_id:
                continue
            name = str(case.get("name", "")).strip() or "未命名案件"
            search_terms = [name, str(case.get("category", "")).strip(), " ".join(case.get("tags", []) or [])]
            for field in case.get("info_fields", []) or []:
                search_terms.append(str(field.get("label", "")).strip())
                search_terms.append(str(field.get("value", "")).strip())
            for value in (case.get("variables", {}) or {}).values():
                search_terms.append(str(value).strip())
            self._case_options.append({
                "case_id": case_id,
                "display": name,
                "search": " ".join(item for item in search_terms if item),
            })

    def _populate_case_combo(self, selected_case_id: str = "") -> None:
        if not self._case_combo:
            return
        self._case_combo.blockSignals(True)
        self._case_combo.clear()
        self._case_combo.addItem("不关联案件（仅在日历中管理）", "")
        completion_items = []
        for option in self._case_options:
            self._case_combo.addItem(option["display"], option["case_id"])
            completion_items.append(option["display"])
        index = self._case_combo.findData(selected_case_id)
        self._case_combo.setCurrentIndex(index if index >= 0 else 0)
        self._case_combo.blockSignals(False)
        self._selected_case_id = selected_case_id if index >= 0 else ""
        self._case_search_model.setStringList(completion_items)
        self._refresh_case_hint()

    def _begin_case_search(self) -> None:
        if not self._case_combo:
            return
        line_edit = self._case_combo.lineEdit()
        self._case_combo.blockSignals(True)
        self._case_combo.setCurrentIndex(-1)
        self._case_combo.blockSignals(False)
        self._selected_case_id = ""
        if line_edit:
            line_edit.clear()
            line_edit.setFocus()
        self._refresh_case_hint()

    def _handle_case_search_input(self, text: str) -> None:
        if not self._case_combo:
            return
        normalized = text.strip()
        completer = self._case_combo.completer()
        filtered = [
            option["display"]
            for option in self._case_options
            if normalized.lower() in option["display"].lower()
            or normalized.lower() in option["search"].lower()
        ] if normalized else [option["display"] for option in self._case_options]
        self._case_search_model.setStringList(filtered)
        if completer and normalized:
            completer.setCompletionPrefix(normalized)
            completer.complete()
        self._refresh_case_hint(search_text=normalized, match_count=len(filtered))

    def _commit_case_search_text(self) -> None:
        if not self._case_combo or not self._case_combo.lineEdit():
            return
        self._select_case_from_text(self._case_combo.lineEdit().text().strip())

    def _select_case_from_combo(self) -> None:
        if not self._case_combo:
            return
        self._selected_case_id = str(self._case_combo.currentData() or "").strip()
        self._refresh_case_hint()

    def _select_case_from_text(self, text: str) -> None:
        if not self._case_combo:
            return
        display_text = str(text or "").strip()
        if not display_text:
            self._case_combo.setCurrentIndex(0)
            self._selected_case_id = ""
            self._refresh_case_hint()
            return

        index = self._case_combo.findText(display_text, Qt.MatchFlag.MatchExactly)
        if index < 0:
            match_option = next(
                (
                    option
                    for option in self._case_options
                    if display_text.lower() in option["display"].lower()
                    or display_text.lower() in option["search"].lower()
                ),
                None,
            )
            if match_option:
                index = self._case_combo.findData(match_option["case_id"])
        if index >= 0:
            self._case_combo.setCurrentIndex(index)
            self._selected_case_id = str(self._case_combo.itemData(index) or "").strip()
        self._refresh_case_hint()

    def _resolve_current_case_selection(self) -> str:
        if not self._case_combo:
            return self._selected_case_id
        current_case_id = str(self._case_combo.currentData() or "").strip()
        if current_case_id:
            self._selected_case_id = current_case_id
            return current_case_id

        line_edit = self._case_combo.lineEdit()
        search_text = line_edit.text().strip() if line_edit else ""
        if not search_text:
            self._selected_case_id = ""
            return ""

        match_option = next(
            (
                option
                for option in self._case_options
                if search_text.lower() in option["display"].lower()
                or search_text.lower() in option["search"].lower()
            ),
            None,
        )
        if not match_option:
            self._selected_case_id = ""
            return ""

        self._selected_case_id = match_option["case_id"]
        combo_index = self._case_combo.findData(self._selected_case_id)
        if combo_index >= 0:
            self._case_combo.setCurrentIndex(combo_index)
        return self._selected_case_id

    def _refresh_case_hint(self, search_text: str = "", match_count: Optional[int] = None) -> None:
        if not self._case_hint_label:
            return
        if search_text:
            self._case_hint_label.setText(
                f"正在搜索“{search_text}”，匹配到 {match_count or 0} 个案件。回车可自动选中最接近的案件，也可以保持留空。"
            )
            return
        if self._selected_case_id:
            matched_case = next((item for item in self._case_options if item["case_id"] == self._selected_case_id), None)
            if matched_case:
                self._case_hint_label.setText(f"当前已关联：{matched_case['display']}。点击输入框可重新搜索，留空则改为仅在日历中管理。")
                return
        self._case_hint_label.setText("可留空。点击输入框会清空当前匹配，直接搜索案件。")

    def _set_time_mode(self, mode: str, *, refresh: bool = True, user_initiated: bool = False) -> None:
        specific = mode == "specific"
        all_day = mode != "specific"

        self._all_day_checkbox.blockSignals(True)
        self._all_day_checkbox.setChecked(all_day)
        self._all_day_checkbox.blockSignals(False)
        self._time_edit.setEnabled(True)

        if specific and self._time_edit.time() == QTime(0, 0):
            self._time_edit.setTime(QTime(9, 0))
        if user_initiated:
            self._time_mode_user_changed = True
        if refresh:
            self._refresh_parse_preview()

    def _on_all_day_toggled(self, checked: bool) -> None:
        self._set_time_mode("all_day" if checked else "specific", user_initiated=True)

    def _on_time_changed(self) -> None:
        if self._all_day_checkbox.isChecked():
            self._set_time_mode("specific", refresh=False)
        self._refresh_parse_preview()

    def _on_type_changed(self) -> None:
        if (
            self._type_combo.currentData() == "hearing"
            and self._all_day_checkbox.isChecked()
            and not self._time_mode_user_changed
        ):
            self._time_edit.setTime(QTime(9, 0))
            self._set_time_mode("specific", refresh=False)
        self._refresh_parse_preview()

    def _get_default_time_policy(self) -> Dict[str, Any]:
        if self._type_combo.currentData() == "hearing":
            return {"default_time": "09:00", "default_all_day": False}
        return {"default_time": "", "default_all_day": True}

    def _refresh_parse_preview(self) -> None:
        parsed = self._build_result_from_controls()
        type_text = self._type_combo.currentText()
        time_text = "全天任务" if parsed["all_day"] else f"指定时分 {parsed['time']}"
        self._parse_result_label.setText(
            f"当前将保存为：{parsed['date']} · {time_text} · {type_text}"
        )

    def _build_result_from_controls(self) -> Dict[str, Any]:
        date_text = self._date_edit.date().toString("yyyy-MM-dd")
        if self._all_day_checkbox.isChecked():
            return {"date": date_text, "time": "", "all_day": True}
        return {"date": date_text, "time": self._time_edit.time().toString("HH:mm"), "all_day": False}

    def _render_smart_result(self, parsed: Dict[str, Any]) -> None:
        description = str(parsed.get("description", "")).strip() or "无额外说明，地点等上下文未单独提取。"
        self._smart_result_label.setText(
            "识别完成："
            f"\n任务名称：{parsed.get('title', '')}"
            f"\n时间：{parsed.get('display_text', '')}"
            f"\n类型：{parsed.get('type_label', '')}"
            f"\n说明：{description}"
        )
        self._refresh_smart_panel_metrics()

    def _apply_smart_result(self, parsed: Dict[str, Any]) -> None:
        self._title_edit.setText(str(parsed.get("title", "")))

        date_value = QDate.fromString(str(parsed.get("date", "")), "yyyy-MM-dd")
        if date_value.isValid():
            self._date_edit.setDate(date_value)

        if parsed.get("all_day", True):
            self._set_time_mode("all_day", refresh=False)
        else:
            time_value = QTime.fromString(str(parsed.get("time", "")), "HH:mm")
            if time_value.isValid():
                self._time_edit.setTime(time_value)
            self._set_time_mode("specific", refresh=False)

        self._select_combo_value(self._type_combo, str(parsed.get("type", "deadline")))
        self._select_combo_value(self._priority_combo, str(parsed.get("priority", "medium")))
        self._description_edit.setPlainText(str(parsed.get("description", "")).strip())
        self._time_mode_user_changed = True
        self._refresh_parse_preview()

    def _on_smart_recognize(self) -> None:
        smart_text = self._smart_input.toPlainText().strip()
        if not smart_text:
            QMessageBox.information(self, "请输入事项", "请先输入一句完整的事项描述，再点击“智能识别”。")
            return

        try:
            parsed = parse_deadline_smart_input_text(smart_text)
        except ValueError as exc:
            self._smart_result_label.setText(f"识别失败：{exc}")
            return

        self._render_smart_result(parsed)
        self._apply_smart_result(parsed)

    def _refresh_smart_panel_metrics(self) -> None:
        self._smart_hint_label.setFixedHeight(64)

    def _resize_smart_fields(self) -> None:
        card_height = self._smart_card.height()
        if card_height <= 0:
            return

        margins = self._smart_card.layout().contentsMargins()
        spacing = self._smart_card.layout().spacing()
        fixed_height = (
            self._smart_title.sizeHint().height()
            + self._smart_hint_label.height()
            + self._smart_actions_widget.sizeHint().height()
        )
        available = card_height - margins.top() - margins.bottom() - fixed_height - spacing * 4
        available = max(88 + 118, available)

        input_height = max(88, int(available * 0.42))
        result_height = max(118, available - input_height)
        self._smart_input.setFixedHeight(input_height)
        self._smart_result_label.setFixedHeight(result_height)

    def _fit_wrapped_label_height(self, label: QLabel, *, minimum: int, maximum: int) -> None:
        width = max(label.width(), 160)
        height = label.heightForWidth(width)
        if height <= 0:
            height = label.sizeHint().height()
        clamped_height = max(minimum, min(height + 12, maximum))
        label.setFixedHeight(clamped_height)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._refresh_smart_panel_metrics()
        self._resize_smart_fields()
        QTimer.singleShot(0, self._resize_smart_fields)

    def _parse_remind_days(self) -> List[int]:
        raw_text = self._remind_edit.text().strip()
        if not raw_text:
            return []

        result = []
        seen = set()
        for part in raw_text.split(","):
            item = part.strip()
            if not item:
                continue
            if not item.isdigit():
                raise ValueError("提前提醒必须是逗号分隔的非负整数")
            value = int(item)
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        result.sort(reverse=True)
        return result

    def _on_accept(self) -> None:
        title = self._title_edit.text().strip()
        if not title and self._smart_input.toPlainText().strip():
            try:
                parsed = parse_deadline_smart_input_text(self._smart_input.toPlainText().strip())
            except ValueError:
                parsed = None
            if parsed:
                self._apply_smart_result(parsed)
                title = self._title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "任务名称为空", "请输入任务名称。")
            return
        self._resolve_current_case_selection()

        try:
            remind_before = self._parse_remind_days()
        except ValueError as exc:
            QMessageBox.warning(self, "提醒格式错误", str(exc))
            return

        parsed_result = self._build_result_from_controls()

        self._result = {
            "title": title,
            "date": parsed_result["date"],
            "time": parsed_result["time"],
            "all_day": parsed_result["all_day"],
            "type": self._type_combo.currentData(),
            "priority": self._priority_combo.currentData(),
            "remind_before": remind_before,
            "description": self._description_edit.toPlainText().strip(),
            "status": self._deadline.get("status", "pending"),
            "completed_at": self._deadline.get("completed_at", ""),
        }
        self.accept()

    def get_deadline_data(self) -> Optional[Dict[str, Any]]:
        return self._result

    def get_selected_case_id(self) -> str:
        """返回当前选择的案件 ID。"""
        if self._case_combo is not None:
            return self._resolve_current_case_selection()
        return self._selected_case_id


class CaseInfoEditorDialog(QDialog):
    """案件信息编辑对话框。"""

    FIELD_TYPES = [
        ("文本", "text"),
        ("日期", "date"),
        ("日期时间", "datetime"),
        ("金额", "money"),
        ("单选", "single_select"),
        ("多选", "multi_select"),
        ("电话", "phone"),
        ("备注", "long_text"),
    ]

    def __init__(self, current_fields: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self._current_fields = current_fields
        self._result: Optional[List[Dict[str, Any]]] = None
        self._setup_ui()
        self._load_fields()

    def _setup_ui(self) -> None:
        c = COLORS
        self.setWindowTitle("编辑案件信息")
        self.setMinimumSize(820, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        hint = QLabel("核心字段会长期保留，自定义字段可随案件扩展。勾选“映射标签”后可把字段值用于筛选。")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px;")
        layout.addWidget(hint)

        tools = QHBoxLayout()
        tools.setSpacing(8)

        add_btn = QPushButton("+ 添加字段")
        add_btn.clicked.connect(self._add_custom_row)
        tools.addWidget(add_btn)

        remove_btn = QPushButton("删除选中字段")
        remove_btn.clicked.connect(self._remove_selected_rows)
        tools.addWidget(remove_btn)
        tools.addStretch()
        layout.addLayout(tools)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["字段名", "值", "类型", "映射标签"])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_fields(self) -> None:
        fields_by_key = {
            str(field.get("key", "")): field for field in self._current_fields if isinstance(field, dict)
        }

        for definition in CORE_INFO_FIELD_DEFINITIONS:
            field = fields_by_key.pop(definition["key"], {
                "id": f"builtin_{definition['key']}",
                "key": definition["key"],
                "label": definition["label"],
                "value": "",
                "type": definition["type"],
                "builtin": True,
                "map_to_tag": False,
            })
            self._append_row(field, builtin=True)

        for field in self._current_fields:
            if str(field.get("key", "")) in {item["key"] for item in CORE_INFO_FIELD_DEFINITIONS}:
                continue
            self._append_row(field, builtin=False)

    def _append_row(self, field: Dict[str, Any], builtin: bool) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        label_item = QTableWidgetItem(str(field.get("label", "")).strip())
        label_item.setData(Qt.ItemDataRole.UserRole, str(field.get("id", "")) or f"field_{uuid.uuid4().hex[:8]}")
        label_item.setData(Qt.ItemDataRole.UserRole + 1, str(field.get("key", "")))
        label_item.setData(Qt.ItemDataRole.UserRole + 2, builtin)
        if builtin:
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, 0, label_item)

        value_item = QTableWidgetItem(str(field.get("value", "")).strip())
        self._table.setItem(row, 1, value_item)

        combo = QComboBox()
        for label, value in self.FIELD_TYPES:
            combo.addItem(label, value)
        index = combo.findData(str(field.get("type", "text")).strip() or "text")
        if index >= 0:
            combo.setCurrentIndex(index)
        self._table.setCellWidget(row, 2, combo)

        checkbox = QCheckBox()
        checkbox.setChecked(bool(field.get("map_to_tag", False)))
        checkbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        container = QWidget()
        wrapper = QHBoxLayout(container)
        wrapper.setContentsMargins(8, 0, 8, 0)
        wrapper.addStretch()
        wrapper.addWidget(checkbox)
        wrapper.addStretch()
        self._table.setCellWidget(row, 3, container)

    def _add_custom_row(self) -> None:
        self._append_row({
            "id": f"field_{uuid.uuid4().hex[:8]}",
            "key": "",
            "label": "",
            "value": "",
            "type": "text",
            "builtin": False,
            "map_to_tag": False,
        }, builtin=False)
        self._table.setCurrentCell(self._table.rowCount() - 1, 0)

    def _remove_selected_rows(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return

        label_item = self._table.item(row, 0)
        if label_item and bool(label_item.data(Qt.ItemDataRole.UserRole + 2)):
            QMessageBox.information(self, "不能删除", "核心字段会长期保留，可保留为空。")
            return

        self._table.removeRow(row)

    def _get_checkbox_value(self, row: int) -> bool:
        container = self._table.cellWidget(row, 3)
        if not container:
            return False
        checkbox = container.findChild(QCheckBox)
        return bool(checkbox and checkbox.isChecked())

    def _on_accept(self) -> None:
        result: List[Dict[str, Any]] = []

        for row in range(self._table.rowCount()):
            label_item = self._table.item(row, 0)
            value_item = self._table.item(row, 1)
            combo = self._table.cellWidget(row, 2)

            if label_item is None or value_item is None or combo is None:
                continue

            label = label_item.text().strip()
            builtin = bool(label_item.data(Qt.ItemDataRole.UserRole + 2))
            key = str(label_item.data(Qt.ItemDataRole.UserRole + 1) or "").strip()
            if not label:
                if builtin:
                    label = str(next(
                        (item["label"] for item in CORE_INFO_FIELD_DEFINITIONS if item["key"] == key),
                        "",
                    ))
                else:
                    continue

            combo_widget = combo if isinstance(combo, QComboBox) else None
            field_type = combo_widget.currentData() if combo_widget else "text"
            if builtin and key in {item["key"] for item in CORE_INFO_FIELD_DEFINITIONS}:
                key_value = key
            else:
                key_value = key or f"custom_{uuid.uuid4().hex[:6]}"

            result.append({
                "id": str(label_item.data(Qt.ItemDataRole.UserRole) or f"field_{uuid.uuid4().hex[:8]}"),
                "key": key_value,
                "label": label,
                "value": value_item.text().strip(),
                "type": field_type,
                "builtin": builtin,
                "map_to_tag": self._get_checkbox_value(row),
            })

        self._result = result
        self.accept()

    def get_info_fields(self) -> List[Dict[str, Any]]:
        return self._result or []
