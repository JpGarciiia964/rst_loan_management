# -*- coding: utf-8 -*-
"""
Pre-migrate v6.0.0:
- Limpia registros de ir_model_data que causan constraint duplicados
- Elimina cron de facturas que ya no existe
- Elimina columnas de facturación (account) obsoletas
"""
import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("RST Loan: Pre-migrate 16.0.6.0.0")

    # 1. Eliminar cron de generación de facturas ANTES de limpiar ir_model_data
    _logger.info("  Eliminando cron de facturas obsoleto...")
    cr.execute("""
        DELETE FROM ir_cron WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'rst_loan_management'
              AND name = 'cron_generate_invoices'
        )
    """)

    # 2. Limpiar registros en ir_model_data que causan constraint errors al reinstalar
    _logger.info("  Limpiando ir_model_data conflictivos...")
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'rst_loan_management'
          AND name IN (
              'action_rst_voucher_sequence',
              'view_rst_voucher_sequence_list',
              'view_rst_voucher_sequence_form',
              'cron_generate_invoices',
              'action_rst_loan_schedule_report',
              'access_rst_loan_voucher_seq_manager',
              'access_rst_loan_voucher_seq_viewer',
              'product_loan_installment'
          )
    """)
    _logger.info("  Eliminados %d registros de ir_model_data", cr.rowcount)

    # 3. Eliminar columnas de account que ya no existen en los modelos
    _logger.info("  Eliminando columnas de facturacion...")
    columns_to_drop = [
        ("rst_loan_contract", "journal_id"),
        ("rst_loan_contract", "income_account_id"),
        ("rst_loan_schedule", "invoice_id"),
        ("rst_loan_schedule", "invoice_state"),
        ("rst_loan_payment", "invoice_id"),
    ]
    for table, column in columns_to_drop:
        cr.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        """, (table, column))
        if cr.fetchone():
            cr.execute('ALTER TABLE "%s" DROP COLUMN IF EXISTS "%s"' % (table, column))
            _logger.info("  Dropped column %s.%s", table, column)
