# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    """Extiende res.partner para clasificación de clientes según historial de préstamos."""
    _inherit = 'res.partner'

    # ── Clasificación RST ─────────────────────────────────────────────────
    loan_currency_id = fields.Many2one(
        'res.currency', string='Moneda Préstamos',
        default=lambda self: self.env.company.currency_id,
    )
    loan_classification = fields.Selection([
        ('preferred', 'Preferencial'),
        ('normal', 'Normal'),
        ('delinquent', 'Moroso'),
    ], string='Clasificación de Crédito', default=False,
        tracking=True,
        help='Clasificación automática basada en el historial de pagos de préstamos.'
    )
    loan_classification_color = fields.Integer(
        compute='_compute_classification_color'
    )
    total_active_loans = fields.Integer(
        compute='_compute_loan_stats', string='Préstamos Activos'
    )
    total_loan_balance = fields.Monetary(
        compute='_compute_loan_stats', string='Saldo Total en Préstamos',
        currency_field='loan_currency_id'
    )
    overdue_payments_count = fields.Integer(
        compute='_compute_loan_stats', string='Cuotas Vencidas'
    )
    loan_ids = fields.One2many(
        'rst.loan.contract', 'partner_id', string='Contratos de Préstamo'
    )
    loan_count = fields.Integer(
        compute='_compute_loan_stats', string='Total Préstamos'
    )

    # =========================================================
    # Computed
    # =========================================================

    @api.depends('loan_classification')
    def _compute_classification_color(self):
        color_map = {
            'preferred': 10,  # Green
            'normal': 4,      # Blue
            'delinquent': 1,  # Red
            False: 0,
        }
        for rec in self:
            rec.loan_classification_color = color_map.get(rec.loan_classification, 0)

    @api.depends('loan_ids', 'loan_ids.state', 'loan_ids.balance_remaining',
                 'loan_ids.overdue_installments')
    def _compute_loan_stats(self):
        Contract = self.env['rst.loan.contract']
        Schedule = self.env['rst.loan.schedule']
        for rec in self:
            active_contracts = Contract.search([
                ('partner_id', '=', rec.id),
                ('state', 'in', ['active', 'overdue']),
            ])
            rec.total_active_loans = len(active_contracts)
            rec.total_loan_balance = sum(active_contracts.mapped('balance_remaining'))
            rec.overdue_payments_count = sum(active_contracts.mapped('overdue_installments'))
            rec.loan_count = Contract.search_count([('partner_id', '=', rec.id)])

    # =========================================================
    # Classification Logic
    # =========================================================

    def _compute_loan_classification(self):
        """Actualiza la clasificación del cliente según su historial."""
        for rec in self:
            contracts = self.env['rst.loan.contract'].search([
                ('partner_id', '=', rec.id),
                ('state', 'in', ['active', 'overdue', 'paid']),
            ])
            if not contracts:
                continue

            all_schedules = self.env['rst.loan.schedule'].search([
                ('contract_id', 'in', contracts.ids),
            ])
            overdue_count = len(all_schedules.filtered(lambda s: s.state == 'overdue'))

            if overdue_count == 0:
                classification = 'preferred'
            elif overdue_count <= 2:
                classification = 'normal'
            else:
                classification = 'delinquent'

            rec.loan_classification = classification

    @api.model
    def action_update_loan_classification(self):
        """Cron: actualiza la clasificación de todos los clientes con préstamos."""
        partners = self.search([('loan_ids', '!=', False)])
        for partner in partners:
            partner._compute_loan_classification()
        return True

    # =========================================================
    # Action
    # =========================================================

    def action_view_loans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Préstamos de %s') % self.name,
            'res_model': 'rst.loan.contract',
            'view_mode': 'kanban,tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
