"""
tests/integration/test_ingest.py — Integration tests for POST /v1/ingest/* endpoints.

Requires a running PostgreSQL instance with migrations applied.
Set DATABASE_URL before running:
    DATABASE_URL=postgresql://ootils:ootils@localhost:5432/ootils pytest tests/integration/test_ingest.py -v
"""
from __future__ import annotations

import os
from uuid import uuid4

import pytest

from .conftest import requires_db, DB_AVAILABLE, TEST_DB_URL

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ingest_client(migrated_db):
    """Module-scoped TestClient wired to a migrated test DB, no seed data needed."""
    os.environ["DATABASE_URL"] = migrated_db
    os.environ["OOTILS_API_TOKEN"] = "test-token"

    from ootils_core.api.app import create_app
    from ootils_core.api.dependencies import get_db
    from ootils_core.db.connection import OotilsDB
    from fastapi.testclient import TestClient

    app = create_app()

    def override_db():
        db = OotilsDB(migrated_db)
        with db.conn() as c:
            yield c

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def auth():
    return {"Authorization": "Bearer test-token"}


# Unique prefix to avoid collision between test runs
PREFIX = str(uuid4())[:8]


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def uid(base: str) -> str:
    return f"{PREFIX}-{base}"


# ─────────────────────────────────────────────────────────────
# POST /v1/ingest/items
# ─────────────────────────────────────────────────────────────

@requires_db
def test_ingest_items_insert(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/items",
        json={
            "items": [
                {"external_id": uid("SKU-001"), "name": "Pump 12V", "item_type": "finished_good", "uom": "EA", "status": "active"},
                {"external_id": uid("SKU-002"), "name": "Gasket", "item_type": "component", "uom": "EA", "status": "active"},
            ],
            "conflict_strategy": "upsert",
            "dry_run": False,
        },
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    assert data["summary"]["total"] == 2
    assert data["summary"]["inserted"] == 2
    assert data["summary"]["errors"] == 0
    assert all(r["action"] == "inserted" for r in data["results"])
    assert all("item_id" in r for r in data["results"])


@requires_db
def test_ingest_items_update(ingest_client, auth):
    # First insert
    ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("SKU-UPD"), "name": "Old Name", "item_type": "component", "uom": "EA", "status": "active"}]},
        headers=auth,
    )
    # Then update
    resp = ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("SKU-UPD"), "name": "New Name", "item_type": "component", "uom": "KG", "status": "active"}]},
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["updated"] == 1
    assert data["results"][0]["action"] == "updated"


@requires_db
def test_ingest_items_dry_run(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/items",
        json={
            "items": [{"external_id": uid("SKU-DRY"), "name": "Dry", "item_type": "component", "uom": "EA", "status": "active"}],
            "dry_run": True,
        },
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dry_run"
    assert data["summary"]["inserted"] == 0


@requires_db
def test_ingest_items_invalid_type(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("SKU-BAD"), "name": "Bad", "item_type": "invalid_type", "uom": "EA", "status": "active"}]},
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["summary"]["errors"] == 1


@requires_db
def test_ingest_items_no_auth(ingest_client):
    resp = ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": "x", "name": "x", "item_type": "component", "uom": "EA", "status": "active"}]},
    )
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────
# POST /v1/ingest/locations
# ─────────────────────────────────────────────────────────────

@requires_db
def test_ingest_locations_insert(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/locations",
        json={
            "locations": [
                {"external_id": uid("DC-ATL"), "name": "Atlanta DC", "location_type": "dc", "country": "US", "timezone": "America/New_York"},
            ],
            "dry_run": False,
        },
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["summary"]["inserted"] == 1
    assert "location_id" in data["results"][0]


@requires_db
def test_ingest_locations_update(ingest_client, auth):
    ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("DC-UPD"), "name": "Old DC", "location_type": "dc"}]},
        headers=auth,
    )
    resp = ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("DC-UPD"), "name": "New DC", "location_type": "warehouse"}]},
        headers=auth,
    )
    assert resp.status_code == 200
    assert resp.json()["summary"]["updated"] == 1


@requires_db
def test_ingest_locations_invalid_type(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("DC-BAD"), "name": "Bad", "location_type": "invalid"}]},
        headers=auth,
    )
    assert resp.status_code == 200
    assert resp.json()["summary"]["errors"] == 1


@requires_db
def test_ingest_locations_dry_run(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("DC-DRY"), "name": "Dry", "location_type": "dc"}], "dry_run": True},
        headers=auth,
    )
    assert resp.json()["status"] == "dry_run"


# ─────────────────────────────────────────────────────────────
# POST /v1/ingest/suppliers
# ─────────────────────────────────────────────────────────────

@requires_db
def test_ingest_suppliers_insert(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/suppliers",
        json={
            "suppliers": [
                {"external_id": uid("VENDOR-001"), "name": "ACME Corp", "lead_time_days": 7, "reliability_score": 0.97, "status": "active"},
            ],
        },
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["summary"]["inserted"] == 1


@requires_db
def test_ingest_suppliers_update(ingest_client, auth):
    ingest_client.post(
        "/v1/ingest/suppliers",
        json={"suppliers": [{"external_id": uid("VENDOR-UPD"), "name": "Old Vendor", "status": "active"}]},
        headers=auth,
    )
    resp = ingest_client.post(
        "/v1/ingest/suppliers",
        json={"suppliers": [{"external_id": uid("VENDOR-UPD"), "name": "New Vendor", "status": "inactive"}]},
        headers=auth,
    )
    assert resp.json()["summary"]["updated"] == 1


@requires_db
def test_ingest_suppliers_invalid_reliability(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/suppliers",
        json={"suppliers": [{"external_id": uid("VENDOR-BAD"), "name": "Bad", "reliability_score": 1.5, "status": "active"}]},
        headers=auth,
    )
    assert resp.json()["summary"]["errors"] == 1


@requires_db
def test_ingest_suppliers_invalid_status(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/suppliers",
        json={"suppliers": [{"external_id": uid("VENDOR-BAD2"), "name": "Bad", "status": "unknown"}]},
        headers=auth,
    )
    assert resp.json()["summary"]["errors"] == 1


@requires_db
def test_ingest_suppliers_dry_run(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/suppliers",
        json={"suppliers": [{"external_id": uid("VENDOR-DRY"), "name": "Dry", "status": "active"}], "dry_run": True},
        headers=auth,
    )
    assert resp.json()["status"] == "dry_run"


# ─────────────────────────────────────────────────────────────
# POST /v1/ingest/supplier-items
# ─────────────────────────────────────────────────────────────

@requires_db
def test_ingest_supplier_items_insert(ingest_client, auth):
    # Setup: create item + supplier first
    ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("SI-ITEM"), "name": "Item for SI", "item_type": "component", "uom": "EA", "status": "active"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/suppliers",
        json={"suppliers": [{"external_id": uid("SI-VENDOR"), "name": "Vendor for SI", "status": "active"}]},
        headers=auth,
    )

    resp = ingest_client.post(
        "/v1/ingest/supplier-items",
        json={
            "supplier_items": [
                {
                    "supplier_external_id": uid("SI-VENDOR"),
                    "item_external_id": uid("SI-ITEM"),
                    "lead_time_days": 7,
                    "moq": 50,
                    "unit_cost": 125.0,
                    "is_preferred": True,
                    "currency": "EUR",
                }
            ]
        },
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["summary"]["inserted"] == 1


@requires_db
def test_ingest_supplier_items_fk_missing(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/supplier-items",
        json={
            "supplier_items": [
                {
                    "supplier_external_id": "DOES-NOT-EXIST",
                    "item_external_id": "ALSO-MISSING",
                    "lead_time_days": 5,
                }
            ]
        },
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["errors"] == 1
    assert data["results"][0]["action"] == "error"


@requires_db
def test_ingest_supplier_items_dry_run(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/supplier-items",
        json={
            "supplier_items": [
                {"supplier_external_id": "X", "item_external_id": "Y", "lead_time_days": 1}
            ],
            "dry_run": True,
        },
        headers=auth,
    )
    assert resp.json()["status"] == "dry_run"


# ─────────────────────────────────────────────────────────────
# POST /v1/ingest/on-hand
# ─────────────────────────────────────────────────────────────

@requires_db
def test_ingest_on_hand_insert(ingest_client, auth):
    # Setup: create item + location
    ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("OH-ITEM"), "name": "OH Item", "item_type": "finished_good", "uom": "EA", "status": "active"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("OH-LOC"), "name": "OH Location", "location_type": "dc"}]},
        headers=auth,
    )

    resp = ingest_client.post(
        "/v1/ingest/on-hand",
        json={
            "on_hand": [
                {
                    "item_external_id": uid("OH-ITEM"),
                    "location_external_id": uid("OH-LOC"),
                    "quantity": 150.0,
                    "uom": "EA",
                    "as_of_date": "2026-04-07",
                }
            ]
        },
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["summary"]["inserted"] == 1
    assert "node_id" in data["results"][0]


@requires_db
def test_ingest_on_hand_update(ingest_client, auth):
    # Insert first
    ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("OH-UPD-ITEM"), "name": "OH UPD Item", "item_type": "finished_good", "uom": "EA", "status": "active"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("OH-UPD-LOC"), "name": "OH UPD Loc", "location_type": "dc"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/on-hand",
        json={"on_hand": [{"item_external_id": uid("OH-UPD-ITEM"), "location_external_id": uid("OH-UPD-LOC"), "quantity": 100.0, "uom": "EA", "as_of_date": "2026-04-07"}]},
        headers=auth,
    )
    # Update
    resp = ingest_client.post(
        "/v1/ingest/on-hand",
        json={"on_hand": [{"item_external_id": uid("OH-UPD-ITEM"), "location_external_id": uid("OH-UPD-LOC"), "quantity": 200.0, "uom": "EA", "as_of_date": "2026-04-07"}]},
        headers=auth,
    )
    assert resp.json()["summary"]["updated"] == 1


@requires_db
def test_ingest_on_hand_fk_missing(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/on-hand",
        json={"on_hand": [{"item_external_id": "MISSING", "location_external_id": "MISSING", "quantity": 1.0, "uom": "EA", "as_of_date": "2026-04-07"}]},
        headers=auth,
    )
    data = resp.json()
    assert data["summary"]["errors"] == 1


# ─────────────────────────────────────────────────────────────
# POST /v1/ingest/purchase-orders
# ─────────────────────────────────────────────────────────────

@requires_db
def test_ingest_purchase_orders_insert(ingest_client, auth):
    # Setup
    ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("PO-ITEM"), "name": "PO Item", "item_type": "finished_good", "uom": "EA", "status": "active"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("PO-LOC"), "name": "PO Location", "location_type": "dc"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/suppliers",
        json={"suppliers": [{"external_id": uid("PO-VENDOR"), "name": "PO Vendor", "status": "active"}]},
        headers=auth,
    )

    resp = ingest_client.post(
        "/v1/ingest/purchase-orders",
        json={
            "purchase_orders": [
                {
                    "external_id": uid("PO-2026-001"),
                    "item_external_id": uid("PO-ITEM"),
                    "location_external_id": uid("PO-LOC"),
                    "supplier_external_id": uid("PO-VENDOR"),
                    "quantity": 500.0,
                    "uom": "EA",
                    "expected_delivery_date": "2026-04-20",
                    "status": "confirmed",
                }
            ]
        },
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["summary"]["inserted"] == 1
    assert "node_id" in data["results"][0]


@requires_db
def test_ingest_purchase_orders_update(ingest_client, auth):
    # Re-ingest same external_id
    ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("PO2-ITEM"), "name": "PO2 Item", "item_type": "finished_good", "uom": "EA", "status": "active"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("PO2-LOC"), "name": "PO2 Loc", "location_type": "dc"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/suppliers",
        json={"suppliers": [{"external_id": uid("PO2-VENDOR"), "name": "PO2 Vendor", "status": "active"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/purchase-orders",
        json={"purchase_orders": [{"external_id": uid("PO-UPD"), "item_external_id": uid("PO2-ITEM"), "location_external_id": uid("PO2-LOC"), "supplier_external_id": uid("PO2-VENDOR"), "quantity": 100.0, "uom": "EA", "expected_delivery_date": "2026-04-20", "status": "confirmed"}]},
        headers=auth,
    )
    resp = ingest_client.post(
        "/v1/ingest/purchase-orders",
        json={"purchase_orders": [{"external_id": uid("PO-UPD"), "item_external_id": uid("PO2-ITEM"), "location_external_id": uid("PO2-LOC"), "supplier_external_id": uid("PO2-VENDOR"), "quantity": 200.0, "uom": "EA", "expected_delivery_date": "2026-04-25", "status": "confirmed"}]},
        headers=auth,
    )
    assert resp.json()["summary"]["updated"] == 1


@requires_db
def test_ingest_purchase_orders_fk_missing(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/purchase-orders",
        json={"purchase_orders": [{"external_id": "PO-MISS", "item_external_id": "MISS", "location_external_id": "MISS", "supplier_external_id": "MISS", "quantity": 1.0, "uom": "EA", "expected_delivery_date": "2026-04-20", "status": "confirmed"}]},
        headers=auth,
    )
    assert resp.json()["summary"]["errors"] == 1


# ─────────────────────────────────────────────────────────────
# POST /v1/ingest/forecast-demand
# ─────────────────────────────────────────────────────────────

@requires_db
def test_ingest_forecast_demand_insert(ingest_client, auth):
    ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("FC-ITEM"), "name": "FC Item", "item_type": "finished_good", "uom": "EA", "status": "active"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("FC-LOC"), "name": "FC Location", "location_type": "dc"}]},
        headers=auth,
    )

    resp = ingest_client.post(
        "/v1/ingest/forecast-demand",
        json={
            "forecasts": [
                {
                    "item_external_id": uid("FC-ITEM"),
                    "location_external_id": uid("FC-LOC"),
                    "quantity": 200.0,
                    "bucket_date": "2026-04-14",
                    "time_grain": "week",
                    "source": "statistical",
                }
            ]
        },
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["summary"]["inserted"] == 1
    assert "node_id" in data["results"][0]


@requires_db
def test_ingest_forecast_demand_update(ingest_client, auth):
    ingest_client.post(
        "/v1/ingest/items",
        json={"items": [{"external_id": uid("FC2-ITEM"), "name": "FC2 Item", "item_type": "finished_good", "uom": "EA", "status": "active"}]},
        headers=auth,
    )
    ingest_client.post(
        "/v1/ingest/locations",
        json={"locations": [{"external_id": uid("FC2-LOC"), "name": "FC2 Location", "location_type": "dc"}]},
        headers=auth,
    )
    # Insert
    ingest_client.post(
        "/v1/ingest/forecast-demand",
        json={"forecasts": [{"item_external_id": uid("FC2-ITEM"), "location_external_id": uid("FC2-LOC"), "quantity": 100.0, "bucket_date": "2026-04-14", "time_grain": "week"}]},
        headers=auth,
    )
    # Update
    resp = ingest_client.post(
        "/v1/ingest/forecast-demand",
        json={"forecasts": [{"item_external_id": uid("FC2-ITEM"), "location_external_id": uid("FC2-LOC"), "quantity": 300.0, "bucket_date": "2026-04-14", "time_grain": "week"}]},
        headers=auth,
    )
    assert resp.json()["summary"]["updated"] == 1


@requires_db
def test_ingest_forecast_demand_invalid_grain(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/forecast-demand",
        json={"forecasts": [{"item_external_id": "X", "location_external_id": "Y", "quantity": 1.0, "bucket_date": "2026-04-14", "time_grain": "invalid_grain"}]},
        headers=auth,
    )
    assert resp.json()["summary"]["errors"] == 1


@requires_db
def test_ingest_forecast_demand_dry_run(ingest_client, auth):
    resp = ingest_client.post(
        "/v1/ingest/forecast-demand",
        json={"forecasts": [{"item_external_id": "X", "location_external_id": "Y", "quantity": 1.0, "bucket_date": "2026-04-14", "time_grain": "week"}], "dry_run": True},
        headers=auth,
    )
    assert resp.json()["status"] == "dry_run"
