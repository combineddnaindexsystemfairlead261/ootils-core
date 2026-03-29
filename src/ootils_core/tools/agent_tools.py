"""
AI agent tool interface for the supply chain decision engine.

:class:`SupplyChainTools` exposes the engine's capabilities as a collection
of strongly-typed callable methods. Each method accepts and returns plain
Python dictionaries so that they can be serialised to JSON and consumed
directly by LLM function-calling APIs (OpenAI tools, Anthropic tool use,
Google Gemini function declarations, etc.).

All tool methods follow the same contract:

* **Input**: a flat dictionary of primitive values.
* **Output**: a dictionary with a ``"status"`` key (``"ok"`` or ``"error"``)
  and either a ``"result"`` key containing the answer or an ``"error"``
  key containing a human-readable error message.

Example (OpenAI-style agent)::

    tools = SupplyChainTools()
    result = tools.calculate_reorder_point({
        "daily_demand": 50,
        "lead_time_days": 14,
        "demand_std_daily": 8,
        "lead_time_std_days": 2,
        "service_level": 0.95,
    })
    # result -> {"status": "ok", "result": {"reorder_point": ..., "safety_stock": ...}}
"""

from __future__ import annotations

import math
from typing import Any

from ootils_core.engine.decision_engine import SupplyChainDecisionEngine
from ootils_core.engine.policies import (
    economic_order_quantity,
    reorder_point,
    safety_stock,
    urgency_level,
)
from ootils_core.engine.supplier_selection import rank_suppliers
from ootils_core.models import InventoryState, Product, Supplier


class SupplyChainTools:
    """A collection of callable tools designed for AI agent consumption.

    Each public method represents one "tool" that an agent can invoke.  The
    methods are intentionally coarse-grained (one tool per decision type) so
    agents can pick the most relevant one rather than having to orchestrate
    many low-level calls.

    The class is stateless and thread-safe.
    """

    _engine = SupplyChainDecisionEngine()

    # ------------------------------------------------------------------
    # Tool: calculate_reorder_point
    # ------------------------------------------------------------------

    def calculate_reorder_point(self, params: dict[str, Any]) -> dict[str, Any]:
        """Calculate the reorder point and safety stock for a product.

        Args:
            params: Dictionary with keys:

                * ``daily_demand`` (float): Average daily demand in units.
                * ``lead_time_days`` (float): Supplier lead time in days.
                * ``demand_std_daily`` (float, optional): Std-dev of daily
                  demand. Defaults to ``0``.
                * ``lead_time_std_days`` (float, optional): Std-dev of lead
                  time. Defaults to ``0``.
                * ``service_level`` (float, optional): Desired service level
                  in (0, 1). Defaults to ``0.95``.

        Returns:
            ``{"status": "ok", "result": {"reorder_point": float, "safety_stock": float}}``
            on success, or ``{"status": "error", "error": str}`` on failure.
        """
        try:
            daily_demand = float(params["daily_demand"])
            lead_time_days = float(params["lead_time_days"])
            demand_std_daily = float(params.get("demand_std_daily", 0))
            lead_time_std_days = float(params.get("lead_time_std_days", 0))
            service_level = float(params.get("service_level", 0.95))

            ss = safety_stock(
                daily_demand=daily_demand,
                demand_std_daily=demand_std_daily,
                lead_time_days=lead_time_days,
                lead_time_std_days=lead_time_std_days,
                service_level=service_level,
            )
            rop = reorder_point(
                daily_demand=daily_demand,
                lead_time_days=lead_time_days,
                safety_stock=ss,
            )
            return {
                "status": "ok",
                "result": {
                    "reorder_point": round(rop, 2),
                    "safety_stock": round(ss, 2),
                    "average_demand_during_lead_time": round(daily_demand * lead_time_days, 2),
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc)}

    # ------------------------------------------------------------------
    # Tool: calculate_eoq
    # ------------------------------------------------------------------

    def calculate_eoq(self, params: dict[str, Any]) -> dict[str, Any]:
        """Calculate the Economic Order Quantity (EOQ).

        Args:
            params: Dictionary with keys:

                * ``annual_demand`` (float): Annual demand in units.
                * ``ordering_cost`` (float): Fixed cost per purchase order.
                * ``unit_cost`` (float): Cost per unit.
                * ``holding_cost_rate`` (float, optional): Annual holding cost
                  as a fraction of unit cost. Defaults to ``0.25``.

        Returns:
            ``{"status": "ok", "result": {"eoq": float, "annual_total_cost": float}}``
        """
        try:
            annual_demand = float(params["annual_demand"])
            ordering_cost = float(params["ordering_cost"])
            unit_cost = float(params["unit_cost"])
            holding_cost_rate = float(params.get("holding_cost_rate", 0.25))

            eoq = economic_order_quantity(
                annual_demand=annual_demand,
                ordering_cost=ordering_cost,
                unit_cost=unit_cost,
                holding_cost_rate=holding_cost_rate,
            )
            holding_cost_per_unit = unit_cost * holding_cost_rate
            annual_total_cost = (
                (annual_demand / eoq) * ordering_cost + (eoq / 2) * holding_cost_per_unit
                if eoq > 0
                else 0.0
            )
            return {
                "status": "ok",
                "result": {
                    "eoq": round(eoq, 2),
                    "annual_ordering_cost": round((annual_demand / eoq) * ordering_cost, 2)
                    if eoq > 0
                    else 0.0,
                    "annual_holding_cost": round((eoq / 2) * holding_cost_per_unit, 2),
                    "annual_total_cost": round(annual_total_cost, 2),
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc)}

    # ------------------------------------------------------------------
    # Tool: recommend_order
    # ------------------------------------------------------------------

    def recommend_order(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a full purchase order recommendation for a product.

        This is the primary decision tool.  It combines inventory policy
        calculations with supplier selection to produce a single actionable
        recommendation.

        Args:
            params: Dictionary with keys:

                * ``sku`` (str): Product SKU.
                * ``name`` (str): Product name.
                * ``unit_cost`` (float): Product unit cost.
                * ``current_stock`` (float): On-hand inventory.
                * ``daily_demand`` (float): Average daily demand.
                * ``demand_std_daily`` (float, optional): Demand std-dev.
                * ``open_order_quantity`` (float, optional): In-transit units.
                * ``holding_cost_rate`` (float, optional): Defaults to 0.25.
                * ``ordering_cost`` (float, optional): Defaults to 50.
                * ``service_level`` (float, optional): Defaults to 0.95.
                * ``lead_time_days`` (float, optional): Defaults to 14.
                * ``lead_time_std_days`` (float, optional): Defaults to 2.
                * ``suppliers`` (list[dict]): Each dict may contain:
                    - ``name`` (str, required)
                    - ``lead_time_days`` (float, required)
                    - ``lead_time_std_days`` (float, optional)
                    - ``reliability_score`` (float, optional)
                    - ``unit_price_multiplier`` (float, optional)
                    - ``min_order_quantity`` (int, optional)
                    - ``max_order_quantity`` (int, optional)

        Returns:
            ``{"status": "ok", "result": {...}}`` with the recommendation
            details, or ``{"status": "no_action"}`` if no order is needed,
            or ``{"status": "error", "error": str}`` on failure.
        """
        try:
            product = Product(
                sku=str(params["sku"]),
                name=str(params["name"]),
                unit_cost=float(params["unit_cost"]),
                holding_cost_rate=float(params.get("holding_cost_rate", 0.25)),
                ordering_cost=float(params.get("ordering_cost", 50.0)),
                service_level=float(params.get("service_level", 0.95)),
                lead_time_days=float(params.get("lead_time_days", 14.0)),
                lead_time_std_days=float(params.get("lead_time_std_days", 2.0)),
            )
            state = InventoryState(
                product=product,
                current_stock=float(params["current_stock"]),
                daily_demand=float(params["daily_demand"]),
                demand_std_daily=float(params.get("demand_std_daily", 0.0)),
                open_order_quantity=float(params.get("open_order_quantity", 0.0)),
            )

            raw_suppliers = params.get("suppliers", [])
            if not raw_suppliers:
                return {"status": "error", "error": "At least one supplier is required."}

            suppliers = [
                Supplier(
                    name=str(s["name"]),
                    lead_time_days=float(s["lead_time_days"]),
                    lead_time_std_days=float(s.get("lead_time_std_days", 2.0)),
                    reliability_score=float(s.get("reliability_score", 1.0)),
                    unit_price_multiplier=float(s.get("unit_price_multiplier", 1.0)),
                    min_order_quantity=int(s.get("min_order_quantity", 1)),
                    max_order_quantity=int(s["max_order_quantity"])
                    if s.get("max_order_quantity") is not None
                    else None,
                )
                for s in raw_suppliers
            ]

            recommendation = self._engine.decide(state, suppliers)

            if recommendation is None:
                return {
                    "status": "no_action",
                    "result": {
                        "message": "Stock levels are adequate. No order is required at this time.",
                        "effective_stock": state.effective_stock,
                        "days_of_supply": round(state.days_of_supply, 1)
                        if not math.isinf(state.days_of_supply)
                        else None,
                    },
                }

            return {
                "status": "ok",
                "result": {
                    "sku": recommendation.product.sku,
                    "supplier": recommendation.supplier.name,
                    "order_quantity": recommendation.order_quantity,
                    "urgency": recommendation.urgency,
                    "reorder_point": round(recommendation.reorder_point, 2),
                    "safety_stock": round(recommendation.safety_stock, 2),
                    "economic_order_quantity": round(recommendation.economic_order_quantity, 2),
                    "rationale": recommendation.rationale,
                    "metadata": recommendation.metadata,
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc)}

    # ------------------------------------------------------------------
    # Tool: rank_suppliers
    # ------------------------------------------------------------------

    def rank_suppliers(self, params: dict[str, Any]) -> dict[str, Any]:
        """Rank a list of suppliers for a product by composite score.

        Args:
            params: Dictionary with keys:

                * ``unit_cost`` (float): Base unit cost of the product.
                * ``suppliers`` (list[dict]): Supplier dictionaries (same
                  schema as in :meth:`recommend_order`).

        Returns:
            ``{"status": "ok", "result": {"ranked_suppliers": [...]}}``
            where each entry has ``name``, ``score``, ``lead_time_days``,
            ``reliability_score``, and ``effective_unit_cost``.
        """
        try:
            unit_cost = float(params["unit_cost"])
            raw_suppliers = params.get("suppliers", [])
            if not raw_suppliers:
                return {"status": "error", "error": "At least one supplier is required."}

            suppliers = [
                Supplier(
                    name=str(s["name"]),
                    lead_time_days=float(s["lead_time_days"]),
                    lead_time_std_days=float(s.get("lead_time_std_days", 2.0)),
                    reliability_score=float(s.get("reliability_score", 1.0)),
                    unit_price_multiplier=float(s.get("unit_price_multiplier", 1.0)),
                    min_order_quantity=int(s.get("min_order_quantity", 1)),
                )
                for s in raw_suppliers
            ]

            ranked = rank_suppliers(suppliers, unit_cost)
            return {
                "status": "ok",
                "result": {
                    "ranked_suppliers": [
                        {
                            "name": s.name,
                            "score": round(score, 6),
                            "lead_time_days": s.lead_time_days,
                            "reliability_score": s.reliability_score,
                            "effective_unit_cost": round(s.effective_unit_cost(unit_cost), 4),
                        }
                        for s, score in ranked
                    ]
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc)}

    # ------------------------------------------------------------------
    # Tool: assess_risk
    # ------------------------------------------------------------------

    def assess_risk(self, params: dict[str, Any]) -> dict[str, Any]:
        """Assess supply chain risk for a given inventory snapshot.

        Provides a structured risk assessment that agents can use to
        prioritise their actions without making a full ordering decision.

        Args:
            params: Dictionary with keys:

                * ``current_stock`` (float): On-hand inventory.
                * ``daily_demand`` (float): Average daily demand.
                * ``reorder_point`` (float): Calculated or known reorder point.
                * ``safety_stock`` (float): Safety stock level.
                * ``lead_time_days`` (float, optional): For coverage calculation.

        Returns:
            ``{"status": "ok", "result": {...}}`` with ``urgency``,
            ``days_of_supply``, ``stock_coverage_days``, and a plain-English
            ``assessment``.
        """
        try:
            current_stock = float(params["current_stock"])
            daily_demand = float(params["daily_demand"])
            rop = float(params["reorder_point"])
            ss = float(params["safety_stock"])
            lead_time_days = float(params.get("lead_time_days", 0))

            urgency = urgency_level(
                current_stock=current_stock,
                daily_demand=daily_demand,
                reorder_point=rop,
                safety_stock=ss,
            )

            days = current_stock / daily_demand if daily_demand > 0 else None

            stock_below_safety = current_stock < ss
            stock_below_rop = current_stock <= rop
            coverage_ok = days is None or days >= lead_time_days

            parts = []
            if urgency == "critical":
                parts.append("Stock is critically low or exhausted.")
            elif urgency == "high":
                parts.append("Stock is below safety stock threshold — risk of imminent stock-out.")
            elif urgency == "medium":
                parts.append("Stock has crossed the reorder point — replenishment should begin.")
            else:
                parts.append("Stock levels are within acceptable bounds.")

            if not coverage_ok:
                parts.append(
                    f"Stock covers only {days:.1f} days, which is less than "
                    f"the {lead_time_days:.0f}-day lead time."
                )

            return {
                "status": "ok",
                "result": {
                    "urgency": urgency,
                    "days_of_supply": round(days, 1) if days is not None else None,
                    "stock_below_safety_stock": stock_below_safety,
                    "stock_below_reorder_point": stock_below_rop,
                    "lead_time_coverage_adequate": coverage_ok,
                    "assessment": " ".join(parts),
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc)}

    # ------------------------------------------------------------------
    # Schema helper
    # ------------------------------------------------------------------

    @staticmethod
    def tool_schemas() -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool schemas for all public tool methods.

        Agents can pass these schemas directly to an LLM's ``tools`` parameter
        to enable function calling.

        Returns:
            A list of tool schema dictionaries.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "calculate_reorder_point",
                    "description": (
                        "Calculate the inventory reorder point and safety stock "
                        "required to meet a target service level."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "daily_demand": {"type": "number", "description": "Average daily demand (units)."},
                            "lead_time_days": {"type": "number", "description": "Supplier lead time in days."},
                            "demand_std_daily": {"type": "number", "description": "Std-dev of daily demand (units). Default 0."},
                            "lead_time_std_days": {"type": "number", "description": "Std-dev of lead time in days. Default 0."},
                            "service_level": {"type": "number", "description": "Target service level (0–1). Default 0.95."},
                        },
                        "required": ["daily_demand", "lead_time_days"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_eoq",
                    "description": "Calculate the Economic Order Quantity (EOQ) that minimises total ordering and holding costs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "annual_demand": {"type": "number", "description": "Annual demand in units."},
                            "ordering_cost": {"type": "number", "description": "Fixed cost per purchase order."},
                            "unit_cost": {"type": "number", "description": "Purchase cost per unit."},
                            "holding_cost_rate": {"type": "number", "description": "Annual holding cost as fraction of unit cost. Default 0.25."},
                        },
                        "required": ["annual_demand", "ordering_cost", "unit_cost"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "recommend_order",
                    "description": (
                        "Generate a complete purchase order recommendation for a product, "
                        "including supplier selection, order quantity, and rationale."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string", "description": "Product SKU."},
                            "name": {"type": "string", "description": "Product name."},
                            "unit_cost": {"type": "number", "description": "Product unit cost."},
                            "current_stock": {"type": "number", "description": "Current on-hand inventory."},
                            "daily_demand": {"type": "number", "description": "Average daily demand."},
                            "demand_std_daily": {"type": "number", "description": "Demand standard deviation. Default 0."},
                            "open_order_quantity": {"type": "number", "description": "Units already on order. Default 0."},
                            "suppliers": {
                                "type": "array",
                                "description": "List of candidate suppliers.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "lead_time_days": {"type": "number"},
                                        "reliability_score": {"type": "number"},
                                        "unit_price_multiplier": {"type": "number"},
                                        "min_order_quantity": {"type": "integer"},
                                        "max_order_quantity": {"type": "integer"},
                                    },
                                    "required": ["name", "lead_time_days"],
                                },
                            },
                        },
                        "required": ["sku", "name", "unit_cost", "current_stock", "daily_demand", "suppliers"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "rank_suppliers",
                    "description": "Rank suppliers by a composite score balancing cost, lead time, and reliability.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "unit_cost": {"type": "number", "description": "Base unit cost of the product."},
                            "suppliers": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "lead_time_days": {"type": "number"},
                                        "reliability_score": {"type": "number"},
                                        "unit_price_multiplier": {"type": "number"},
                                    },
                                    "required": ["name", "lead_time_days"],
                                },
                            },
                        },
                        "required": ["unit_cost", "suppliers"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "assess_risk",
                    "description": "Assess supply chain risk for a given inventory snapshot, returning urgency level and a plain-English assessment.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "current_stock": {"type": "number", "description": "Current on-hand inventory."},
                            "daily_demand": {"type": "number", "description": "Average daily demand."},
                            "reorder_point": {"type": "number", "description": "Inventory reorder point."},
                            "safety_stock": {"type": "number", "description": "Safety stock level."},
                            "lead_time_days": {"type": "number", "description": "Supplier lead time in days."},
                        },
                        "required": ["current_stock", "daily_demand", "reorder_point", "safety_stock"],
                    },
                },
            },
        ]
