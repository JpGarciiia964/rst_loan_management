# -*- coding: utf-8 -*-
"""
Pre-migration script for rst_loan_management 16.0.3.0.0
Adds new columns to existing tables BEFORE Odoo validates the views.
This allows upgrading from 16.0.1.0.0 to 16.0.3.0.0 without reinstalling.
"""


def migrate(cr, version):
    """Add new columns to all tables before model loading and view validation."""

    statements = [
        # ── rst.loan.contract ──────────────────────────────────────────────
        "ALTER TABLE rst_loan_contract ADD COLUMN IF NOT EXISTS grace_days INTEGER DEFAULT 0",
        "ALTER TABLE rst_loan_contract ADD COLUMN IF NOT EXISTS late_fee_type VARCHAR DEFAULT 'percentage'",
        "ALTER TABLE rst_loan_contract ADD COLUMN IF NOT EXISTS late_fee_value FLOAT DEFAULT 0.0",
        "ALTER TABLE rst_loan_contract ADD COLUMN IF NOT EXISTS journal_id INTEGER",
        "ALTER TABLE rst_loan_contract ADD COLUMN IF NOT EXISTS income_account_id INTEGER",
        "ALTER TABLE rst_loan_contract ADD COLUMN IF NOT EXISTS cancellation_penalty_type VARCHAR DEFAULT 'percentage'",
        "ALTER TABLE rst_loan_contract ADD COLUMN IF NOT EXISTS cancellation_penalty_value FLOAT DEFAULT 0.0",

        # ── rst.loan.type ──────────────────────────────────────────────────
        "ALTER TABLE rst_loan_type ADD COLUMN IF NOT EXISTS grace_days INTEGER DEFAULT 0",
        "ALTER TABLE rst_loan_type ADD COLUMN IF NOT EXISTS late_fee_type VARCHAR DEFAULT 'percentage'",
        "ALTER TABLE rst_loan_type ADD COLUMN IF NOT EXISTS late_fee_value FLOAT DEFAULT 0.0",

        # ── rst.loan.schedule ─────────────────────────────────────────────
        "ALTER TABLE rst_loan_schedule ADD COLUMN IF NOT EXISTS invoice_id INTEGER",
        "ALTER TABLE rst_loan_schedule ADD COLUMN IF NOT EXISTS invoice_state VARCHAR",
        "ALTER TABLE rst_loan_schedule ADD COLUMN IF NOT EXISTS late_fee_applied BOOLEAN DEFAULT FALSE",
        "ALTER TABLE rst_loan_schedule ADD COLUMN IF NOT EXISTS late_fee_amount FLOAT DEFAULT 0.0",

        # ── rst.loan.payment ──────────────────────────────────────────────
        "ALTER TABLE rst_loan_payment ADD COLUMN IF NOT EXISTS invoice_id INTEGER",
        "ALTER TABLE rst_loan_payment ADD COLUMN IF NOT EXISTS balance_before FLOAT DEFAULT 0.0",
        "ALTER TABLE rst_loan_payment ADD COLUMN IF NOT EXISTS balance_after FLOAT DEFAULT 0.0",

        # ── rst.loan.document.type ────────────────────────────────────────
        "ALTER TABLE rst_loan_document_type ADD COLUMN IF NOT EXISTS is_cedula BOOLEAN DEFAULT FALSE",
    ]

    for sql in statements:
        try:
            cr.execute(sql)
        except Exception as e:
            # Column may already exist or table may not exist yet (fresh install)
            pass
