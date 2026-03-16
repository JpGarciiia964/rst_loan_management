# -*- coding: utf-8 -*-
def migrate(cr, version):
    """Limpia action y menu anteriores para que post-migrate los recree limpios."""
    cr.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = 'rst_loan_management' AND name = 'menu_rst_voucher_sequences'
    """)
    row = cr.fetchone()
    if row:
        cr.execute("DELETE FROM ir_ui_menu_group_rel WHERE menu_id = %s", (row[0],))
        cr.execute("DELETE FROM ir_ui_menu WHERE id = %s", (row[0],))

    cr.execute("""
        SELECT res_id FROM ir_model_data
        WHERE module = 'rst_loan_management' AND name = 'action_rst_voucher_sequence'
    """)
    row = cr.fetchone()
    if row:
        cr.execute("DELETE FROM ir_act_window WHERE id = %s", (row[0],))

    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'rst_loan_management'
          AND name IN ('action_rst_voucher_sequence', 'menu_rst_voucher_sequences')
    """)
