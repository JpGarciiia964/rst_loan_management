# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    rst_loan_supervisor_id = fields.Many2one(
        'res.users', string='Supervisor de Prestamos',
        help='Supervisor asignado para aprobar cancelaciones de contratos. '
             'Si no se asigna, todos los supervisores podran ver los contratos de este oficial.'
    )
