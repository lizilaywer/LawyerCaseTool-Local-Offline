# -*- coding: utf-8 -*-
"""法律工具中心的核心计算逻辑。"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple


DOUBLE_DELAY_DAILY_RATE = Decimal("0.000175")

WORK_INJURY_ONE_TIME_SUBSIDY_MONTHS = {
    1: 27,
    2: 25,
    3: 23,
    4: 21,
    5: 18,
    6: 16,
    7: 13,
    8: 11,
    9: 9,
    10: 7,
}

WORK_INJURY_ALLOWANCE_RATES = {
    1: Decimal("0.90"),
    2: Decimal("0.85"),
    3: Decimal("0.80"),
    4: Decimal("0.75"),
    5: Decimal("0.70"),
    6: Decimal("0.60"),
}

PROCEDURAL_LIMIT_RULES: Dict[str, Dict[str, object]] = {
    "civil_first_ordinary": {"label": "民事一审普通程序", "months": 6, "note": "民诉法通常审限 6 个月。"},
    "civil_first_summary": {"label": "民事一审简易程序", "months": 3, "note": "民诉法简易程序通常审限 3 个月。"},
    "civil_second_judgment": {"label": "民事二审判决", "months": 3, "note": "民事二审案件通常 3 个月审结。"},
    "civil_second_order": {"label": "民事二审裁定", "days": 30, "note": "民事二审裁定案件通常 30 日。"},
    "admin_first": {"label": "行政一审", "months": 6, "note": "行政诉讼通常审限 6 个月。"},
    "admin_second": {"label": "行政二审", "months": 3, "note": "行政二审通常审限 3 个月。"},
    "criminal_first": {"label": "刑事一审（普通）", "months": 2, "note": "刑诉法通常 2 个月，至迟不超过 3 个月。"},
    "criminal_second": {"label": "刑事二审", "months": 2, "note": "刑事二审通常 2 个月。"},
    "execution_case": {"label": "执行案件（参考）", "months": 6, "note": "执行期限常见参考口径 6 个月。"},
}

COMMON_CIVIL_CAUSES: Dict[str, List[str]] = {
    "合同纠纷": [
        "买卖合同纠纷",
        "借款合同纠纷",
        "融资租赁合同纠纷",
        "承揽合同纠纷",
        "建设工程施工合同纠纷",
        "房屋租赁合同纠纷",
        "物业服务合同纠纷",
        "委托合同纠纷",
        "保管合同纠纷",
    ],
    "人格权与侵权": [
        "生命权、身体权、健康权纠纷",
        "名誉权纠纷",
        "隐私权、个人信息保护纠纷",
        "网络侵权责任纠纷",
        "教育机构责任纠纷",
        "产品责任纠纷",
        "机动车交通事故责任纠纷",
    ],
    "婚姻家事": [
        "离婚纠纷",
        "离婚后财产纠纷",
        "离婚后损害责任纠纷",
        "同居关系析产纠纷",
        "抚养费纠纷",
        "继承纠纷",
        "分家析产纠纷",
    ],
    "物权与不动产": [
        "所有权确认纠纷",
        "返还原物纠纷",
        "排除妨害纠纷",
        "相邻关系纠纷",
        "业主共有权纠纷",
        "建设用地使用权纠纷",
    ],
    "公司与商事": [
        "股东资格确认纠纷",
        "股东出资纠纷",
        "公司决议纠纷",
        "损害公司利益责任纠纷",
        "证券虚假陈述责任纠纷",
    ],
    "劳动争议": [
        "确认劳动关系纠纷",
        "追索劳动报酬纠纷",
        "违法解除劳动合同赔偿金纠纷",
        "竞业限制纠纷",
        "工伤保险待遇纠纷",
    ],
    "知识产权与竞争": [
        "著作权权属、侵权纠纷",
        "商标权侵权纠纷",
        "专利权侵权纠纷",
        "技术合同纠纷",
        "不正当竞争纠纷",
    ],
    "金融与执行衍生": [
        "金融借款合同纠纷",
        "保证保险合同纠纷",
        "票据追索权纠纷",
        "执行异议之诉",
        "案外人执行异议之诉",
    ],
}

LEGAL_REFERENCE_LINKS: List[Tuple[str, str]] = [
    ("国家法律法规数据库", "https://flk.npc.gov.cn/"),
    ("最高人民法院", "https://www.court.gov.cn/"),
    ("中国法院网", "https://www.chinacourt.org/"),
    ("人民法院在线服务", "https://www.rmfyss.cn/"),
    ("中国裁判文书网", "https://wenshu.court.gov.cn/"),
    ("中国执行信息公开网", "http://zxgk.court.gov.cn/"),
    ("中国庭审公开网", "http://tingshen.court.gov.cn/"),
    ("全国企业破产重整案件信息网", "https://pccz.court.gov.cn/pcajxxw/index/xxwsy"),
    ("人力资源和社会保障部", "https://www.mohrss.gov.cn/"),
    ("国家统计局", "https://www.stats.gov.cn/"),
]


def _d(value: float | int | str | Decimal) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def money(value: float | int | str | Decimal) -> Decimal:
    return _d(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def non_negative(value: float | int | str | Decimal) -> Decimal:
    return max(Decimal("0"), _d(value))


def calculate_property_litigation_fee(amount: float | int | str) -> Decimal:
    """财产案件诉讼费。"""
    amt = non_negative(amount)
    if amt <= Decimal("10000"):
        return money("50")
    if amt <= Decimal("100000"):
        return money(Decimal("50") + (amt - Decimal("10000")) * Decimal("0.025"))
    if amt <= Decimal("200000"):
        return money(Decimal("2300") + (amt - Decimal("100000")) * Decimal("0.02"))
    if amt <= Decimal("500000"):
        return money(Decimal("4300") + (amt - Decimal("200000")) * Decimal("0.015"))
    if amt <= Decimal("1000000"):
        return money(Decimal("8800") + (amt - Decimal("500000")) * Decimal("0.01"))
    if amt <= Decimal("2000000"):
        return money(Decimal("13800") + (amt - Decimal("1000000")) * Decimal("0.009"))
    if amt <= Decimal("5000000"):
        return money(Decimal("22800") + (amt - Decimal("2000000")) * Decimal("0.008"))
    if amt <= Decimal("10000000"):
        return money(Decimal("46800") + (amt - Decimal("5000000")) * Decimal("0.007"))
    if amt <= Decimal("20000000"):
        return money(Decimal("81800") + (amt - Decimal("10000000")) * Decimal("0.006"))
    return money(Decimal("141800") + (amt - Decimal("20000000")) * Decimal("0.005"))


def calculate_divorce_litigation_fee(base_fee: float | int | str, property_amount: float | int | str) -> Decimal:
    """离婚案件诉讼费参考。"""
    property_value = non_negative(property_amount)
    excess = max(Decimal("0"), property_value - Decimal("200000"))
    return money(non_negative(base_fee) + excess * Decimal("0.005"))


def calculate_personality_litigation_fee(
    base_fee: float | int | str,
    compensation_amount: float | int | str,
) -> Decimal:
    """人格权纠纷诉讼费参考。"""
    amount = non_negative(compensation_amount)
    fee = non_negative(base_fee)
    if amount <= Decimal("50000"):
        return money(fee)
    if amount <= Decimal("100000"):
        return money(fee + (amount - Decimal("50000")) * Decimal("0.01"))
    return money(fee + Decimal("500") + (amount - Decimal("100000")) * Decimal("0.005"))


def calculate_execution_fee(amount: float | int | str, *, no_amount_mode: bool = False, base_fee: float | int | str = 50) -> Decimal:
    """执行申请费。"""
    if no_amount_mode:
        return money(base_fee)

    amt = non_negative(amount)
    if amt <= Decimal("10000"):
        return money("50")
    if amt <= Decimal("500000"):
        return money(Decimal("50") + (amt - Decimal("10000")) * Decimal("0.015"))
    if amt <= Decimal("5000000"):
        return money(Decimal("7400") + (amt - Decimal("500000")) * Decimal("0.01"))
    if amt <= Decimal("10000000"):
        return money(Decimal("52400") + (amt - Decimal("5000000")) * Decimal("0.005"))
    return money(Decimal("77400") + (amt - Decimal("10000000")) * Decimal("0.001"))


def calculate_preservation_fee(amount: float | int | str, *, no_amount_mode: bool = False, base_fee: float | int | str = 30) -> Decimal:
    """财产保全申请费。"""
    if no_amount_mode:
        return money(base_fee)

    amt = non_negative(amount)
    if amt <= Decimal("1000"):
        return money("30")
    if amt <= Decimal("100000"):
        return money(Decimal("30") + (amt - Decimal("1000")) * Decimal("0.01"))
    fee = Decimal("1020") + (amt - Decimal("100000")) * Decimal("0.005")
    return money(min(fee, Decimal("5000")))


def calculate_simple_interest(
    principal: float | int | str,
    annual_rate_pct: float | int | str,
    days: int,
    day_basis: int = 365,
) -> Decimal:
    amt = non_negative(principal)
    rate = non_negative(annual_rate_pct) / Decimal("100")
    total_days = max(int(days), 0)
    basis = Decimal(str(day_basis if day_basis > 0 else 365))
    return money(amt * rate * Decimal(total_days) / basis)


def calculate_liquidated_damages(
    base_amount: float | int | str,
    days: int,
    *,
    daily_rate_pct: float | int | str = 0,
    annual_rate_pct: float | int | str = 0,
    fixed_amount: float | int | str = 0,
) -> Decimal:
    amt = non_negative(base_amount)
    total_days = max(int(days), 0)
    fixed = non_negative(fixed_amount)
    if _d(daily_rate_pct) > 0:
        return money(fixed + amt * non_negative(daily_rate_pct) / Decimal("100") * Decimal(total_days))
    if _d(annual_rate_pct) > 0:
        return money(fixed + amt * non_negative(annual_rate_pct) / Decimal("100") * Decimal(total_days) / Decimal("365"))
    return money(fixed)


def calculate_occupation_fee(
    monthly_fee: float | int | str,
    months: float | int | str,
    *,
    daily_fee: float | int | str = 0,
    days: int = 0,
    fixed_amount: float | int | str = 0,
) -> Decimal:
    return money(
        non_negative(monthly_fee) * non_negative(months)
        + non_negative(daily_fee) * Decimal(max(int(days), 0))
        + non_negative(fixed_amount)
    )


def calculate_delay_performance_interest(
    principal: float | int | str,
    days: int,
    *,
    normal_annual_rate_pct: float | int | str = 0,
    day_basis: int = 365,
) -> Dict[str, Decimal]:
    amt = non_negative(principal)
    total_days = max(int(days), 0)
    general_interest = calculate_simple_interest(amt, normal_annual_rate_pct, total_days, day_basis=day_basis)
    doubled_interest = money(amt * DOUBLE_DELAY_DAILY_RATE * Decimal(total_days))
    return {
        "general_interest": general_interest,
        "doubled_interest": doubled_interest,
        "total": money(general_interest + doubled_interest),
    }


def calculate_lawyer_fee(
    mode: str,
    *,
    fixed_fee: float | int | str = 0,
    hourly_rate: float | int | str = 0,
    hours: float | int | str = 0,
    claim_amount: float | int | str = 0,
    rate_pct: float | int | str = 0,
) -> Decimal:
    if mode == "fixed":
        return money(fixed_fee)
    if mode == "hourly":
        return money(non_negative(hourly_rate) * non_negative(hours))
    return money(non_negative(claim_amount) * non_negative(rate_pct) / Decimal("100"))


def calculate_labor_compensation(
    monthly_wage: float | int | str,
    local_avg_wage: float | int | str,
    full_years: int,
    extra_months: int,
) -> Dict[str, Decimal]:
    years = max(int(full_years), 0)
    months = max(int(extra_months), 0)
    compensation_months = Decimal(str(years))
    if months >= 6:
        compensation_months += Decimal("1")
    elif months > 0:
        compensation_months += Decimal("0.5")

    actual_wage = non_negative(monthly_wage)
    local_avg = non_negative(local_avg_wage)
    monthly_base = actual_wage
    if local_avg > 0 and actual_wage > local_avg * Decimal("3"):
        monthly_base = local_avg * Decimal("3")
        compensation_months = min(compensation_months, Decimal("12"))

    compensation = money(monthly_base * compensation_months)
    return {
        "monthly_base": money(monthly_base),
        "compensation_months": compensation_months,
        "economic_compensation": compensation,
        "damages": money(compensation * Decimal("2")),
    }


def calculate_work_injury_disability(
    monthly_wage: float | int | str,
    level: int,
    *,
    local_medical_subsidy: float | int | str = 0,
    local_employment_subsidy: float | int | str = 0,
) -> Dict[str, Decimal]:
    wage = non_negative(monthly_wage)
    lv = max(1, min(int(level), 10))
    one_time_months = Decimal(str(WORK_INJURY_ONE_TIME_SUBSIDY_MONTHS[lv]))
    one_time_subsidy = money(wage * one_time_months)
    allowance = Decimal("0")
    if lv in WORK_INJURY_ALLOWANCE_RATES:
        allowance = money(wage * WORK_INJURY_ALLOWANCE_RATES[lv])
    total = money(one_time_subsidy + allowance + non_negative(local_medical_subsidy) + non_negative(local_employment_subsidy))
    return {
        "one_time_subsidy": one_time_subsidy,
        "monthly_allowance": allowance,
        "medical_subsidy": money(local_medical_subsidy),
        "employment_subsidy": money(local_employment_subsidy),
        "total_reference": total,
    }


def calculate_work_injury_death(
    employee_monthly_wage: float | int | str,
    local_avg_month_wage: float | int | str,
    national_disposable_income: float | int | str,
    *,
    spouse_count: int = 1,
    other_dependents: int = 0,
    extra_supported_people: int = 0,
) -> Dict[str, Decimal]:
    wage = non_negative(employee_monthly_wage)
    funeral_grant = money(non_negative(local_avg_month_wage) * Decimal("6"))
    death_grant = money(non_negative(national_disposable_income) * Decimal("20"))
    rate = Decimal("0.4") * Decimal(max(spouse_count, 0))
    rate += Decimal("0.3") * Decimal(max(other_dependents, 0))
    rate += Decimal("0.1") * Decimal(max(extra_supported_people, 0))
    rate = min(rate, Decimal("1.0"))
    dependent_pension_monthly = money(wage * rate)
    total = money(funeral_grant + death_grant)
    return {
        "funeral_grant": funeral_grant,
        "death_grant": death_grant,
        "dependent_pension_monthly": dependent_pension_monthly,
        "total_reference": total,
    }


def compensation_years_for_age(age: int) -> int:
    if age < 60:
        return 20
    if age >= 75:
        return 5
    return max(5, 20 - (age - 60))


def calculate_traffic_injury_compensation(
    *,
    medical_fee: float | int | str = 0,
    rehabilitation_fee: float | int | str = 0,
    followup_fee: float | int | str = 0,
    hospital_meal_fee: float | int | str = 0,
    nutrition_fee: float | int | str = 0,
    nursing_days: int = 0,
    nursing_daily_fee: float | int | str = 0,
    lost_income_days: int = 0,
    lost_income_daily: float | int | str = 0,
    transportation_fee: float | int | str = 0,
    accommodation_fee: float | int | str = 0,
    disability_percent: float | int | str = 0,
    disability_base_year_amount: float | int | str = 0,
    disability_years: int = 20,
    assistive_device_fee: float | int | str = 0,
    mental_damage_fee: float | int | str = 0,
    funeral_fee: float | int | str = 0,
    death_compensation_base_year_amount: float | int | str = 0,
    death_years: int = 20,
    dependent_living_fee: float | int | str = 0,
) -> Dict[str, Decimal]:
    disability_ratio = non_negative(disability_percent) / Decimal("100")
    disability_compensation = money(
        non_negative(disability_base_year_amount) * Decimal(max(int(disability_years), 0)) * disability_ratio
    )
    death_compensation = money(
        non_negative(death_compensation_base_year_amount) * Decimal(max(int(death_years), 0))
    )
    nursing_fee = money(non_negative(nursing_daily_fee) * Decimal(max(int(nursing_days), 0)))
    lost_income_fee = money(non_negative(lost_income_daily) * Decimal(max(int(lost_income_days), 0)))
    total = money(
        non_negative(medical_fee)
        + non_negative(rehabilitation_fee)
        + non_negative(followup_fee)
        + non_negative(hospital_meal_fee)
        + non_negative(nutrition_fee)
        + nursing_fee
        + lost_income_fee
        + non_negative(transportation_fee)
        + non_negative(accommodation_fee)
        + disability_compensation
        + non_negative(assistive_device_fee)
        + non_negative(mental_damage_fee)
        + non_negative(funeral_fee)
        + death_compensation
        + non_negative(dependent_living_fee)
    )
    return {
        "nursing_fee": nursing_fee,
        "lost_income_fee": lost_income_fee,
        "disability_compensation": disability_compensation,
        "death_compensation": death_compensation,
        "total_reference": total,
    }


def calculate_bankruptcy_administrator_fee(
    asset_amount: float | int | str,
    *,
    adjustment_factor: float | int | str = 1.0,
) -> Decimal:
    """按《企业破产案件管理人报酬规定》的分段上限口径计算参考值。"""
    amt = non_negative(asset_amount)
    factor = max(Decimal("0"), _d(adjustment_factor))
    fee = Decimal("0")
    tiers = [
        (Decimal("1000000"), Decimal("0.12")),
        (Decimal("5000000"), Decimal("0.10")),
        (Decimal("10000000"), Decimal("0.08")),
        (Decimal("50000000"), Decimal("0.06")),
        (Decimal("100000000"), Decimal("0.03")),
        (Decimal("500000000"), Decimal("0.01")),
    ]
    previous = Decimal("0")
    remaining = amt
    for upper, rate in tiers:
        if remaining <= 0:
            break
        span = min(amt, upper) - previous
        if span > 0:
            fee += span * rate
            previous = upper
            remaining = amt - previous
    if amt > Decimal("500000000"):
        fee += (amt - Decimal("500000000")) * Decimal("0.005")
    return money(fee * factor)


def add_months(source: date, months: int) -> date:
    total_month = source.month - 1 + months
    target_year = source.year + total_month // 12
    target_month = total_month % 12 + 1
    target_day = min(source.day, monthrange(target_year, target_month)[1])
    return date(target_year, target_month, target_day)


def add_years(source: date, years: int) -> date:
    target_year = source.year + years
    target_day = min(source.day, monthrange(target_year, source.month)[1])
    return date(target_year, source.month, target_day)


def calculate_date_offset(
    start: date,
    *,
    days: int = 0,
    months: int = 0,
    years: int = 0,
    exclude_start_day: bool = False,
    move_to_next_workday: bool = False,
) -> date:
    result = start
    if exclude_start_day and days >= 0:
        result += timedelta(days=1)
    if years:
        result = add_years(result, int(years))
    if months:
        result = add_months(result, int(months))
    if days:
        result += timedelta(days=int(days))
    if move_to_next_workday:
        while result.weekday() >= 5:
            result += timedelta(days=1)
    return result


def calculate_procedural_deadline(
    start: date,
    rule_key: str,
    *,
    exclude_start_day: bool = False,
    move_to_next_workday: bool = True,
) -> Dict[str, object]:
    rule = PROCEDURAL_LIMIT_RULES[rule_key]
    result = start
    if exclude_start_day:
        result += timedelta(days=1)
    if "months" in rule:
        result = add_months(result, int(rule["months"]))
    if "days" in rule:
        result += timedelta(days=int(rule["days"]))
    if move_to_next_workday:
        while result.weekday() >= 5:
            result += timedelta(days=1)
    return {
        "label": str(rule["label"]),
        "deadline": result,
        "note": str(rule["note"]),
    }

