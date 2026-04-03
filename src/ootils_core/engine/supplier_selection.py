"""
Supplier selection logic.

The selection algorithm scores each active supplier on a composite metric
that balances cost, lead time, and reliability, then returns the best match.
"""

from __future__ import annotations

from typing import Sequence

from ootils_core.models import Supplier


def select_supplier(suppliers: Sequence[Supplier], base_unit_cost: float) -> Supplier:
    """Select the best supplier from *suppliers* using a composite score.

    The score is computed as::

        score = reliability * (w_cost * cost_score + w_lead * lead_score)

    where ``cost_score = 1 / effective_unit_cost`` and
    ``lead_score = 1 / (lead_time_days + 1)``.  Both weights default to 0.5
    so cost and lead time are weighted equally.

    Args:
        suppliers: Non-empty sequence of active :class:`~ootils_core.models.Supplier`
            instances.
        base_unit_cost: The product's base unit cost (``Product.unit_cost``),
            used to calculate effective prices.

    Returns:
        The highest-scoring supplier.

    Raises:
        ValueError: If *suppliers* is empty.
    """
    if not suppliers:
        raise ValueError("Cannot select a supplier from an empty list.")

    return max(suppliers, key=lambda s: _score(s, base_unit_cost))


def rank_suppliers(
    suppliers: Sequence[Supplier],
    base_unit_cost: float,
) -> list[tuple[Supplier, float]]:
    """Rank all *suppliers* by composite score (descending).

    Args:
        suppliers: Sequence of :class:`~ootils_core.models.Supplier` instances.
        base_unit_cost: The product's base unit cost.

    Returns:
        List of ``(supplier, score)`` tuples, sorted best-first.
    """
    scored = [(_score(s, base_unit_cost), i, s) for i, s in enumerate(suppliers)]
    scored.sort(key=lambda t: (t[0], -t[1]), reverse=True)
    return [(s, score) for score, _, s in scored]


def _score(supplier: Supplier, base_unit_cost: float) -> float:
    effective_cost = supplier.effective_unit_cost(base_unit_cost)
    cost_score = 1.0 / effective_cost if effective_cost > 0 else 0.0
    lead_score = 1.0 / (supplier.lead_time_days + 1)
    return supplier.reliability_score * (0.5 * cost_score + 0.5 * lead_score)
