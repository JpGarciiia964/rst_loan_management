# -*- coding: utf-8 -*-
"""
Pre-migration: 16.0.3.0.0 → 16.0.4.0.0

IMPORTANTE: No usar COMMIT/ROLLBACK explícitos aquí.
Odoo maneja su propia transacción. Usar SAVEPOINTS para
aislar errores por columna sin romper la transacción principal.
"""


def migrate(cr, version):
    """
    Agrega columnas nuevas ANTES de que Odoo valide las vistas XML.
    Usa savepoints para que un fallo en una columna no cancele las demás.
    """

    columnas = [
        # tabla,                    columna,                        tipo
        # ── rst_loan_type ─────────────────────────────────────────────────
        ("rst_loan_type",           "grace_days",                   "INTEGER DEFAULT 0"),
        ("rst_loan_type",           "late_fee_type",                "VARCHAR DEFAULT 'percentage'"),
        ("rst_loan_type",           "late_fee_value",               "DOUBLE PRECISION DEFAULT 0.0"),

        # ── rst_loan_contract ──────────────────────────────────────────────
        ("rst_loan_contract",       "grace_days",                   "INTEGER DEFAULT 0"),
        ("rst_loan_contract",       "late_fee_type",                "VARCHAR DEFAULT 'percentage'"),
        ("rst_loan_contract",       "late_fee_value",               "DOUBLE PRECISION DEFAULT 0.0"),
        ("rst_loan_contract",       "journal_id",                   "INTEGER"),
        ("rst_loan_contract",       "income_account_id",            "INTEGER"),
        ("rst_loan_contract",       "cancellation_penalty_type",    "VARCHAR DEFAULT 'percentage'"),
        ("rst_loan_contract",       "cancellation_penalty_value",   "DOUBLE PRECISION DEFAULT 0.0"),

        # ── rst_loan_schedule ──────────────────────────────────────────────
        ("rst_loan_schedule",       "invoice_id",                   "INTEGER"),
        ("rst_loan_schedule",       "invoice_state",                "VARCHAR"),
        ("rst_loan_schedule",       "late_fee_applied",             "BOOLEAN DEFAULT FALSE"),
        ("rst_loan_schedule",       "late_fee_amount",              "DOUBLE PRECISION DEFAULT 0.0"),

        # ── rst_loan_payment ───────────────────────────────────────────────
        ("rst_loan_payment",        "invoice_id",                   "INTEGER"),
        ("rst_loan_payment",        "balance_before",               "DOUBLE PRECISION DEFAULT 0.0"),
        ("rst_loan_payment",        "balance_after",                "DOUBLE PRECISION DEFAULT 0.0"),

        # ── rst_loan_document_type ─────────────────────────────────────────
        ("rst_loan_document_type",  "is_cedula",                    "BOOLEAN DEFAULT FALSE"),
    ]

    for tabla, columna, tipo in columnas:
        sp = f"sp_{tabla}_{columna}"
        try:
            cr.execute(f"SAVEPOINT {sp}")
            cr.execute(
                f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {tipo}"
            )
            cr.execute(f"RELEASE SAVEPOINT {sp}")
        except Exception:
            # Columna ya existe o tabla aún no creada (instalación nueva) → ignorar
            cr.execute(f"ROLLBACK TO SAVEPOINT {sp}")
