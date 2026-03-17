# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RstLoanPaymentDenomination(models.Model):
    """Denominaciones de billetes/monedas para pagos en efectivo."""
    _name = 'rst.loan.payment.denomination'
    _description = 'Denominacion de Pago en Efectivo'
    _order = 'denomination desc'

    payment_id = fields.Many2one(
        'rst.loan.payment', string='Pago', ondelete='cascade', index=True)
    denomination = fields.Float('Denominacion', required=True)
    quantity = fields.Integer('Cantidad', required=True, default=0)
    subtotal = fields.Float('Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('denomination', 'quantity')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.denomination * rec.quantity


class RstLoanPaymentDenominationWizard(models.TransientModel):
    """Denominaciones temporales para el wizard de pago."""
    _name = 'rst.loan.payment.denomination.wizard'
    _description = 'Denominacion Wizard'
    _order = 'denomination desc'

    wizard_id = fields.Many2one(
        'rst.loan.payment.wizard', string='Wizard', ondelete='cascade')
    denomination = fields.Float('Denominacion', required=True)
    quantity = fields.Integer('Cantidad', required=True, default=0)
    subtotal = fields.Float('Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('denomination', 'quantity')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.denomination * rec.quantity
