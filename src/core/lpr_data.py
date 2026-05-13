# -*- coding: utf-8 -*-
"""LPR 贷款市场报价利率数据管理与查询。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from src.config.config_manager import get_config_manager


# 默认 LPR 历史数据（日期 -> {"1y": 年利率%, "5y": 年利率%}）
# 数据按日期降序排列，方便查找
default_lpr_history: List[Tuple[str, Dict[str, float]]] = [
    ("2026-04-20", {"1y": 3.00, "5y": 3.50}),
    ("2026-03-20", {"1y": 3.00, "5y": 3.50}),
    ("2026-02-24", {"1y": 3.00, "5y": 3.50}),
    ("2026-01-20", {"1y": 3.00, "5y": 3.50}),
    ("2025-12-22", {"1y": 3.00, "5y": 3.50}),
    ("2025-11-20", {"1y": 3.00, "5y": 3.50}),
    ("2025-10-20", {"1y": 3.00, "5y": 3.50}),
    ("2025-09-22", {"1y": 3.00, "5y": 3.50}),
    ("2025-08-20", {"1y": 3.00, "5y": 3.50}),
    ("2025-07-21", {"1y": 3.00, "5y": 3.50}),
    ("2025-06-20", {"1y": 3.00, "5y": 3.50}),
    ("2025-05-20", {"1y": 3.00, "5y": 3.50}),
    ("2025-04-21", {"1y": 3.10, "5y": 3.60}),
    ("2025-03-20", {"1y": 3.10, "5y": 3.60}),
    ("2025-02-20", {"1y": 3.10, "5y": 3.60}),
    ("2025-01-20", {"1y": 3.10, "5y": 3.60}),
    ("2024-12-20", {"1y": 3.10, "5y": 3.60}),
    ("2024-11-20", {"1y": 3.10, "5y": 3.60}),
    ("2024-10-21", {"1y": 3.10, "5y": 3.60}),
    ("2024-09-20", {"1y": 3.35, "5y": 3.85}),
    ("2024-08-20", {"1y": 3.35, "5y": 3.85}),
    ("2024-07-22", {"1y": 3.35, "5y": 3.85}),
    ("2024-06-20", {"1y": 3.45, "5y": 3.95}),
    ("2024-05-20", {"1y": 3.45, "5y": 3.95}),
    ("2024-04-22", {"1y": 3.45, "5y": 3.95}),
    ("2024-03-20", {"1y": 3.45, "5y": 3.95}),
    ("2024-02-20", {"1y": 3.45, "5y": 3.95}),
    ("2024-01-22", {"1y": 3.45, "5y": 4.20}),
    ("2023-12-20", {"1y": 3.45, "5y": 4.20}),
    ("2023-11-20", {"1y": 3.45, "5y": 4.20}),
    ("2023-10-20", {"1y": 3.45, "5y": 4.20}),
    ("2023-09-20", {"1y": 3.45, "5y": 4.20}),
    ("2023-08-21", {"1y": 3.45, "5y": 4.20}),
    ("2023-07-20", {"1y": 3.55, "5y": 4.20}),
    ("2023-06-20", {"1y": 3.55, "5y": 4.20}),
    ("2023-05-22", {"1y": 3.65, "5y": 4.30}),
    ("2023-04-20", {"1y": 3.65, "5y": 4.30}),
    ("2023-03-20", {"1y": 3.65, "5y": 4.30}),
    ("2023-02-20", {"1y": 3.65, "5y": 4.30}),
    ("2023-01-20", {"1y": 3.65, "5y": 4.30}),
    ("2022-12-20", {"1y": 3.65, "5y": 4.30}),
    ("2022-11-21", {"1y": 3.65, "5y": 4.30}),
    ("2022-10-20", {"1y": 3.65, "5y": 4.30}),
    ("2022-09-20", {"1y": 3.65, "5y": 4.30}),
    ("2022-08-22", {"1y": 3.65, "5y": 4.30}),
    ("2022-07-20", {"1y": 3.70, "5y": 4.45}),
    ("2022-06-20", {"1y": 3.70, "5y": 4.45}),
    ("2022-05-20", {"1y": 3.70, "5y": 4.45}),
    ("2022-04-20", {"1y": 3.70, "5y": 4.60}),
    ("2022-03-21", {"1y": 3.70, "5y": 4.60}),
    ("2022-02-21", {"1y": 3.70, "5y": 4.60}),
    ("2022-01-20", {"1y": 3.70, "5y": 4.60}),
    ("2021-12-20", {"1y": 3.80, "5y": 4.65}),
    ("2021-11-22", {"1y": 3.85, "5y": 4.65}),
    ("2021-10-20", {"1y": 3.85, "5y": 4.65}),
    ("2021-09-22", {"1y": 3.85, "5y": 4.65}),
    ("2021-08-20", {"1y": 3.85, "5y": 4.65}),
    ("2021-07-20", {"1y": 3.85, "5y": 4.65}),
    ("2021-06-21", {"1y": 3.85, "5y": 4.65}),
    ("2021-05-20", {"1y": 3.85, "5y": 4.65}),
    ("2021-04-20", {"1y": 3.85, "5y": 4.65}),
    ("2021-03-22", {"1y": 3.85, "5y": 4.65}),
    ("2021-02-22", {"1y": 3.85, "5y": 4.65}),
    ("2021-01-20", {"1y": 3.85, "5y": 4.65}),
    ("2020-12-21", {"1y": 3.85, "5y": 4.65}),
    ("2020-11-20", {"1y": 3.85, "5y": 4.65}),
    ("2020-10-20", {"1y": 3.85, "5y": 4.65}),
    ("2020-09-21", {"1y": 3.85, "5y": 4.65}),
    ("2020-08-20", {"1y": 3.85, "5y": 4.65}),
    ("2020-07-20", {"1y": 3.85, "5y": 4.65}),
    ("2020-06-22", {"1y": 3.85, "5y": 4.65}),
    ("2020-05-20", {"1y": 3.85, "5y": 4.65}),
    ("2020-04-20", {"1y": 3.85, "5y": 4.65}),
    ("2020-03-20", {"1y": 4.05, "5y": 4.75}),
    ("2020-02-20", {"1y": 4.05, "5y": 4.75}),
    ("2020-01-20", {"1y": 4.15, "5y": 4.80}),
    ("2019-12-20", {"1y": 4.15, "5y": 4.80}),
    ("2019-11-20", {"1y": 4.15, "5y": 4.80}),
    ("2019-10-21", {"1y": 4.20, "5y": 4.85}),
    ("2019-09-20", {"1y": 4.20, "5y": 4.85}),
    ("2019-08-20", {"1y": 4.25, "5y": 4.85}),
]


class LprDataManager:
    """LPR 数据管理器，支持默认数据 + 用户自定义扩展。"""

    _instance: Optional["LprDataManager"] = None

    def __new__(cls) -> "LprDataManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._config = get_config_manager()
        self._cache: Optional[List[Tuple[str, Dict[str, float]]]] = None

    def _load_data(self) -> List[Tuple[str, Dict[str, float]]]:
        """加载 LPR 数据（默认 + 用户自定义）。"""
        if self._cache is not None:
            return self._cache
        custom = self._config.get("tools.lpr_custom", []) or []
        # 合并默认数据和用户自定义数据
        merged = list(default_lpr_history)
        for item in custom:
            date_str = str(item.get("date", "")).strip()
            if not date_str:
                continue
            rates = {
                "1y": float(item.get("1y", 0) or 0),
                "5y": float(item.get("5y", 0) or 0),
            }
            # 如果日期已存在则覆盖，否则插入
            found = False
            for i, (d, _) in enumerate(merged):
                if d == date_str:
                    merged[i] = (date_str, rates)
                    found = True
                    break
            if not found:
                merged.append((date_str, rates))
        # 按日期降序排序
        merged.sort(key=lambda x: x[0], reverse=True)
        self._cache = merged
        return self._cache

    def clear_cache(self) -> None:
        """清除缓存，下次加载时重新读取。"""
        self._cache = None

    def all_records(self) -> List[Tuple[str, Dict[str, float]]]:
        """返回所有 LPR 记录（日期降序）。"""
        return list(self._load_data())

    def query(self, query_date: str, term: str = "1y") -> Optional[float]:
        """查询指定日期适用的 LPR 利率。

        Args:
            query_date: 查询日期，格式 "YYYY-MM-DD"
            term: "1y" 或 "5y"

        Returns:
            适用的年利率（%），如果无数据则返回 None
        """
        data = self._load_data()
        if not data:
            return None
        for date_str, rates in data:
            if query_date >= date_str:
                return rates.get(term)
        # 如果 query_date 早于最早记录，返回最早记录的值
        return data[-1][1].get(term)

    def segments(
        self,
        start_date: str,
        end_date: str,
        term: str = "1y",
    ) -> List[Tuple[str, str, float]]:
        """获取起止日期之间的 LPR 分段信息。

        Returns:
            [(段起始日期, 段结束日期, 段利率), ...]
        """
        data = self._load_data()
        if not data:
            return []

        # 收集在区间 [start_date, end_date] 内有影响的所有变更日期
        relevant_dates = [start_date]
        for date_str, _ in data:
            if start_date < date_str <= end_date:
                relevant_dates.append(date_str)
        relevant_dates = sorted(set(relevant_dates))

        segments: List[Tuple[str, str, float]] = []
        for i, seg_start in enumerate(relevant_dates):
            seg_end = relevant_dates[i + 1] if i + 1 < len(relevant_dates) else end_date
            rate = self.query(seg_start, term)
            if rate is not None:
                segments.append((seg_start, seg_end, rate))
        return segments

    def add_custom(self, date_str: str, rate_1y: float, rate_5y: float) -> bool:
        """添加用户自定义 LPR 记录。"""
        if not date_str:
            return False
        custom = list(self._config.get("tools.lpr_custom", []) or [])
        # 查找是否已存在
        found = False
        for item in custom:
            if str(item.get("date", "")) == date_str:
                item["1y"] = float(rate_1y)
                item["5y"] = float(rate_5y)
                found = True
                break
        if not found:
            custom.append({
                "date": date_str,
                "1y": float(rate_1y),
                "5y": float(rate_5y),
            })
        self._config.set("tools.lpr_custom", custom)
        self.clear_cache()
        return True

    def remove_custom(self, date_str: str) -> bool:
        """删除用户自定义 LPR 记录。"""
        custom = list(self._config.get("tools.lpr_custom", []) or [])
        original_len = len(custom)
        custom = [item for item in custom if str(item.get("date", "")) != date_str]
        if len(custom) == original_len:
            return False
        self._config.set("tools.lpr_custom", custom)
        self.clear_cache()
        return True


def get_lpr_manager() -> LprDataManager:
    """获取 LPR 数据管理器单例。"""
    return LprDataManager()


def apply_lpr_adjustment(
    base_rate: float,
    *,
    bp: float = 0,
    adjust_mode: str = "multiple",  # "multiple" | "add" | "float"
    adjust_value: float = 1.0,
) -> float:
    """应用 LPR 调整方式。

    Args:
        base_rate: 基础利率（%）
        bp: 基点（1BP = 0.01%）
        adjust_mode: 调整模式
            - "multiple": 倍数（如 1.5 表示上浮 50%）
            - "add": 加计（如 50 表示加计 50%）
            - "float": 浮动（如 0.5 表示上浮 0.5%）
        adjust_value: 调整值

    Returns:
        调整后的利率（%）
    """
    rate = base_rate + bp * 0.01
    if adjust_mode == "multiple":
        rate = rate * adjust_value
    elif adjust_mode == "add":
        rate = rate * (1 + adjust_value / 100)
    elif adjust_mode == "float":
        rate = rate + adjust_value
    return rate


def calculate_interest_days(
    start_date: str,
    end_date: str,
    *,
    include_start: bool = True,
    include_end: bool = True,
) -> int:
    """计算起止日期之间的天数。

    Args:
        start_date: 起始日期 "YYYY-MM-DD"
        end_date: 截止日期 "YYYY-MM-DD"
        include_start: 起始日期是否计算在内
        include_end: 截止日期是否计算在内
    """
    s = date.fromisoformat(start_date)
    e = date.fromisoformat(end_date)
    delta = (e - s).days
    if delta < 0:
        return 0
    # 基础天数（不含起止日期）
    base = max(delta - 1, 0)
    if include_start:
        base += 1
    if include_end:
        base += 1
    # 如果起止日期是同一天，特殊处理
    if delta == 0:
        if include_start and include_end:
            return 1
        elif include_start or include_end:
            return 1
        else:
            return 0
    return base


def calculate_lpr_interest(
    principal: float,
    start_date: str,
    end_date: str,
    *,
    term: str = "1y",
    day_basis: int = 365,
    include_start: bool = True,
    include_end: bool = True,
    lpr_mode: str = "segment",  # "segment" | "fixed"
    fixed_rate: float = 0.0,
    bp: float = 0,
    adjust_mode: str = "multiple",
    adjust_value: float = 1.0,
) -> Dict[str, Any]:
    """按 LPR 计算利息。

    Args:
        principal: 本金
        start_date: 起始日期
        end_date: 截止日期
        term: LPR 档次 "1y" 或 "5y"
        day_basis: 一年按 360 或 365 天
        include_start: 起始日期是否计算在内
        include_end: 截止日期是否计算在内
        lpr_mode: "segment" 分段LPR / "fixed" 指定LPR
        fixed_rate: 指定LPR模式下使用固定利率
        bp: 基点
        adjust_mode: 调整模式
        adjust_value: 调整值

    Returns:
        {
            "total_interest": Decimal,
            "total_days": int,
            "segments": [
                {"start": str, "end": str, "days": int, "rate": float, "interest": Decimal}
            ],
        }
    """
    from src.core.legal_toolkit import money, non_negative

    principal_dec = non_negative(principal)
    basis = Decimal(str(day_basis if day_basis > 0 else 365))

    total_days = calculate_interest_days(
        start_date, end_date,
        include_start=include_start, include_end=include_end,
    )

    if lpr_mode == "fixed":
        rate = apply_lpr_adjustment(fixed_rate, bp=bp, adjust_mode=adjust_mode, adjust_value=adjust_value)
        interest = money(principal_dec * Decimal(str(rate)) / Decimal("100") * Decimal(total_days) / basis)
        return {
            "total_interest": interest,
            "total_days": total_days,
            "segments": [{
                "start": start_date,
                "end": end_date,
                "days": total_days,
                "rate": rate,
                "interest": interest,
            }],
        }

    # 分段 LPR
    manager = get_lpr_manager()
    segs = manager.segments(start_date, end_date, term)
    if not segs:
        # 无 LPR 数据，尝试用固定利率回退
        if fixed_rate > 0:
            rate = apply_lpr_adjustment(fixed_rate, bp=bp, adjust_mode=adjust_mode, adjust_value=adjust_value)
            interest = money(principal_dec * Decimal(str(rate)) / Decimal("100") * Decimal(total_days) / basis)
            return {
                "total_interest": interest,
                "total_days": total_days,
                "segments": [{
                    "start": start_date,
                    "end": end_date,
                    "days": total_days,
                    "rate": rate,
                    "interest": interest,
                }],
            }
        return {
            "total_interest": money(Decimal("0")),
            "total_days": total_days,
            "segments": [],
        }

    result_segments = []
    total_interest = Decimal("0")

    for seg_start, seg_end, base_rate in segs:
        seg_days = calculate_interest_days(
            seg_start, seg_end,
            include_start=include_start if seg_start == start_date else True,
            include_end=include_end if seg_end == end_date else False,
        )
        if seg_days <= 0:
            continue
        rate = apply_lpr_adjustment(base_rate, bp=bp, adjust_mode=adjust_mode, adjust_value=adjust_value)
        interest = money(principal_dec * Decimal(str(rate)) / Decimal("100") * Decimal(seg_days) / basis)
        total_interest += interest
        result_segments.append({
            "start": seg_start,
            "end": seg_end,
            "days": seg_days,
            "rate": rate,
            "interest": interest,
        })

    return {
        "total_interest": money(total_interest),
        "total_days": total_days,
        "segments": result_segments,
    }
