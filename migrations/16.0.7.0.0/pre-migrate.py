# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("RST Loan: Pre-migrate 16.0.7.0.0")

    # Agregar columna rst_loan_supervisor_id a res_users
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS rst_loan_supervisor_id INTEGER
    """)
    _logger.info("  Added column res_users.rst_loan_supervisor_id")

    # Agregar columna cancel_state a rst_loan_contract
    cr.execute("""
        ALTER TABLE rst_loan_contract
        ADD COLUMN IF NOT EXISTS cancel_state VARCHAR DEFAULT 'none'
    """)
    _logger.info("  Added column rst_loan_contract.cancel_state")

    # Agregar columnas nuevas de payment
    for col in ['amount_penalty', 'is_full_payoff']:
        cr.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'rst_loan_payment' AND column_name = %s
        """, (col,))
        if not cr.fetchone():
            if col == 'is_full_payoff':
                cr.execute('ALTER TABLE rst_loan_payment ADD COLUMN %s BOOLEAN DEFAULT FALSE' % col)
            else:
                cr.execute('ALTER TABLE rst_loan_payment ADD COLUMN %s NUMERIC DEFAULT 0' % col)
            _logger.info("  Added column rst_loan_payment.%s", col)

    # Limpiar ir_model_data conflictivos
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'rst_loan_management'
          AND name IN (
              'rule_rst_loan_contract_supervisor',
              'view_users_form_rst_loan'
          )
    """)
