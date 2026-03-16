# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Colores de documentos impresos ──────────────────────────────
    rst_primary_color = fields.Char(
        string='Color Principal',
        config_parameter='rst_loan_management.primary_color',
        default='#1a3a5c',
        help='Color principal para encabezados y barras de los documentos impresos (ej: #1a3a5c).'
    )
    rst_secondary_color = fields.Char(
        string='Color Secundario',
        config_parameter='rst_loan_management.secondary_color',
        default='#2980b9',
        help='Color secundario para acentos y degradados (ej: #2980b9).'
    )
    rst_accent_color = fields.Char(
        string='Color de Acento',
        config_parameter='rst_loan_management.accent_color',
        default='#27ae60',
        help='Color para elementos positivos como cuotas y totales (ej: #27ae60).'
    )
    rst_danger_color = fields.Char(
        string='Color de Alerta',
        config_parameter='rst_loan_management.danger_color',
        default='#c0392b',
        help='Color para totales a pagar y alertas (ej: #c0392b).'
    )
