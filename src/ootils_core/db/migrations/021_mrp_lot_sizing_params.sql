-- Migration 021: Add lot sizing parameters to item_planning_params
--
-- Phase 0 LotSizingEngine requires:
-- - economic_order_qty: EOQ value for the Economic Order Quantity rule
-- - lot_size_poq_periods: number of periods to cover for POQ rule
-- - order_multiple_qty: quantity multiple for the MULTIPLE rule
-- - frozen_time_fence_days: frozen zone boundary (days from today)
-- - slashed_time_fence_days: slashed zone boundary (days from today)
-- - forecast_consumption_strategy: strategy for consuming forecast
-- - consumption_window_days: window for forecast carry-over
-- - reorder_point_qty: reorder point for MIN_MAX rule
--
-- These columns may already exist from a prior run. All statements are idempotent.

-- Add lot_size_rule_type enum values if missing
ALTER TYPE lot_size_rule_type ADD VALUE IF NOT EXISTS 'POQ';
ALTER TYPE lot_size_rule_type ADD VALUE IF NOT EXISTS 'EOQ';
ALTER TYPE lot_size_rule_type ADD VALUE IF NOT EXISTS 'MULTIPLE';
ALTER TYPE lot_size_rule_type ADD VALUE IF NOT EXISTS 'FIXED_QTY';

-- Add missing columns to item_planning_params (idempotent — IF NOT EXISTS)
ALTER TABLE item_planning_params
    ADD COLUMN IF NOT EXISTS economic_order_qty NUMERIC(18,6) CHECK (economic_order_qty > 0),
    ADD COLUMN IF NOT EXISTS lot_size_poq_periods INTEGER DEFAULT 1 CHECK (lot_size_poq_periods > 0),
    ADD COLUMN IF NOT EXISTS order_multiple_qty NUMERIC(18,6) CHECK (order_multiple_qty > 0),
    ADD COLUMN IF NOT EXISTS frozen_time_fence_days INTEGER DEFAULT 7 CHECK (frozen_time_fence_days >= 0),
    ADD COLUMN IF NOT EXISTS slashed_time_fence_days INTEGER DEFAULT 30 CHECK (slashed_time_fence_days > 0),
    ADD COLUMN IF NOT EXISTS forecast_consumption_strategy TEXT DEFAULT 'max_only',
    ADD COLUMN IF NOT EXISTS consumption_window_days INTEGER DEFAULT 7 CHECK (consumption_window_days > 0),
    ADD COLUMN IF NOT EXISTS reorder_point_qty NUMERIC(18,6) CHECK (reorder_point_qty >= 0);

-- mrp_runs table (idempotent)
CREATE TABLE IF NOT EXISTS mrp_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL,
    location_id UUID,
    run_status TEXT NOT NULL DEFAULT 'RUNNING',
    run_type TEXT NOT NULL DEFAULT 'APICS',
    horizon_days INTEGER NOT NULL DEFAULT 90,
    bucket_grain TEXT NOT NULL DEFAULT 'week',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- mrp_bucket_records table (idempotent)
CREATE TABLE IF NOT EXISTS mrp_bucket_records (
    bucket_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES mrp_runs(run_id),
    item_id UUID NOT NULL,
    location_id UUID NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    bucket_sequence INTEGER NOT NULL,
    gross_requirements NUMERIC(18,6) NOT NULL DEFAULT 0,
    scheduled_receipts NUMERIC(18,6) NOT NULL DEFAULT 0,
    projected_on_hand NUMERIC(18,6) NOT NULL DEFAULT 0,
    net_requirements NUMERIC(18,6) NOT NULL DEFAULT 0,
    planned_order_receipts NUMERIC(18,6) NOT NULL DEFAULT 0,
    planned_order_releases NUMERIC(18,6) NOT NULL DEFAULT 0,
    has_shortage BOOLEAN NOT NULL DEFAULT false,
    shortage_qty NUMERIC(18,6) NOT NULL DEFAULT 0,
    llc INTEGER NOT NULL DEFAULT 0,
    time_fence_zone TEXT,
    lot_size_rule_applied TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- mrp_action_messages table (idempotent)
CREATE TABLE IF NOT EXISTS mrp_action_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES mrp_runs(run_id),
    item_id UUID NOT NULL,
    location_id UUID,
    message_type TEXT NOT NULL,
    message_date DATE NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    quantity NUMERIC(18,6) NOT NULL DEFAULT 0,
    shortage_qty NUMERIC(18,6) NOT NULL DEFAULT 0,
    time_fence_zone TEXT,
    llc INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_mrp_runs_scenario ON mrp_runs (scenario_id);
CREATE INDEX IF NOT EXISTS idx_mrp_runs_status ON mrp_runs (run_status);
CREATE INDEX IF NOT EXISTS idx_mrp_bucket_records_run ON mrp_bucket_records (run_id);
CREATE INDEX IF NOT EXISTS idx_mrp_bucket_records_item ON mrp_bucket_records (item_id, period_start);
CREATE INDEX IF NOT EXISTS idx_mrp_action_messages_run ON mrp_action_messages (run_id);
