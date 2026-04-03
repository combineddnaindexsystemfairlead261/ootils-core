"""Supply chain data models."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Product:
    """Represents a product in the supply chain.

    Attributes:
        sku: Stock Keeping Unit identifier.
        name: Human-readable product name.
        unit_cost: Cost per unit (purchase price).
        holding_cost_rate: Annual holding cost as a fraction of unit cost (e.g. 0.25 = 25%).
        ordering_cost: Fixed cost per purchase order placed.
        service_level: Desired probability of not running out of stock (0–1).
        lead_time_days: Average supplier lead time in days (can be overridden per supplier).
        lead_time_std_days: Standard deviation of lead time in days (for safety stock).
    """

    sku: str
    name: str
    unit_cost: float
    holding_cost_rate: float = 0.25
    ordering_cost: float = 50.0
    service_level: float = 0.95
    lead_time_days: float = 14.0
    lead_time_std_days: float = 2.0

    def __post_init__(self) -> None:
        if self.unit_cost <= 0:
            raise ValueError(f"unit_cost must be positive, got {self.unit_cost}")
        if not 0 < self.holding_cost_rate <= 1:
            raise ValueError(f"holding_cost_rate must be in (0, 1], got {self.holding_cost_rate}")
        if self.ordering_cost < 0:
            raise ValueError(f"ordering_cost must be non-negative, got {self.ordering_cost}")
        if not 0 < self.service_level < 1:
            raise ValueError(f"service_level must be in (0, 1), got {self.service_level}")
        if self.lead_time_days < 0:
            raise ValueError(f"lead_time_days must be non-negative, got {self.lead_time_days}")
        if self.lead_time_std_days < 0:
            raise ValueError(
                f"lead_time_std_days must be non-negative, got {self.lead_time_std_days}"
            )

    @property
    def annual_holding_cost_per_unit(self) -> float:
        """Annual holding cost per unit (currency)."""
        return self.unit_cost * self.holding_cost_rate


@dataclass
class Supplier:
    """Represents a supplier in the supply chain.

    Attributes:
        name: Supplier name.
        lead_time_days: Average delivery lead time in calendar days.
        lead_time_std_days: Standard deviation of lead time in days.
        reliability_score: Historical on-time delivery rate (0–1).
        unit_price_multiplier: Price relative to base ``Product.unit_cost`` (e.g. 1.1 = 10% premium).
        min_order_quantity: Minimum order quantity enforced by the supplier.
        max_order_quantity: Maximum order quantity the supplier can fulfil (None = unlimited).
        active: Whether this supplier is currently available for ordering.
    """

    name: str
    lead_time_days: float
    lead_time_std_days: float = 2.0
    reliability_score: float = 1.0
    unit_price_multiplier: float = 1.0
    min_order_quantity: int = 1
    max_order_quantity: Optional[int] = None
    active: bool = True

    def __post_init__(self) -> None:
        if self.lead_time_days < 0:
            raise ValueError(f"lead_time_days must be non-negative, got {self.lead_time_days}")
        if not 0 <= self.reliability_score <= 1:
            raise ValueError(
                f"reliability_score must be in [0, 1], got {self.reliability_score}"
            )
        if self.unit_price_multiplier <= 0:
            raise ValueError(
                f"unit_price_multiplier must be positive, got {self.unit_price_multiplier}"
            )
        if self.min_order_quantity < 1:
            raise ValueError(
                f"min_order_quantity must be >= 1, got {self.min_order_quantity}"
            )
        if self.max_order_quantity is not None and self.max_order_quantity < self.min_order_quantity:
            raise ValueError(
                "max_order_quantity must be >= min_order_quantity, "
                f"got {self.max_order_quantity} < {self.min_order_quantity}"
            )

    def effective_unit_cost(self, base_unit_cost: float) -> float:
        """Return the actual unit purchase price from this supplier."""
        return base_unit_cost * self.unit_price_multiplier

    def clamp_quantity(self, quantity: int) -> int:
        """Clamp *quantity* to this supplier's min/max order constraints."""
        clamped = max(quantity, self.min_order_quantity)
        if self.max_order_quantity is not None:
            clamped = min(clamped, self.max_order_quantity)
        return clamped


@dataclass
class InventoryState:
    """Snapshot of the current inventory situation for a single product.

    Attributes:
        product: The product this state refers to.
        current_stock: Units currently on hand.
        daily_demand: Average daily demand (units/day).
        demand_std_daily: Standard deviation of daily demand.
        open_order_quantity: Units already on order but not yet received.
        days_of_supply: Calculated as ``current_stock / daily_demand`` (read-only).
    """

    product: Product
    current_stock: float
    daily_demand: float
    demand_std_daily: float = 0.0
    open_order_quantity: float = 0.0

    def __post_init__(self) -> None:
        if self.current_stock < 0:
            raise ValueError(f"current_stock must be non-negative, got {self.current_stock}")
        if self.daily_demand < 0:
            raise ValueError(f"daily_demand must be non-negative, got {self.daily_demand}")
        if self.demand_std_daily < 0:
            raise ValueError(
                f"demand_std_daily must be non-negative, got {self.demand_std_daily}"
            )
        if self.open_order_quantity < 0:
            raise ValueError(
                f"open_order_quantity must be non-negative, got {self.open_order_quantity}"
            )

    @property
    def days_of_supply(self) -> float:
        """Estimated days until stock-out, excluding open orders."""
        if self.daily_demand == 0:
            return float("inf")
        return self.current_stock / self.daily_demand

    @property
    def effective_stock(self) -> float:
        """Current stock plus any open orders in transit."""
        return self.current_stock + self.open_order_quantity


@dataclass
class OrderRecommendation:
    """A recommended purchase order produced by the decision engine.

    Attributes:
        product: The product to order.
        supplier: The recommended supplier.
        order_quantity: Recommended number of units to order.
        reorder_point: Inventory level that triggered or will trigger the recommendation.
        safety_stock: Calculated safety stock buffer.
        economic_order_quantity: Optimal order size before supplier constraints.
        rationale: Human- and agent-readable explanation of the decision.
        urgency: One of ``"critical"``, ``"high"``, ``"medium"``, or ``"low"``.
    """

    product: Product
    supplier: Supplier
    order_quantity: int
    reorder_point: float
    safety_stock: float
    economic_order_quantity: float
    rationale: str
    urgency: str
    metadata: dict = field(default_factory=dict)
