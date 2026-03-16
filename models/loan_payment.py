# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class RstLoanPayment(models.Model):
    _name = 'rst.loan.payment'
    _description = 'Pago de Préstamo RST'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_payment desc, id desc'

    name = fields.Char('N° Pago', required=True, copy=False, readonly=True,
                        default='Nuevo', tracking=True)
    voucher_number = fields.Char('N° Comprobante', copy=False, readonly=True,
                                  tracking=True)
    contract_id  = fields.Many2one('rst.loan.contract', string='Contrato',
                                    required=True, ondelete='restrict', tracking=True)
    partner_id   = fields.Many2one(related='contract_id.partner_id',
                                    string='Cliente', store=True)
    schedule_id  = fields.Many2one('rst.loan.schedule', string='Cuota a Pagar',
                                    domain="[('contract_id','=',contract_id),"
                                           "('state','in',['pending','partial','overdue'])]")
    date_payment = fields.Date('Fecha de Pago', required=True,
                                default=fields.Date.today, tracking=True)
    amount       = fields.Monetary('Monto Pagado', required=True, tracking=True,
                                    currency_field='currency_id')
    payment_method = fields.Selection([
        ('cash',     'Efectivo'),
        ('transfer', 'Transferencia'),
        ('check',    'Cheque'),
        ('other',    'Otro'),
    ], string='Método de Pago', default='cash', required=True, tracking=True)
    reference    = fields.Char('Referencia / N° Cheque')
    notes        = fields.Text('Notas')
    currency_id  = fields.Many2one(related='contract_id.currency_id', store=True)
    loan_officer_id = fields.Many2one(related='contract_id.loan_officer_id',
                                       string='Oficial', store=True)
    company_id   = fields.Many2one(related='contract_id.company_id', store=True)

    balance_before = fields.Monetary('Saldo Antes', currency_field='currency_id',
                                      readonly=True, copy=False)
    balance_after  = fields.Monetary('Saldo Despues', currency_field='currency_id',
                                      readonly=True, copy=False)

    # Desglose del pago
    amount_capital = fields.Monetary('Aplicado a Capital', currency_field='currency_id',
                                      readonly=True, copy=False)
    amount_interest = fields.Monetary('Aplicado a Interés', currency_field='currency_id',
                                       readonly=True, copy=False)
    amount_late_fee = fields.Monetary('Mora Cobrada', currency_field='currency_id',
                                       readonly=True, copy=False)

    # Penalidad por cancelacion
    amount_penalty = fields.Monetary('Penalidad Cancelacion', currency_field='currency_id',
                                      readonly=True, copy=False)
    is_full_payoff = fields.Boolean('Pago Total (Cancelacion)', readonly=True, copy=False)

    state = fields.Selection([
        ('draft',     'Borrador'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Cancelado'),
    ], default='draft', tracking=True, copy=False)

    # =========================================================
    # ORM
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'Nuevo') == 'Nuevo':
                v['name'] = self.env['ir.sequence'].next_by_code('rst.loan.payment') or 'Nuevo'
        return super().create(vals_list)

    # =========================================================
    # Onchanges
    # =========================================================

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            first = self.contract_id.schedule_ids.filtered(
                lambda s: s.state in ('pending', 'partial', 'overdue')
            ).sorted('sequence')
            self.schedule_id = first[:1].id if first else False
            self.amount = self.contract_id.installment_amount

    # =========================================================
    # Constrains
    # =========================================================

    @api.constrains('amount')
    def _check_amount(self):
        for r in self:
            if r.amount <= 0:
                raise ValidationError(_('El monto del pago debe ser mayor a cero.'))

    # =========================================================
    # Actions
    # =========================================================

    def action_confirm(self):
        """
        Confirma el pago:
        1. Si es pago total: requiere cancelacion aprobada, incluye penalidad.
        2. Aplica el monto a las cuotas pendientes.
        3. Genera numero de comprobante.
        4. Retorna accion para imprimir boleta.
        """
        today = date.today()
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Solo se pueden confirmar pagos en Borrador.'))
            if rec.contract_id.state not in ('active', 'overdue'):
                raise UserError(_('El contrato debe estar Activo o Vencido.'))

            contract = rec.contract_id
            balance = contract.balance_remaining
            penalty = contract.cancellation_penalty_amount or 0
            tolerance = 0.01

            # ── Detectar pago total anticipado ──────────────────────
            # Solo es "pago total" si cubre todo el saldo Y quedan
            # mas de 1 cuota pendiente (pagar la ultima cuota normal no cuenta)
            pending_schedules = contract.schedule_ids.filtered(
                lambda s: s.state in ('pending', 'partial', 'overdue')
            )
            covers_all_balance = (rec.amount >= balance - tolerance)
            is_full = covers_all_balance and len(pending_schedules) > 1

            if is_full:
                # Pago total REQUIERE cancelacion aprobada
                if contract.cancel_state != 'approved':
                    raise UserError(_(
                        'No se puede realizar el pago total del prestamo sin una '
                        'solicitud de cancelacion aprobada por el supervisor.\n\n'
                        'Pasos:\n'
                        '1. Solicitar cancelacion desde el contrato.\n'
                        '2. Esperar aprobacion del supervisor.\n'
                        '3. Luego realizar el pago total (saldo + penalidad).'
                    ))
                # Verificar que el monto incluye la penalidad
                total_required = balance + penalty
                if rec.amount < total_required - tolerance:
                    raise UserError(_(
                        'El pago total debe incluir la penalidad por cancelacion.\n\n'
                        'Saldo pendiente: %s %s\n'
                        'Penalidad: %s %s\n'
                        'Total requerido: %s %s\n'
                        'Monto ingresado: %s %s'
                    ) % (
                        contract.currency_id.symbol, balance,
                        contract.currency_id.symbol, penalty,
                        contract.currency_id.symbol, total_required,
                        contract.currency_id.symbol, rec.amount,
                    ))
                rec.is_full_payoff = True
                rec.amount_penalty = penalty

            rec.balance_before = balance

            remaining = rec.amount
            # Si es pago total con penalidad, descontar la penalidad primero
            if rec.is_full_payoff and penalty > 0:
                remaining = remaining - penalty

            total_capital = 0.0
            total_interest = 0.0
            total_late_fee = 0.0

            for schedule in contract.schedule_ids.filtered(
                lambda s: s.state in ('pending', 'partial', 'overdue')
            ).sorted('sequence'):
                if remaining <= 0:
                    break

                late_fee = schedule.late_fee_amount if schedule.late_fee_applied else 0.0
                pending = schedule.amount_pending
                applied = min(remaining, pending)

                if applied >= pending:
                    total_capital += schedule.amount_principal
                    total_interest += schedule.amount_interest
                    total_late_fee += late_fee
                else:
                    ratio = applied / pending if pending else 0
                    total_capital += schedule.amount_principal * ratio
                    total_interest += schedule.amount_interest * ratio
                    total_late_fee += late_fee * ratio

                remaining = schedule.apply_payment(remaining)

            # Generar numero de comprobante
            voucher_seq = rec.env['rst.loan.voucher.sequence'].search([
                ('is_default', '=', True),
            ], limit=1)
            if voucher_seq:
                rec.voucher_number = voucher_seq.get_next_number()
            else:
                rec.voucher_number = rec.name

            rec.amount_capital = round(total_capital, 2)
            rec.amount_interest = round(total_interest, 2)
            rec.amount_late_fee = round(total_late_fee, 2)
            rec.balance_after = contract.balance_remaining
            rec.write({'state': 'confirmed'})

            # Si saldo en 0, marcar como pagado y ejecutar cancelacion
            if contract.balance_remaining < tolerance:
                if rec.is_full_payoff:
                    # Pago total por cancelacion: marcar como cancelado
                    contract.write({'state': 'cancelled'})
                    contract.message_post(
                        body=_(
                            'Contrato cancelado. Pago total recibido (%s %s) '
                            'incluyendo penalidad de %s %s.'
                        ) % (
                            contract.currency_id.symbol, rec.amount,
                            contract.currency_id.symbol, penalty,
                        )
                    )
                else:
                    contract.action_mark_paid()

            contract.message_post(
                body=_(
                    'Pago <b>%s</b> confirmado.%s<br/>'
                    'Monto: %s %s | Metodo: %s<br/>'
                    'Saldo anterior: %s | Saldo actual: %s'
                ) % (
                    rec.voucher_number or rec.name,
                    _(' <b>(PAGO TOTAL + PENALIDAD)</b>') if rec.is_full_payoff else '',
                    rec.currency_id.symbol, rec.amount,
                    dict(rec._fields['payment_method'].selection).get(rec.payment_method, ''),
                    rec.balance_before, rec.balance_after,
                )
            )

        # Retornar acción para imprimir boleta
        if len(self) == 1:
            return self.action_print_receipt()
        return True

    def action_print_receipt(self):
        """Imprime la boleta de pago."""
        return self.env.ref(
            'rst_loan_management.action_report_rst_payment_receipt'
        ).report_action(self)

    def action_cancel(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_('No se puede cancelar un pago ya confirmado.'))
            rec.write({'state': 'cancelled'})
