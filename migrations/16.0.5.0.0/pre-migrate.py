# -*- coding: utf-8 -*-
"""
Pre-migration 16.0.4.0.0 → 16.0.5.0.0
Agrega columnas nuevas al contrato:
  - total_late_fees    (suma de moras acumuladas)
  - days_to_next_due   (días al próximo vencimiento)
  - paid_installments  (cuotas pagadas)
"""


def migrate(cr, version):
    new_columns = [
        ("rst_loan_contract", "total_late_fees",   "NUMERIC(18,2) DEFAULT 0"),
        ("rst_loan_contract", "days_to_next_due",  "INTEGER DEFAULT 0"),
        ("rst_loan_contract", "paid_installments", "INTEGER DEFAULT 0"),
        # loan_type mora fields (may already exist from previous migration)
        ("rst_loan_type", "grace_days",      "INTEGER DEFAULT 0"),
        ("rst_loan_type", "late_fee_type",   "VARCHAR(20) DEFAULT 'percentage'"),
        ("rst_loan_type", "late_fee_value",  "NUMERIC(18,4) DEFAULT 0"),
    ]
    for table, col, col_def in new_columns:
        cr.execute("SAVEPOINT pre_col")
        try:
            cr.execute(
                f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"
            )
            cr.execute("RELEASE SAVEPOINT pre_col")
        except Exception:
            cr.execute("ROLLBACK TO SAVEPOINT pre_col")
