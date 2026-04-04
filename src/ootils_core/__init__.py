"""
ootils-core: The first supply chain decision engine designed for the age of AI agents.

This package provides a comprehensive set of tools for making intelligent supply chain
decisions. It is designed to be used both directly by developers and as a tool-calling
interface for AI agents.

Quick start::

    from ootils_core import SupplyChainDecisionEngine
    from ootils_core.models import Product, Supplier, InventoryState

    engine = SupplyChainDecisionEngine()
    product = Product(sku="SKU-001", name="Widget A", unit_cost=10.0, holding_cost_rate=0.25)
    supplier = Supplier(name="Supplier Co", lead_time_days=14, reliability_score=0.95)

    state = InventoryState(product=product, current_stock=50, daily_demand=5.0)
    decision = engine.decide(state, suppliers=[supplier])
    print(decision)
"""

__version__ = "0.1.0"
__all__: list = []

