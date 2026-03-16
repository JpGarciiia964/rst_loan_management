# -*- coding: utf-8 -*-
"""
Post-migración 16.0.5.8.0
Crea el action y menuitem de Secuencias de Comprobantes via ORM.

NOTA: 'post_migrate' NO es una clave válida en el manifest de Odoo 16.
Los únicos hooks válidos son: pre_init_hook, post_init_hook, uninstall_hook.
Para ejecutar código en cada upgrade se deben usar scripts de migración.
"""
def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Verificar que el modelo existe
    if 'rst.loan.voucher.sequence' not in env:
        return

    # Menu padre Configuración
    parent = env.ref('rst_loan_management.menu_rst_loans_config', raise_if_not_found=False)
    if not parent:
        return

    # Grupo Administrador
    admin_group = env.ref('rst_loan_management.group_rst_loan_manager', raise_if_not_found=False)

    # ── Crear Action ──────────────────────────────────────────────────────
    action = env['ir.actions.act_window'].create({
        'name': 'Secuencias de Comprobantes',
        'res_model': 'rst.loan.voucher.sequence',
        'view_mode': 'list,form',
        'type': 'ir.actions.act_window',
    })
    env['ir.model.data'].create({
        'module': 'rst_loan_management',
        'name': 'action_rst_voucher_sequence',
        'model': 'ir.actions.act_window',
        'res_id': action.id,
        'noupdate': False,
    })

    # ── Crear Menuitem ────────────────────────────────────────────────────
    menu = env['ir.ui.menu'].create({
        'name': 'Secuencias de Comprobantes',
        'parent_id': parent.id,
        'action': '%s,%s' % (action._name, action.id),
        'sequence': 20,
        'groups_id': [(6, 0, [admin_group.id])] if admin_group else [],
    })
    env['ir.model.data'].create({
        'module': 'rst_loan_management',
        'name': 'menu_rst_voucher_sequences',
        'model': 'ir.ui.menu',
        'res_id': menu.id,
        'noupdate': False,
    })
