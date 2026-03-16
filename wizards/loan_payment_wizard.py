# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class RstLoanPaymentWizard(models.TransientModel):
    """Wizard para registrar pagos rápidos desde el Kanban o el formulario."""
    _name = 'rst.loan.payment.wizard'
    _description = 'Wizard de Pago Rápido RST'

    contract_id = fields.Many2one(
        'rst.loan.contract', string='Contrato', required=True,
        readonly=True
    )
    partner_id = fields.Many2one(
        related='contract_id.partner_id', string='Cliente'
    )
    currency_id = fields.Many2one(
        related='contract_id.currency_id'
    )

    # ── Próxima cuota ──────────────────────────────────────────────────────
    next_installment_id = fields.Many2one(
        'rst.loan.schedule', string='Cuota a Pagar',
        domain="[('contract_id', '=', contract_id), ('state', 'in', ['pending', 'partial', 'overdue'])]"
    )
    installment_amount = fields.Monetary(
        related='next_installment_id.amount_pending',
        string='Monto de la Cuota', currency_field='currency_id'
    )
    installment_date_due = fields.Date(
        related='next_installment_id.date_due', string='Fecha de Vencimiento'
    )
    installment_state = fields.Selection(
        related='next_installment_id.state', string='Estado Cuota'
    )

    # ── Mora y penalidad ────────────────────────────────────────────────────
    has_late_fee = fields.Boolean(
        compute='_compute_mora_info', string='Tiene Mora'
    )
    late_fee_amount = fields.Monetary(
        compute='_compute_mora_info', string='Mora de la Cuota',
        currency_field='currency_id'
    )
    contract_total_late_fees = fields.Monetary(
        related='contract_id.total_late_fees',
        string='Mora Acumulada Total', currency_field='currency_id'
    )
    has_penalty = fields.Boolean(
        compute='_compute_mora_info', string='Tiene Penalidad'
    )
    cancellation_penalty = fields.Monetary(
        related='contract_id.cancellation_penalty_amount',
        string='Penalidad Cancelación', currency_field='currency_id'
    )

    # ── Datos del pago ───────────────────────────────────────────────────
    date_payment = fields.Date(
        'Fecha de Pago', required=True, default=fields.Date.today
    )
    amount = fields.Monetary(
        'Monto a Pagar', required=True, currency_field='currency_id'
    )
    payment_method = fields.Selection([
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia Bancaria'),
        ('card', 'Tarjeta'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    ], string='Método de Pago', default='cash', required=True)
    reference = fields.Char('Referencia / N° Comprobante')
    notes = fields.Text('Notas')

    # ── Info del contrato ─────────────────────────────────────────────────
    balance_remaining = fields.Monetary(
        related='contract_id.balance_remaining',
        string='Saldo Pendiente', currency_field='currency_id'
    )
    overdue_amount = fields.Monetary(
        related='contract_id.overdue_amount',
        string='Monto Vencido', currency_field='currency_id'
    )
    cancel_state = fields.Selection(
        related='contract_id.cancel_state', string='Estado Cancelacion'
    )
    full_payoff_amount = fields.Monetary(
        compute='_compute_full_payoff', string='Total Pago Cancelacion',
        currency_field='currency_id'
    )

    # =========================================================
    # Computed
    # =========================================================

    @api.depends('next_installment_id')
    def _compute_mora_info(self):
        for rec in self:
            schedule = rec.next_installment_id
            rec.has_late_fee = schedule.late_fee_applied if schedule else False
            rec.late_fee_amount = schedule.late_fee_amount if schedule else 0
            rec.has_penalty = (rec.contract_id.cancellation_penalty_amount or 0) > 0

    @api.depends('contract_id', 'contract_id.balance_remaining', 'contract_id.cancellation_penalty_amount')
    def _compute_full_payoff(self):
        for rec in self:
            rec.full_payoff_amount = (
                (rec.contract_id.balance_remaining or 0)
                + (rec.contract_id.cancellation_penalty_amount or 0)
            )

    # =========================================================
    # Onchange
    # =========================================================

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            next_pending = self.contract_id.schedule_ids.filtered(
                lambda s: s.state in ('overdue', 'pending', 'partial')
            ).sorted('sequence')
            if next_pending:
                self.next_installment_id = next_pending[0]
                self.amount = next_pending[0].amount_pending

    @api.onchange('next_installment_id')
    def _onchange_next_installment_id(self):
        if self.next_installment_id:
            self.amount = self.next_installment_id.amount_pending

    # =========================================================
    # Constrains
    # =========================================================

    @api.constrains('amount', 'contract_id')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('El monto del pago debe ser mayor a 0.'))
            # Permitir saldo + penalidad si cancelacion aprobada
            max_amount = rec.contract_id.balance_remaining
            if rec.contract_id.cancel_state == 'approved':
                max_amount += rec.contract_id.cancellation_penalty_amount or 0
            if rec.amount > max_amount + 0.01:
                raise ValidationError(_(
                    'El monto (%(a)s) supera el maximo permitido (%(b)s).',
                    a=rec.amount, b=max_amount
                ))

    # =========================================================
    # Action
    # =========================================================

    def action_register_payment(self):
        """Crea el pago, lo confirma y abre la boleta para imprimir."""
        self.ensure_one()
        payment = self.env['rst.loan.payment'].create({
            'contract_id': self.contract_id.id,
            'partner_id': self.partner_id.id,
            'schedule_id': self.next_installment_id.id if self.next_installment_id else False,
            'date_payment': self.date_payment,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'reference': self.reference,
            'notes': self.notes,
            'balance_before': self.contract_id.balance_remaining,
        })
        # action_confirm retorna la acción de imprimir boleta
        return payment.action_confirm()
