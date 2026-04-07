"""
POST /v1/ingest/* — Batch import/upsert endpoints for supply chain master data.

Endpoints:
  POST /v1/ingest/items
  POST /v1/ingest/locations
  POST /v1/ingest/suppliers
  POST /v1/ingest/supplier-items
  POST /v1/ingest/on-hand
  POST /v1/ingest/purchase-orders
  POST /v1/ingest/forecast-demand

All endpoints accept JSON only (no TSV/CSV upload — MVP scope).
All DB operations use psycopg3 sync connections (same as other routers).
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, field_validator

from ootils_core.api.auth import require_auth
from ootils_core.api.dependencies import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/ingest", tags=["ingest"])

BASELINE_SCENARIO_ID = UUID("00000000-0000-0000-0000-000000000001")

# ─────────────────────────────────────────────────────────────
# Shared response models
# ─────────────────────────────────────────────────────────────

class IngestSummary(BaseModel):
    total: int
    inserted: int
    updated: int
    errors: int


class IngestResponse(BaseModel):
    status: str
    summary: IngestSummary
    results: list[dict]


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _ok(inserted: int, updated: int, total: int, results: list[dict]) -> IngestResponse:
    return IngestResponse(
        status="ok",
        summary=IngestSummary(total=total, inserted=inserted, updated=updated, errors=0),
        results=results,
    )


def _dry_run_response(items: list[Any], label: str = "external_id") -> IngestResponse:
    return IngestResponse(
        status="dry_run",
        summary=IngestSummary(total=len(items), inserted=0, updated=0, errors=0),
        results=[{"action": "dry_run", label: getattr(row, label, "?")} for row in items],
    )


def _error_response(total: int, errors: list[dict]) -> IngestResponse:
    return IngestResponse(
        status="error" if not any(e.get("action") not in (None, "error") for e in errors) else "partial",
        summary=IngestSummary(total=total, inserted=0, updated=0, errors=len(errors)),
        results=errors,
    )


def _batch_existing(
    db: psycopg.Connection,
    table: str,
    id_col: str,
    pk_col: str,
    external_ids: list[str],
) -> dict[str, UUID]:
    """Return {external_id: pk} for all rows matching the given external_ids."""
    if not external_ids:
        return {}
    rows = db.execute(
        f"SELECT {id_col}, {pk_col} FROM {table} WHERE {id_col} = ANY(%s)",
        (external_ids,),
    ).fetchall()
    return {r[id_col]: r[pk_col] for r in rows}


# ─────────────────────────────────────────────────────────────
# 1. POST /v1/ingest/items
# ─────────────────────────────────────────────────────────────

VALID_ITEM_TYPES = {"finished_good", "component", "raw_material", "semi_finished"}
VALID_ITEM_STATUSES = {"active", "obsolete", "phase_out"}


class ItemRow(BaseModel):
    external_id: str
    name: str
    item_type: str = "finished_good"
    uom: str = "EA"
    status: str = "active"

    @field_validator("external_id", "name")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


class IngestItemsRequest(BaseModel):
    items: list[ItemRow]
    conflict_strategy: str = "upsert"
    dry_run: bool = False


@router.post("/items", response_model=IngestResponse)
async def ingest_items(
    body: IngestItemsRequest,
    db: psycopg.Connection = Depends(get_db),
    _token: str = Depends(require_auth),
) -> IngestResponse:
    """Upsert items by external_id."""
    errors: list[dict] = []
    valid_items: list[ItemRow] = []

    for i, item in enumerate(body.items):
        row_errs = []
        if item.item_type not in VALID_ITEM_TYPES:
            row_errs.append(f"item_type '{item.item_type}' invalid; valid: {sorted(VALID_ITEM_TYPES)}")
        if item.status not in VALID_ITEM_STATUSES:
            row_errs.append(f"status '{item.status}' invalid; valid: {sorted(VALID_ITEM_STATUSES)}")
        if row_errs:
            errors.append({"external_id": item.external_id, "row": i, "errors": row_errs, "action": "error"})
        else:
            valid_items.append(item)

    if errors:
        return _error_response(len(body.items), errors)

    if body.dry_run:
        return _dry_run_response(valid_items)

    # Batch-fetch existing items
    existing = _batch_existing(
        db, "items", "external_id", "item_id",
        [it.external_id for it in valid_items],
    )

    results: list[dict] = []
    inserted = updated = 0

    for item in valid_items:
        if item.external_id in existing:
            db.execute(
                """
                UPDATE items
                SET name = %s, item_type = %s, uom = %s, status = %s, updated_at = now()
                WHERE external_id = %s
                """,
                (item.name, item.item_type, item.uom, item.status, item.external_id),
            )
            results.append({"external_id": item.external_id, "item_id": str(existing[item.external_id]), "action": "updated"})
            updated += 1
        else:
            item_id = uuid4()
            db.execute(
                """
                INSERT INTO items (item_id, external_id, name, item_type, uom, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (item_id, item.external_id, item.name, item.item_type, item.uom, item.status),
            )
            results.append({"external_id": item.external_id, "item_id": str(item_id), "action": "inserted"})
            inserted += 1

    logger.info("ingest.items total=%d inserted=%d updated=%d", len(valid_items), inserted, updated)
    return _ok(inserted, updated, len(body.items), results)


# ─────────────────────────────────────────────────────────────
# 2. POST /v1/ingest/locations
# ─────────────────────────────────────────────────────────────

VALID_LOCATION_TYPES = {"plant", "dc", "warehouse", "supplier_virtual", "customer_virtual"}


class LocationRow(BaseModel):
    external_id: str
    name: str
    location_type: str = "dc"
    country: Optional[str] = None
    timezone: Optional[str] = None
    parent_external_id: Optional[str] = None

    @field_validator("external_id", "name")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


class IngestLocationsRequest(BaseModel):
    locations: list[LocationRow]
    conflict_strategy: str = "upsert"
    dry_run: bool = False


@router.post("/locations", response_model=IngestResponse)
async def ingest_locations(
    body: IngestLocationsRequest,
    db: psycopg.Connection = Depends(get_db),
    _token: str = Depends(require_auth),
) -> IngestResponse:
    """Upsert locations by external_id."""
    errors: list[dict] = []
    valid_locs: list[LocationRow] = []

    # Build set of external_ids in the payload (for parent validation)
    payload_ext_ids = {loc.external_id for loc in body.locations}

    for i, loc in enumerate(body.locations):
        row_errs = []
        if loc.location_type not in VALID_LOCATION_TYPES:
            row_errs.append(
                f"location_type '{loc.location_type}' invalid; valid: {sorted(VALID_LOCATION_TYPES)}"
            )
        if loc.parent_external_id and loc.parent_external_id not in payload_ext_ids:
            # Check if parent exists in DB
            parent_in_db = db.execute(
                "SELECT 1 FROM locations WHERE external_id = %s",
                (loc.parent_external_id,),
            ).fetchone()
            if not parent_in_db:
                row_errs.append(
                    f"parent_external_id '{loc.parent_external_id}' not found in payload or DB"
                )
        if row_errs:
            errors.append({"external_id": loc.external_id, "row": i, "errors": row_errs, "action": "error"})
        else:
            valid_locs.append(loc)

    if errors:
        return _error_response(len(body.locations), errors)

    if body.dry_run:
        return _dry_run_response(valid_locs)

    existing = _batch_existing(
        db, "locations", "external_id", "location_id",
        [loc.external_id for loc in valid_locs],
    )

    results: list[dict] = []
    inserted = updated = 0

    for loc in valid_locs:
        if loc.external_id in existing:
            db.execute(
                """
                UPDATE locations
                SET name = %s, location_type = %s, country = %s, timezone = %s
                WHERE external_id = %s
                """,
                (loc.name, loc.location_type, loc.country, loc.timezone, loc.external_id),
            )
            results.append({"external_id": loc.external_id, "location_id": str(existing[loc.external_id]), "action": "updated"})
            updated += 1
        else:
            location_id = uuid4()
            db.execute(
                """
                INSERT INTO locations (location_id, external_id, name, location_type, country, timezone)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (location_id, loc.external_id, loc.name, loc.location_type, loc.country, loc.timezone),
            )
            results.append({"external_id": loc.external_id, "location_id": str(location_id), "action": "inserted"})
            inserted += 1

    logger.info("ingest.locations total=%d inserted=%d updated=%d", len(valid_locs), inserted, updated)
    return _ok(inserted, updated, len(body.locations), results)


# ─────────────────────────────────────────────────────────────
# 3. POST /v1/ingest/suppliers
# ─────────────────────────────────────────────────────────────

VALID_SUPPLIER_STATUSES = {"active", "inactive", "blocked"}


class SupplierRow(BaseModel):
    external_id: str
    name: str
    lead_time_days: Optional[int] = None
    reliability_score: Optional[float] = None
    moq: Optional[float] = None          # not a suppliers column, accepted but not persisted
    currency: Optional[str] = None       # not a suppliers column, accepted but not persisted
    country: Optional[str] = None
    status: str = "active"

    @field_validator("external_id", "name")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


class IngestSuppliersRequest(BaseModel):
    suppliers: list[SupplierRow]
    conflict_strategy: str = "upsert"
    dry_run: bool = False


@router.post("/suppliers", response_model=IngestResponse)
async def ingest_suppliers(
    body: IngestSuppliersRequest,
    db: psycopg.Connection = Depends(get_db),
    _token: str = Depends(require_auth),
) -> IngestResponse:
    """Upsert suppliers by external_id."""
    errors: list[dict] = []
    valid_suppliers: list[SupplierRow] = []

    for i, sup in enumerate(body.suppliers):
        row_errs = []
        if sup.status not in VALID_SUPPLIER_STATUSES:
            row_errs.append(f"status '{sup.status}' invalid; valid: {sorted(VALID_SUPPLIER_STATUSES)}")
        if sup.reliability_score is not None and not (0.0 <= sup.reliability_score <= 1.0):
            row_errs.append(f"reliability_score {sup.reliability_score} must be in [0, 1]")
        if row_errs:
            errors.append({"external_id": sup.external_id, "row": i, "errors": row_errs, "action": "error"})
        else:
            valid_suppliers.append(sup)

    if errors:
        return _error_response(len(body.suppliers), errors)

    if body.dry_run:
        return _dry_run_response(valid_suppliers)

    existing = _batch_existing(
        db, "suppliers", "external_id", "supplier_id",
        [s.external_id for s in valid_suppliers],
    )

    results: list[dict] = []
    inserted = updated = 0

    for sup in valid_suppliers:
        if sup.external_id in existing:
            db.execute(
                """
                UPDATE suppliers
                SET name = %s, lead_time_days = %s, reliability_score = %s,
                    country = %s, status = %s, updated_at = now()
                WHERE external_id = %s
                """,
                (sup.name, sup.lead_time_days, sup.reliability_score, sup.country, sup.status, sup.external_id),
            )
            results.append({"external_id": sup.external_id, "supplier_id": str(existing[sup.external_id]), "action": "updated"})
            updated += 1
        else:
            supplier_id = uuid4()
            db.execute(
                """
                INSERT INTO suppliers (supplier_id, external_id, name, lead_time_days, reliability_score, country, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (supplier_id, sup.external_id, sup.name, sup.lead_time_days, sup.reliability_score, sup.country, sup.status),
            )
            results.append({"external_id": sup.external_id, "supplier_id": str(supplier_id), "action": "inserted"})
            inserted += 1

    logger.info("ingest.suppliers total=%d inserted=%d updated=%d", len(valid_suppliers), inserted, updated)
    return _ok(inserted, updated, len(body.suppliers), results)


# ─────────────────────────────────────────────────────────────
# 4. POST /v1/ingest/supplier-items
# ─────────────────────────────────────────────────────────────

class SupplierItemRow(BaseModel):
    supplier_external_id: str
    item_external_id: str
    lead_time_days: int
    moq: Optional[float] = None
    unit_cost: Optional[float] = None
    is_preferred: bool = False
    currency: str = "EUR"


class IngestSupplierItemsRequest(BaseModel):
    supplier_items: list[SupplierItemRow]
    conflict_strategy: str = "upsert"
    dry_run: bool = False


@router.post("/supplier-items", response_model=IngestResponse)
async def ingest_supplier_items(
    body: IngestSupplierItemsRequest,
    db: psycopg.Connection = Depends(get_db),
    _token: str = Depends(require_auth),
) -> IngestResponse:
    """Upsert supplier_items by (supplier_id, item_id)."""
    if body.dry_run:
        results = []
        for si in body.supplier_items:
            results.append({
                "supplier_external_id": si.supplier_external_id,
                "item_external_id": si.item_external_id,
                "action": "dry_run",
            })
        return IngestResponse(
            status="dry_run",
            summary=IngestSummary(total=len(body.supplier_items), inserted=0, updated=0, errors=0),
            results=results,
        )

    # Resolve all supplier_external_ids in one query
    sup_ext_ids = list({si.supplier_external_id for si in body.supplier_items})
    item_ext_ids = list({si.item_external_id for si in body.supplier_items})

    supplier_map = _batch_existing(db, "suppliers", "external_id", "supplier_id", sup_ext_ids)
    item_map = _batch_existing(db, "items", "external_id", "item_id", item_ext_ids)

    results: list[dict] = []
    inserted = updated = errors_count = 0

    for i, si in enumerate(body.supplier_items):
        row_errs = []
        if si.supplier_external_id not in supplier_map:
            row_errs.append(f"supplier_external_id '{si.supplier_external_id}' not found in DB")
        if si.item_external_id not in item_map:
            row_errs.append(f"item_external_id '{si.item_external_id}' not found in DB")

        if row_errs:
            results.append({
                "supplier_external_id": si.supplier_external_id,
                "item_external_id": si.item_external_id,
                "row": i,
                "errors": row_errs,
                "action": "error",
            })
            errors_count += 1
            continue

        supplier_id = supplier_map[si.supplier_external_id]
        item_id = item_map[si.item_external_id]

        # Check if (supplier_id, item_id) already exists
        existing = db.execute(
            "SELECT supplier_item_id FROM supplier_items WHERE supplier_id = %s AND item_id = %s",
            (supplier_id, item_id),
        ).fetchone()

        if existing:
            db.execute(
                """
                UPDATE supplier_items
                SET lead_time_days = %s, moq = %s, unit_cost = %s,
                    is_preferred = %s, currency = %s
                WHERE supplier_id = %s AND item_id = %s
                """,
                (si.lead_time_days, si.moq, si.unit_cost, si.is_preferred, si.currency, supplier_id, item_id),
            )
            results.append({
                "supplier_external_id": si.supplier_external_id,
                "item_external_id": si.item_external_id,
                "supplier_item_id": str(existing["supplier_item_id"]),
                "action": "updated",
            })
            updated += 1
        else:
            supplier_item_id = uuid4()
            db.execute(
                """
                INSERT INTO supplier_items
                    (supplier_item_id, supplier_id, item_id, lead_time_days, moq, unit_cost, is_preferred, currency)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (supplier_item_id, supplier_id, item_id, si.lead_time_days, si.moq, si.unit_cost, si.is_preferred, si.currency),
            )
            results.append({
                "supplier_external_id": si.supplier_external_id,
                "item_external_id": si.item_external_id,
                "supplier_item_id": str(supplier_item_id),
                "action": "inserted",
            })
            inserted += 1

    logger.info(
        "ingest.supplier_items total=%d inserted=%d updated=%d errors=%d",
        len(body.supplier_items), inserted, updated, errors_count,
    )
    total_status = "ok" if errors_count == 0 else ("partial" if (inserted + updated) > 0 else "error")
    return IngestResponse(
        status=total_status,
        summary=IngestSummary(
            total=len(body.supplier_items),
            inserted=inserted,
            updated=updated,
            errors=errors_count,
        ),
        results=results,
    )


# ─────────────────────────────────────────────────────────────
# 5. POST /v1/ingest/on-hand
# ─────────────────────────────────────────────────────────────

class OnHandRow(BaseModel):
    item_external_id: str
    location_external_id: str
    quantity: float
    uom: str = "EA"
    as_of_date: date


class IngestOnHandRequest(BaseModel):
    on_hand: list[OnHandRow]
    dry_run: bool = False


@router.post("/on-hand", response_model=IngestResponse)
async def ingest_on_hand(
    body: IngestOnHandRequest,
    db: psycopg.Connection = Depends(get_db),
    _token: str = Depends(require_auth),
) -> IngestResponse:
    """Upsert OnHandSupply nodes in the baseline scenario."""
    if body.dry_run:
        results = [
            {"item_external_id": r.item_external_id, "location_external_id": r.location_external_id, "action": "dry_run"}
            for r in body.on_hand
        ]
        return IngestResponse(
            status="dry_run",
            summary=IngestSummary(total=len(body.on_hand), inserted=0, updated=0, errors=0),
            results=results,
        )

    item_ext_ids = list({r.item_external_id for r in body.on_hand})
    loc_ext_ids = list({r.location_external_id for r in body.on_hand})

    item_map = _batch_existing(db, "items", "external_id", "item_id", item_ext_ids)
    loc_map = _batch_existing(db, "locations", "external_id", "location_id", loc_ext_ids)

    results: list[dict] = []
    inserted = updated = errors_count = 0

    for i, row in enumerate(body.on_hand):
        row_errs = []
        if row.item_external_id not in item_map:
            row_errs.append(f"item_external_id '{row.item_external_id}' not found in DB")
        if row.location_external_id not in loc_map:
            row_errs.append(f"location_external_id '{row.location_external_id}' not found in DB")

        if row_errs:
            results.append({
                "item_external_id": row.item_external_id,
                "location_external_id": row.location_external_id,
                "row": i,
                "errors": row_errs,
                "action": "error",
            })
            errors_count += 1
            continue

        item_id = item_map[row.item_external_id]
        location_id = loc_map[row.location_external_id]

        # Upsert: one OnHandSupply node per (item, location, scenario)
        existing = db.execute(
            """
            SELECT node_id FROM nodes
            WHERE node_type = 'OnHandSupply'
              AND item_id = %s AND location_id = %s
              AND scenario_id = %s
              AND active = TRUE
            LIMIT 1
            """,
            (item_id, location_id, BASELINE_SCENARIO_ID),
        ).fetchone()

        if existing:
            db.execute(
                """
                UPDATE nodes
                SET quantity = %s, qty_uom = %s, time_ref = %s, updated_at = now()
                WHERE node_id = %s
                """,
                (row.quantity, row.uom, row.as_of_date, existing["node_id"]),
            )
            results.append({
                "item_external_id": row.item_external_id,
                "location_external_id": row.location_external_id,
                "node_id": str(existing["node_id"]),
                "action": "updated",
            })
            updated += 1
        else:
            node_id = uuid4()
            db.execute(
                """
                INSERT INTO nodes
                    (node_id, node_type, scenario_id, item_id, location_id,
                     quantity, qty_uom, time_grain, time_ref, active)
                VALUES (%s, 'OnHandSupply', %s, %s, %s, %s, %s, 'timeless', %s, TRUE)
                """,
                (node_id, BASELINE_SCENARIO_ID, item_id, location_id,
                 row.quantity, row.uom, row.as_of_date),
            )
            results.append({
                "item_external_id": row.item_external_id,
                "location_external_id": row.location_external_id,
                "node_id": str(node_id),
                "action": "inserted",
            })
            inserted += 1

    logger.info(
        "ingest.on_hand total=%d inserted=%d updated=%d errors=%d",
        len(body.on_hand), inserted, updated, errors_count,
    )
    total_status = "ok" if errors_count == 0 else ("partial" if (inserted + updated) > 0 else "error")
    return IngestResponse(
        status=total_status,
        summary=IngestSummary(
            total=len(body.on_hand),
            inserted=inserted,
            updated=updated,
            errors=errors_count,
        ),
        results=results,
    )


# ─────────────────────────────────────────────────────────────
# 6. POST /v1/ingest/purchase-orders
# ─────────────────────────────────────────────────────────────

VALID_PO_STATUSES = {"draft", "confirmed", "in_transit", "received", "cancelled"}


class PurchaseOrderRow(BaseModel):
    external_id: str
    item_external_id: str
    location_external_id: str
    supplier_external_id: str
    quantity: float
    uom: str = "EA"
    expected_delivery_date: date
    status: str = "confirmed"

    @field_validator("external_id")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


class IngestPurchaseOrdersRequest(BaseModel):
    purchase_orders: list[PurchaseOrderRow]
    dry_run: bool = False


@router.post("/purchase-orders", response_model=IngestResponse)
async def ingest_purchase_orders(
    body: IngestPurchaseOrdersRequest,
    db: psycopg.Connection = Depends(get_db),
    _token: str = Depends(require_auth),
) -> IngestResponse:
    """Upsert PurchaseOrderSupply nodes, tracked via external_references."""
    if body.dry_run:
        return IngestResponse(
            status="dry_run",
            summary=IngestSummary(total=len(body.purchase_orders), inserted=0, updated=0, errors=0),
            results=[{"external_id": po.external_id, "action": "dry_run"} for po in body.purchase_orders],
        )

    item_ext_ids = list({po.item_external_id for po in body.purchase_orders})
    loc_ext_ids = list({po.location_external_id for po in body.purchase_orders})
    sup_ext_ids = list({po.supplier_external_id for po in body.purchase_orders})

    item_map = _batch_existing(db, "items", "external_id", "item_id", item_ext_ids)
    loc_map = _batch_existing(db, "locations", "external_id", "location_id", loc_ext_ids)
    sup_map = _batch_existing(db, "suppliers", "external_id", "supplier_id", sup_ext_ids)

    # Fetch existing PO node references
    po_ext_ids = [po.external_id for po in body.purchase_orders]
    existing_refs_rows = db.execute(
        """
        SELECT external_id, internal_id FROM external_references
        WHERE entity_type = 'purchase_order' AND external_id = ANY(%s)
        """,
        (po_ext_ids,),
    ).fetchall()
    existing_refs: dict[str, UUID] = {r["external_id"]: r["internal_id"] for r in existing_refs_rows}

    results: list[dict] = []
    inserted = updated = errors_count = 0

    for i, po in enumerate(body.purchase_orders):
        row_errs = []
        if po.item_external_id not in item_map:
            row_errs.append(f"item_external_id '{po.item_external_id}' not found in DB")
        if po.location_external_id not in loc_map:
            row_errs.append(f"location_external_id '{po.location_external_id}' not found in DB")
        if po.supplier_external_id not in sup_map:
            row_errs.append(f"supplier_external_id '{po.supplier_external_id}' not found in DB")

        if row_errs:
            results.append({"external_id": po.external_id, "row": i, "errors": row_errs, "action": "error"})
            errors_count += 1
            continue

        item_id = item_map[po.item_external_id]
        location_id = loc_map[po.location_external_id]
        active = po.status != "cancelled"

        if po.external_id in existing_refs:
            node_id = existing_refs[po.external_id]
            db.execute(
                """
                UPDATE nodes
                SET quantity = %s, qty_uom = %s, time_ref = %s,
                    active = %s, updated_at = now()
                WHERE node_id = %s
                """,
                (po.quantity, po.uom, po.expected_delivery_date, active, node_id),
            )
            results.append({"external_id": po.external_id, "node_id": str(node_id), "action": "updated"})
            updated += 1
        else:
            node_id = uuid4()
            db.execute(
                """
                INSERT INTO nodes
                    (node_id, node_type, scenario_id, item_id, location_id,
                     quantity, qty_uom, time_grain, time_ref, active)
                VALUES (%s, 'PurchaseOrderSupply', %s, %s, %s, %s, %s, 'exact_date', %s, %s)
                """,
                (node_id, BASELINE_SCENARIO_ID, item_id, location_id,
                 po.quantity, po.uom, po.expected_delivery_date, active),
            )
            # Register external reference
            db.execute(
                """
                INSERT INTO external_references
                    (entity_type, external_id, source_system, internal_id)
                VALUES ('purchase_order', %s, 'ingest_api', %s)
                ON CONFLICT (entity_type, external_id, source_system) DO UPDATE
                    SET internal_id = EXCLUDED.internal_id, updated_at = now()
                """,
                (po.external_id, node_id),
            )
            results.append({"external_id": po.external_id, "node_id": str(node_id), "action": "inserted"})
            inserted += 1

    logger.info(
        "ingest.purchase_orders total=%d inserted=%d updated=%d errors=%d",
        len(body.purchase_orders), inserted, updated, errors_count,
    )
    total_status = "ok" if errors_count == 0 else ("partial" if (inserted + updated) > 0 else "error")
    return IngestResponse(
        status=total_status,
        summary=IngestSummary(
            total=len(body.purchase_orders),
            inserted=inserted,
            updated=updated,
            errors=errors_count,
        ),
        results=results,
    )


# ─────────────────────────────────────────────────────────────
# 7. POST /v1/ingest/forecast-demand
# ─────────────────────────────────────────────────────────────

VALID_TIME_GRAINS = {"exact_date", "day", "week", "month", "timeless"}
VALID_FORECAST_SOURCES = {"statistical", "consensus", "manual", "ml"}


class ForecastRow(BaseModel):
    item_external_id: str
    location_external_id: str
    quantity: float
    bucket_date: date
    time_grain: str = "week"
    source: str = "statistical"


class IngestForecastRequest(BaseModel):
    forecasts: list[ForecastRow]
    dry_run: bool = False


@router.post("/forecast-demand", response_model=IngestResponse)
async def ingest_forecast_demand(
    body: IngestForecastRequest,
    db: psycopg.Connection = Depends(get_db),
    _token: str = Depends(require_auth),
) -> IngestResponse:
    """Upsert ForecastDemand nodes. Keyed by (item, location, bucket_date, time_grain, scenario)."""
    errors: list[dict] = []
    valid_forecasts: list[ForecastRow] = []

    for i, fc in enumerate(body.forecasts):
        row_errs = []
        if fc.time_grain not in VALID_TIME_GRAINS:
            row_errs.append(f"time_grain '{fc.time_grain}' invalid; valid: {sorted(VALID_TIME_GRAINS)}")
        if row_errs:
            errors.append({
                "item_external_id": fc.item_external_id,
                "bucket_date": str(fc.bucket_date),
                "row": i,
                "errors": row_errs,
                "action": "error",
            })
        else:
            valid_forecasts.append(fc)

    if errors:
        return _error_response(len(body.forecasts), errors)

    if body.dry_run:
        return IngestResponse(
            status="dry_run",
            summary=IngestSummary(total=len(body.forecasts), inserted=0, updated=0, errors=0),
            results=[
                {"item_external_id": fc.item_external_id, "bucket_date": str(fc.bucket_date), "action": "dry_run"}
                for fc in valid_forecasts
            ],
        )

    item_ext_ids = list({fc.item_external_id for fc in valid_forecasts})
    loc_ext_ids = list({fc.location_external_id for fc in valid_forecasts})

    item_map = _batch_existing(db, "items", "external_id", "item_id", item_ext_ids)
    loc_map = _batch_existing(db, "locations", "external_id", "location_id", loc_ext_ids)

    results: list[dict] = []
    inserted = updated = errors_count = 0

    for i, fc in enumerate(valid_forecasts):
        row_errs = []
        if fc.item_external_id not in item_map:
            row_errs.append(f"item_external_id '{fc.item_external_id}' not found in DB")
        if fc.location_external_id not in loc_map:
            row_errs.append(f"location_external_id '{fc.location_external_id}' not found in DB")

        if row_errs:
            results.append({
                "item_external_id": fc.item_external_id,
                "bucket_date": str(fc.bucket_date),
                "row": i,
                "errors": row_errs,
                "action": "error",
            })
            errors_count += 1
            continue

        item_id = item_map[fc.item_external_id]
        location_id = loc_map[fc.location_external_id]

        existing = db.execute(
            """
            SELECT node_id FROM nodes
            WHERE node_type = 'ForecastDemand'
              AND item_id = %s AND location_id = %s
              AND scenario_id = %s
              AND time_ref = %s AND time_grain = %s
              AND active = TRUE
            LIMIT 1
            """,
            (item_id, location_id, BASELINE_SCENARIO_ID, fc.bucket_date, fc.time_grain),
        ).fetchone()

        if existing:
            db.execute(
                """
                UPDATE nodes
                SET quantity = %s, updated_at = now()
                WHERE node_id = %s
                """,
                (fc.quantity, existing["node_id"]),
            )
            results.append({
                "item_external_id": fc.item_external_id,
                "bucket_date": str(fc.bucket_date),
                "node_id": str(existing["node_id"]),
                "action": "updated",
            })
            updated += 1
        else:
            node_id = uuid4()
            db.execute(
                """
                INSERT INTO nodes
                    (node_id, node_type, scenario_id, item_id, location_id,
                     quantity, time_grain, time_ref, active)
                VALUES (%s, 'ForecastDemand', %s, %s, %s, %s, %s, %s, TRUE)
                """,
                (node_id, BASELINE_SCENARIO_ID, item_id, location_id,
                 fc.quantity, fc.time_grain, fc.bucket_date),
            )
            results.append({
                "item_external_id": fc.item_external_id,
                "bucket_date": str(fc.bucket_date),
                "node_id": str(node_id),
                "action": "inserted",
            })
            inserted += 1

    logger.info(
        "ingest.forecast_demand total=%d inserted=%d updated=%d errors=%d",
        len(body.forecasts), inserted, updated, errors_count,
    )
    total_status = "ok" if errors_count == 0 else ("partial" if (inserted + updated) > 0 else "error")
    return IngestResponse(
        status=total_status,
        summary=IngestSummary(
            total=len(body.forecasts),
            inserted=inserted,
            updated=updated,
            errors=errors_count,
        ),
        results=results,
    )
