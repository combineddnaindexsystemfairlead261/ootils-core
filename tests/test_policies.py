"""Tests for inventory policies (EOQ, ROP, safety stock, urgency)."""

import math

import pytest

from ootils_core.engine.policies import (
    economic_order_quantity,
    reorder_point,
    safety_stock,
    urgency_level,
    z_score,
)


class TestZScore:
    def test_known_values(self):
        assert z_score(0.95) == pytest.approx(1.645)
        assert z_score(0.99) == pytest.approx(2.326)
        assert z_score(0.90) == pytest.approx(1.282)

    def test_interpolated_value(self):
        # Between 0.95 (1.645) and 0.96 (1.751)
        z = z_score(0.955)
        assert 1.645 < z < 1.751

    def test_invalid_bounds(self):
        with pytest.raises(ValueError):
            z_score(0.0)
        with pytest.raises(ValueError):
            z_score(1.0)


class TestSafetyStock:
    def test_zero_variability(self):
        ss = safety_stock(
            daily_demand=10,
            demand_std_daily=0,
            lead_time_days=14,
            lead_time_std_days=0,
            service_level=0.95,
        )
        assert ss == pytest.approx(0.0)

    def test_demand_variability_only(self):
        # SS = z * sqrt(L * σ_d²) = z * σ_d * sqrt(L)
        d_std = 5.0
        L = 9.0
        z = 1.645
        expected = z * d_std * math.sqrt(L)
        ss = safety_stock(
            daily_demand=50,
            demand_std_daily=d_std,
            lead_time_days=L,
            lead_time_std_days=0,
            service_level=0.95,
        )
        assert ss == pytest.approx(expected, rel=0.001)

    def test_lead_time_variability_only(self):
        # SS = z * sqrt(d² * σ_L²) = z * d * σ_L
        d = 10.0
        lt_std = 3.0
        z = 1.645
        expected = z * d * lt_std
        ss = safety_stock(
            daily_demand=d,
            demand_std_daily=0,
            lead_time_days=14,
            lead_time_std_days=lt_std,
            service_level=0.95,
        )
        assert ss == pytest.approx(expected, rel=0.001)

    def test_combined_variability(self):
        ss = safety_stock(
            daily_demand=50,
            demand_std_daily=8,
            lead_time_days=14,
            lead_time_std_days=2,
            service_level=0.95,
        )
        assert ss > 0

    def test_higher_service_level_means_more_safety_stock(self):
        kwargs = dict(
            daily_demand=50,
            demand_std_daily=8,
            lead_time_days=14,
            lead_time_std_days=2,
        )
        ss_95 = safety_stock(**kwargs, service_level=0.95)
        ss_99 = safety_stock(**kwargs, service_level=0.99)
        assert ss_99 > ss_95


class TestReorderPoint:
    def test_basic(self):
        rop = reorder_point(daily_demand=10, lead_time_days=14, safety_stock=50)
        assert rop == pytest.approx(190.0)

    def test_zero_safety_stock(self):
        rop = reorder_point(daily_demand=5, lead_time_days=10, safety_stock=0)
        assert rop == pytest.approx(50.0)

    def test_zero_demand(self):
        rop = reorder_point(daily_demand=0, lead_time_days=14, safety_stock=20)
        assert rop == pytest.approx(20.0)


class TestEOQ:
    def test_classic_formula(self):
        # EOQ = sqrt(2 * 1000 * 50 / (10 * 0.25)) = sqrt(40000) = 200
        eoq = economic_order_quantity(
            annual_demand=1000,
            ordering_cost=50,
            unit_cost=10,
            holding_cost_rate=0.25,
        )
        assert eoq == pytest.approx(200.0, rel=0.001)

    def test_zero_demand_returns_one(self):
        assert economic_order_quantity(0, 50, 10, 0.25) == 1.0

    def test_larger_demand_increases_eoq(self):
        eoq_low = economic_order_quantity(500, 50, 10, 0.25)
        eoq_high = economic_order_quantity(2000, 50, 10, 0.25)
        assert eoq_high > eoq_low


class TestUrgencyLevel:
    def test_critical_no_stock(self):
        assert urgency_level(0, 10, 100, 30) == "critical"

    def test_critical_less_than_one_day(self):
        assert urgency_level(5, 10, 100, 30) == "critical"

    def test_high_below_safety_stock(self):
        assert urgency_level(20, 10, 100, 25) == "high"

    def test_medium_at_reorder_point(self):
        # current_stock > safety_stock, <= rop, days >= 3
        assert urgency_level(50, 5, 50, 10) == "medium"

    def test_low_above_rop(self):
        assert urgency_level(200, 10, 100, 30) == "low"

    def test_zero_demand_is_low(self):
        assert urgency_level(10, 0, 100, 30) == "low"
