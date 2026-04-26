# -*- coding: utf-8 -*-
"""法律工具中心核心公式测试"""

from src.core.legal_toolkit import (
    calculate_bankruptcy_administrator_fee,
    calculate_delay_performance_interest,
    calculate_labor_compensation,
    calculate_preservation_fee,
    calculate_property_litigation_fee,
)


class TestLegalToolkit:
    """核心公式回归。"""

    def test_property_litigation_fee_uses_progressive_rates(self):
        assert calculate_property_litigation_fee(10000) == 50
        assert calculate_property_litigation_fee(100000) == 2300
        assert calculate_property_litigation_fee(200000) == 4300

    def test_preservation_fee_has_cap(self):
        assert calculate_preservation_fee(500) == 30
        assert calculate_preservation_fee(1_000_000) == 5000

    def test_delay_performance_interest_splits_general_and_doubled_parts(self):
        result = calculate_delay_performance_interest(100000, 10, normal_annual_rate_pct=3.65)
        assert result["general_interest"] == 100
        assert result["doubled_interest"] == 175
        assert result["total"] == 275

    def test_labor_compensation_applies_three_times_average_cap(self):
        result = calculate_labor_compensation(40000, 10000, 15, 0)
        assert result["monthly_base"] == 30000
        assert result["compensation_months"] == 12
        assert result["economic_compensation"] == 360000
        assert result["damages"] == 720000

    def test_bankruptcy_fee_uses_piecewise_formula(self):
        assert calculate_bankruptcy_administrator_fee(1_000_000) == 120000
        assert calculate_bankruptcy_administrator_fee(6_000_000) == 600000
