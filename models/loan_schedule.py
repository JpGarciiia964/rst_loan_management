# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class RstLoanSchedule(models.Model):
    _name = 'rst.loan.schedule'
    _description = 'Cuota de Préstamo RST'
    _order = 'contract_id, sequence'
    _rec_name = 'display_name'

    contract_id = fields.Many2one(
        'rst.loan.contract', string='Contrato', required=True,
        ondelete='cascade', index=True
    )
    partner_id = fields.Many2one(
        related='contract_id.partner_id', string='Cliente', store=True
    )
    sequence    = fields.Integer('N° Cuota', required=True)
    date_due    = fields.Date('Fecha de Vencimiento', required=True)
    date_paid   = fields.Date('Fecha de Pago')

    amount_principal = fields.Monetary('Capital',      currency_field='currency_id')
    amount_interest  = fields.Monetary('Interés',      currency_field='currency_id')
    amount_due       = fields.Monetary('Total Cuota',  currency_field='currency_id')
    amount_paid      = fields.Monetary('Monto Pagado', currency_field='currency_id', default=0)
    amount_pending   = fields.Monetary('Pendiente',    currency_field='currency_id',
                                       compute='_compute_pending', store=True)
    balance_after    = fields.Monetary('Saldo tras Cuota', currency_field='currency_id')
    currency_id      = fields.Many2one(related='contract_id.currency_id', store=True)

    # ── Mora ─────────────────────────────────────────────────────────────
    late_fee_applied = fields.Boolean('Mora Aplicada', default=False, copy=False)
    late_fee_amount  = fields.Monetary('Monto de Mora', currency_field='currency_id',
                                       default=0.0, copy=False)

    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('partial', 'Pago Parcial'),
        ('paid',    'Pagada'),
        ('overdue', 'Vencida'),
    ], string='Estado', default='pending', tracking=True)

    notes        = fields.Char('Notas')
    display_name = fields.Char(compute='_compute_display_name', store=True)
    color        = fields.Integer(compute='_compute_color')

    # =========================================================
    # Computed
    # =========================================================

    @api.depends('amount_due', 'amount_paid')
    def _compute_pending(self):
        for r in self:
            r.amount_pending = max(r.amount_due - r.amount_paid, 0)

    @api.depends('contract_id.name', 'sequence')
    def _compute_display_name(self):
        for r in self:
            r.display_name = _('Cuota %d - %s') % (r.sequence, r.contract_id.name)

    @api.depends('state')
    def _compute_color(self):
        m = {'pending': 4, 'partial': 3, 'paid': 10, 'overdue': 1}
        for r in self:
            r.color = m.get(r.state, 0)

    # =========================================================
    # Business Logic
    # =========================================================

    def apply_payment(self, amount):
        """Aplica un monto a esta cuota. Retorna el excedente."""
        self.ensure_one()
        pending = self.amount_pending
        if amount >= pending:
            self.write({'amount_paid': self.amount_due,
                        'date_paid': date.today(), 'state': 'paid'})
            return amount - pending
        else:
            self.write({'amount_paid': self.amount_paid + amount, 'state': 'partial'})
            return 0

    # ── Cron methods ─────────────────────────────────────────────────────

    @api.model
    def action_update_overdue(self):
        """Marca cuotas vencidas (respeta días de gracia del contrato)."""
        today = date.today()
        candidates = self.search([
            ('state', 'in', ['pending', 'partial']),
            ('date_due', '<', today),
        ])
        to_overdue = self.env['rst.loan.schedule']
        for s in candidates:
            grace = s.contract_id.grace_days or 0
            if (today - s.date_due).days > grace:
                to_overdue |= s
        if to_overdue:
            to_overdue.write({'state': 'overdue'})
        return True

    @api.model
    def action_send_payment_reminders(self):
        """Envía recordatorio 3 días antes del vencimiento."""
        today = date.today()
        target = today + relativedelta(days=3)
        for s in self.search([('date_due', '=', target),
                               ('state', 'in', ['pending', 'partial'])]):
            s.contract_id.message_post(
                body=_('⏰ Recordatorio: Cuota %d vence el %s por %s') % (
                    s.sequence, s.date_due, s.amount_pending),
                message_type='email',
                partner_ids=[(4, s.partner_id.id)],
            )
        return True
