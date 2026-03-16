# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _logger.info("RST pre-migrate 5.9.0: limpiando action y menu comprobantes")

    cr.execute("SELECT res_id FROM ir_model_data WHERE module='rst_loan_management' AND name='menu_rst_voucher_sequences'")
    row = cr.fetchone()
    if row:
        cr.execute("DELETE FROM ir_ui_menu_group_rel WHERE menu_id=%s", (row[0],))
        cr.execute("DELETE FROM ir_ui_menu WHERE id=%s", (row[0],))
        _logger.info("RST pre-migrate: menuitem borrado id=%s", row[0])

    cr.execute("SELECT res_id FROM ir_model_data WHERE module='rst_loan_management' AND name='action_rst_voucher_sequence'")
    row = cr.fetchone()
    if row:
        cr.execute("DELETE FROM ir_act_window WHERE id=%s", (row[0],))
        _logger.info("RST pre-migrate: action borrado id=%s", row[0])

    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module='rst_loan_management'
          AND name IN ('action_rst_voucher_sequence','menu_rst_voucher_sequences')
    """)
    _logger.info("RST pre-migrate 5.9.0: limpieza completa")
