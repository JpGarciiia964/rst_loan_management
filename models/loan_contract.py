# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import date
import math


class RstLoanContract(models.Model):
    """Contrato de préstamo principal."""
    _name = 'rst.loan.contract'
    _description = 'Contrato de Préstamo RST'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    _rec_name = 'name'

    # ── Identificación ───────────────────────────────────────────────────
    name = fields.Char(
        'N° Contrato', required=True, copy=False, readonly=True,
        default='Nuevo', tracking=True
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_review', 'En Revisión'),
        ('approved', 'Aprobado'),
        ('active', 'Activo'),
        ('overdue', 'Vencido'),
        ('paid', 'Pagado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True, copy=False,
        group_expand='_group_expand_states'
    )
    color = fields.Integer('Color', compute='_compute_color')
    priority = fields.Selection([
        ('0', 'Normal'), ('1', 'Importante'), ('2', 'Muy Importante'), ('3', 'Urgente')
    ], default='0')
    kanban_state = fields.Selection([
        ('normal', 'En Proceso'),
        ('done', 'Listo para siguiente etapa'),
        ('blocked', 'Bloqueado'),
    ], string='Estado Kanban', default='normal', tracking=True)

    # ── Partes del contrato ──────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Cliente', required=True,
        tracking=True, ondelete='restrict',
        domain="[('is_company', 'in', [True, False])]"
    )
    partner_classification = fields.Selection(
        related='partner_id.loan_classification', string='Clasificación Cliente',
        store=True
    )
    loan_officer_id = fields.Many2one(
        'res.users', string='Oficial de Crédito',
        default=lambda self: self.env.user, tracking=True
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        default=lambda self: self.env.company, required=True
    )
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id
    )

    # ── Tipo y condiciones del préstamo ──────────────────────────────────
    loan_type_id = fields.Many2one(
        'rst.loan.type', string='Tipo de Préstamo', tracking=True,
        ondelete='restrict'
    )
    amount = fields.Monetary(
        'Monto Solicitado', required=True, currency_field='currency_id',
        tracking=True
    )
    interest_rate = fields.Float(
        'Tasa de Interés Anual (%)', required=True, tracking=True
    )
    term_months = fields.Integer(
        'Plazo (meses)', required=True, tracking=True
    )
    payment_frequency = fields.Selection([
        ('monthly', 'Mensual'),
        ('biweekly', 'Quincenal'),
        ('weekly', 'Semanal'),
    ], string='Frecuencia de Pago', default='monthly', required=True, tracking=True)
    amortization_method = fields.Selection([
        ('french', 'Francés (Cuota Fija)'),
        ('simple', 'Interés Simple'),
    ], string='Método de Amortización', default='french', tracking=True)

    # ── Mora y días de gracia ────────────────────────────────────────────
    grace_days = fields.Integer(
        'Días de Gracia', default=0, tracking=True,
        help='Número de días después del vencimiento antes de aplicar mora.'
    )
    late_fee_type = fields.Selection([
        ('fixed', 'Monto Fijo'),
        ('percentage', 'Porcentaje sobre cuota'),
    ], string='Tipo de Mora', default='percentage', tracking=True)
    late_fee_value = fields.Float(
        'Valor de Mora', default=0.0, tracking=True,
        help='Si es porcentaje: ej. 5 = 5% de la cuota. Si es fijo: monto exacto.'
    )


    # ── Fechas ───────────────────────────────────────────────────────────
    date_start = fields.Date(
        'Fecha de Inicio', tracking=True,
        default=fields.Date.today
    )
    date_end = fields.Date(
        'Fecha de Vencimiento', compute='_compute_date_end',
        store=True, tracking=True
    )
    date_approved = fields.Date('Fecha de Aprobación', readonly=True, copy=False)
    date_disbursed = fields.Date('Fecha de Desembolso', readonly=True, copy=False)

    # ── Totales calculados ───────────────────────────────────────────────
    total_interest = fields.Monetary(
        'Total Intereses', compute='_compute_totals',
        store=True, currency_field='currency_id'
    )
    total_to_pay = fields.Monetary(
        'Total a Pagar', compute='_compute_totals',
        store=True, currency_field='currency_id'
    )
    amount_paid = fields.Monetary(
        'Monto Pagado', compute='_compute_amounts',
        store=True, currency_field='currency_id'
    )
    balance_remaining = fields.Monetary(
        'Saldo Pendiente', compute='_compute_amounts',
        store=True, currency_field='currency_id'
    )
    installment_amount = fields.Monetary(
        'Monto de Cuota', compute='_compute_totals',
        store=True, currency_field='currency_id'
    )
    progress_percent = fields.Float(
        'Progreso (%)', compute='_compute_amounts', store=True
    )
    overdue_amount = fields.Monetary(
        'Monto Vencido', compute='_compute_amounts',
        store=True, currency_field='currency_id'
    )

    total_late_fees = fields.Monetary(
        'Mora Acumulada', compute='_compute_amounts',
        store=True, currency_field='currency_id'
    )
    days_to_next_due = fields.Integer(
        'Días al Próximo Vencimiento', compute='_compute_amounts', store=True
    )
    paid_installments = fields.Integer(
        'Cuotas Pagadas', compute='_compute_counts', store=True
    )

    # ── Relaciones ───────────────────────────────────────────────────────
    schedule_ids = fields.One2many(
        'rst.loan.schedule', 'contract_id', string='Cronograma de Pagos'
    )
    payment_ids = fields.One2many(
        'rst.loan.payment', 'contract_id', string='Pagos Realizados'
    )
    document_ids = fields.One2many(
        'rst.loan.document', 'contract_id', string='Documentos'
    )

    # ── Contadores para smart buttons ────────────────────────────────────
    schedule_count = fields.Integer(compute='_compute_counts', string='Cuotas', store=True)
    payment_count = fields.Integer(compute='_compute_counts', string='Pagos', store=True)
    document_count = fields.Integer(compute='_compute_counts', string='Documentos', store=True)
    overdue_installments = fields.Integer(
        compute='_compute_counts', string='Cuotas Vencidas', store=True
    )
    missing_documents = fields.Integer(
        compute='_compute_missing_docs', string='Docs. Faltantes', store=True
    )

    # ── Notas ─────────────────────────────────────────────────────────────
    notes = fields.Text('Notas Internas')
    rejection_reason = fields.Text('Motivo de Cancelacion/Rechazo', copy=False)

    # ── Flujo de cancelacion ──────────────────────────────────────────────
    cancel_state = fields.Selection([
        ('none', 'Sin Solicitud'),
        ('requested', 'Solicitud Enviada'),
        ('approved', 'Cancelacion Aprobada'),
        ('rejected', 'Cancelacion Rechazada'),
    ], string='Estado Cancelacion', default='none', tracking=True, copy=False)

    # ── Penalidad por cancelacion anticipada ─────────────────────────────
    cancellation_penalty_type = fields.Selection([
        ('fixed',      'Monto Fijo'),
        ('percentage', 'Porcentaje sobre saldo pendiente'),
    ], string='Tipo de Penalidad', default='percentage',
       help='Tipo de penalidad para cancelacion anticipada de contrato activo.')
    cancellation_penalty_value = fields.Float(
        'Valor de Penalidad', default=0.0,
        help='Porcentaje (ej: 5 = 5% del saldo) o monto fijo a cobrar al cancelar anticipadamente.'
    )
    cancellation_penalty_amount = fields.Monetary(
        'Monto Penalidad', compute='_compute_cancellation_penalty',
        currency_field='currency_id',
        help='Monto calculado de penalidad por cancelacion anticipada.'
    )

    # ── Flag de edición bloqueada ─────────────────────────────────────────
    is_locked = fields.Boolean(
        compute='_compute_is_locked',
        help='El contrato está bloqueado para edición después del desembolso.'
    )

    # =========================================================
    # ORM Overrides
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('rst.loan.contract') or 'Nuevo'
        records = super().create(vals_list)
        # Auto-poblar documentos requeridos si el tipo de prestamo tiene y no se crearon via onchange
        for rec in records:
            if rec.loan_type_id and rec.loan_type_id.required_document_ids:
                rec._populate_required_documents()
        return records

    def write(self, vals):
        """Previene regresion de estado en contratos bloqueados (activos/vencidos/pagados)."""
        locked_states = ('active', 'overdue', 'paid')
        forbidden_back = ('draft', 'in_review', 'approved')
        new_state = vals.get('state')
        if new_state and new_state in forbidden_back:
            for rec in self:
                if rec.state in locked_states:
                    raise UserError(_(
                        'El contrato "%s" fue desembolsado (estado: %s) y no puede '
                        'regresar al estado "%s". Un prestamo activo o vencido no puede '
                        'revertirse.'
                    ) % (rec.name, rec.state, new_state))
        return super().write(vals)

    # =========================================================
    # Constrains & Validations
    # =========================================================

    @api.constrains('amount', 'loan_type_id')
    def _check_amount_range(self):
        for rec in self:
            if rec.loan_type_id:
                if rec.amount < rec.loan_type_id.min_amount:
                    raise ValidationError(_(
                        'El monto %(amount)s es menor al mínimo permitido %(min)s.',
                        amount=rec.amount, min=rec.loan_type_id.min_amount,
                    ))
                if rec.amount > rec.loan_type_id.max_amount:
                    raise ValidationError(_(
                        'El monto %(amount)s supera el máximo permitido %(max)s.',
                        amount=rec.amount, max=rec.loan_type_id.max_amount,
                    ))

    @api.constrains('term_months')
    def _check_term(self):
        for rec in self:
            if rec.term_months < 1:
                raise ValidationError(_('El plazo debe ser al menos 1 mes.'))

    @api.constrains('interest_rate')
    def _check_interest_rate(self):
        for rec in self:
            if rec.interest_rate <= 0:
                raise ValidationError(_('La tasa de interés debe ser mayor a 0.'))

    # =========================================================
    # Onchanges
    # =========================================================

    @api.onchange('loan_type_id')
    def _onchange_loan_type_id(self):
        if self.loan_type_id:
            lt = self.loan_type_id
            self.interest_rate = lt.interest_rate
            self.payment_frequency = lt.payment_frequency
            self.amortization_method = lt.amortization_method
            self.grace_days = lt.grace_days
            self.late_fee_type = lt.late_fee_type
            self.late_fee_value = lt.late_fee_value
            mid_term = (lt.min_term + lt.max_term) // 2
            self.term_months = mid_term
            # Auto-poblar documentos requeridos
            if lt.required_document_ids:
                existing_type_ids = set(self.document_ids.mapped('document_type_id').ids)
                cmds = []
                for doc_type in lt.required_document_ids:
                    if doc_type.id not in existing_type_ids:
                        cmds.append((0, 0, {
                            'document_type_id': doc_type.id,
                            'state': 'pending',
                        }))
                if cmds:
                    self.update({'document_ids': cmds})

    def _populate_required_documents(self):
        """Crea lineas de documentos requeridos que falten en el contrato."""
        self.ensure_one()
        if not self.loan_type_id or not self.loan_type_id.required_document_ids:
            return
        existing_type_ids = set(self.document_ids.mapped('document_type_id').ids)
        DocModel = self.env['rst.loan.document']
        for doc_type in self.loan_type_id.required_document_ids:
            if doc_type.id not in existing_type_ids:
                DocModel.create({
                    'contract_id': self.id,
                    'document_type_id': doc_type.id,
                    'state': 'pending',
                })


    # =========================================================
    # Computed Fields
    # =========================================================

    @api.depends('state')
    def _compute_is_locked(self):
        for rec in self:
            rec.is_locked = rec.state in ('active', 'overdue', 'paid')

    @api.depends('balance_remaining', 'cancellation_penalty_type', 'cancellation_penalty_value')
    def _compute_cancellation_penalty(self):
        for rec in self:
            if rec.cancellation_penalty_type == 'percentage':
                rec.cancellation_penalty_amount = round(
                    rec.balance_remaining * rec.cancellation_penalty_value / 100, 2
                )
            else:
                rec.cancellation_penalty_amount = rec.cancellation_penalty_value

    @api.depends('state')
    def _compute_color(self):
        color_map = {
            'draft': 0, 'in_review': 3, 'approved': 4,
            'active': 10, 'overdue': 1, 'paid': 6, 'cancelled': 9,
        }
        for rec in self:
            rec.color = color_map.get(rec.state, 0)

    @api.depends('date_start', 'term_months')
    def _compute_date_end(self):
        for rec in self:
            if rec.date_start and rec.term_months:
                rec.date_end = rec.date_start + relativedelta(months=rec.term_months)
            else:
                rec.date_end = False

    @api.depends('amount', 'interest_rate', 'term_months', 'payment_frequency', 'amortization_method')
    def _compute_totals(self):
        for rec in self:
            if not rec.amount or not rec.interest_rate or not rec.term_months:
                rec.total_interest = 0
                rec.total_to_pay = 0
                rec.installment_amount = 0
                continue
            periods = rec._get_periods()
            periodic_rate = rec._get_periodic_rate()
            if rec.amortization_method == 'french':
                if periodic_rate > 0:
                    installment = rec.amount * (
                        periodic_rate * (1 + periodic_rate) ** periods
                    ) / ((1 + periodic_rate) ** periods - 1)
                else:
                    installment = rec.amount / periods
                total_pay = installment * periods
            else:
                annual_rate = rec.interest_rate / 100
                total_interest_simple = rec.amount * annual_rate * (rec.term_months / 12)
                total_pay = rec.amount + total_interest_simple
                installment = total_pay / periods
            rec.installment_amount = round(installment, 2)
            rec.total_to_pay = round(total_pay, 2)
            rec.total_interest = round(total_pay - rec.amount, 2)

    @api.depends('payment_ids', 'payment_ids.amount', 'payment_ids.state',
                 'total_to_pay', 'schedule_ids.state', 'schedule_ids.amount_due',
                 'schedule_ids.late_fee_amount', 'schedule_ids.date_due')
    def _compute_amounts(self):
        from datetime import date as _date
        for rec in self:
            paid = sum(p.amount for p in rec.payment_ids if p.state == 'confirmed')
            rec.amount_paid = paid
            rec.balance_remaining = max(rec.total_to_pay - paid, 0)
            rec.progress_percent = (paid / rec.total_to_pay * 100) if rec.total_to_pay else 0
            rec.overdue_amount = sum(
                s.amount_due for s in rec.schedule_ids if s.state == 'overdue'
            )
            rec.total_late_fees = sum(
                s.late_fee_amount for s in rec.schedule_ids if s.late_fee_amount
            )
            # Días al próximo vencimiento (cuota pending o partial más próxima)
            pending = rec.schedule_ids.filtered(
                lambda s: s.state in ('pending', 'partial') and s.date_due
            ).sorted('date_due')
            if pending:
                delta = (pending[0].date_due - _date.today()).days
                rec.days_to_next_due = delta
            else:
                rec.days_to_next_due = 0

    @api.depends('schedule_ids', 'schedule_ids.state', 'payment_ids', 'document_ids')
    def _compute_counts(self):
        for rec in self:
            rec.schedule_count = len(rec.schedule_ids)
            rec.payment_count = len(rec.payment_ids)
            rec.document_count = len(rec.document_ids)
            rec.overdue_installments = len(
                rec.schedule_ids.filtered(lambda s: s.state == 'overdue')
            )
            rec.paid_installments = len(
                rec.schedule_ids.filtered(lambda s: s.state == 'paid')
            )


    @api.depends('document_ids', 'document_ids.document_type_id',
                 'document_ids.file_data', 'document_ids.state',
                 'loan_type_id', 'loan_type_id.required_document_ids',
                 'loan_type_id.required_document_ids.is_mandatory')
    def _compute_missing_docs(self):
        for rec in self:
            if not rec.loan_type_id:
                rec.missing_documents = 0
                continue
            required = rec.loan_type_id.required_document_ids.filtered('is_mandatory')
            # Un documento esta completo si tiene archivo cargado
            uploaded_types = rec.document_ids.filtered(
                lambda d: d.file_data and d.state != 'rejected'
            ).mapped('document_type_id')
            rec.missing_documents = len(required.filtered(lambda d: d not in uploaded_types))

    # =========================================================
    # Helper Methods
    # =========================================================

    def _get_periods(self):
        self.ensure_one()
        freq_map = {'monthly': 1, 'biweekly': 2, 'weekly': 4}
        return self.term_months * freq_map.get(self.payment_frequency, 1)

    def _get_periodic_rate(self):
        self.ensure_one()
        annual_rate = self.interest_rate / 100
        freq_map = {'monthly': 12, 'biweekly': 24, 'weekly': 52}
        return annual_rate / freq_map.get(self.payment_frequency, 12)

    def _get_period_delta(self):
        self.ensure_one()
        if self.payment_frequency == 'monthly':
            return relativedelta(months=1)
        elif self.payment_frequency == 'biweekly':
            return relativedelta(weeks=2)
        else:
            return relativedelta(weeks=1)


    # =========================================================
    # Schedule Generation
    # =========================================================

    def _generate_schedule(self):
        self.ensure_one()
        self.schedule_ids.unlink()
        periods = self._get_periods()
        periodic_rate = self._get_periodic_rate()
        delta = self._get_period_delta()
        balance = self.amount
        current_date = self.date_start or date.today()
        vals_list = []

        if self.amortization_method == 'french':
            if periodic_rate > 0:
                installment = self.amount * (
                    periodic_rate * (1 + periodic_rate) ** periods
                ) / ((1 + periodic_rate) ** periods - 1)
            else:
                installment = self.amount / periods

            for i in range(1, periods + 1):
                current_date = current_date + delta
                interest = balance * periodic_rate
                principal = installment - interest
                if i == periods:
                    principal = balance
                    installment_final = principal + interest
                else:
                    installment_final = installment
                balance = max(balance - principal, 0)
                vals_list.append({
                    'contract_id': self.id,
                    'sequence': i,
                    'date_due': current_date,
                    'amount_principal': round(principal, 2),
                    'amount_interest': round(interest, 2),
                    'amount_due': round(installment_final, 2),
                    'balance_after': round(balance, 2),
                    'state': 'pending',
                })
        else:
            annual_rate = self.interest_rate / 100
            total_interest = self.amount * annual_rate * (self.term_months / 12)
            installment_principal = self.amount / periods
            installment_interest = total_interest / periods
            installment = installment_principal + installment_interest

            for i in range(1, periods + 1):
                current_date = current_date + delta
                balance = max(balance - installment_principal, 0)
                vals_list.append({
                    'contract_id': self.id,
                    'sequence': i,
                    'date_due': current_date,
                    'amount_principal': round(installment_principal, 2),
                    'amount_interest': round(installment_interest, 2),
                    'amount_due': round(installment, 2),
                    'balance_after': round(balance, 2),
                    'state': 'pending',
                })

        if vals_list:
            self.env['rst.loan.schedule'].create(vals_list)

    # =========================================================
    # Invoice Generation
    # =========================================================


    # =========================================================
    # Late Fee (Mora)
    # =========================================================

    def _apply_late_fee(self, schedule):
        """Aplica mora a una cuota vencida (sin crear facturas)."""
        self.ensure_one()
        if self.late_fee_value <= 0:
            return
        if schedule.late_fee_applied:
            return

        if self.late_fee_type == 'percentage':
            fee_amount = round(schedule.amount_due * self.late_fee_value / 100, 2)
        else:
            fee_amount = self.late_fee_value

        if fee_amount <= 0:
            return

        # Sumar la mora al monto de la cuota
        schedule.write({
            'late_fee_amount': fee_amount,
            'late_fee_applied': True,
            'amount_due': schedule.amount_due + fee_amount,
        })
        self.message_post(
            body=_('Mora aplicada a Cuota %d: %s %s') % (
                schedule.sequence, self.currency_id.symbol, fee_amount)
        )

    # =========================================================
    # Cron Methods
    # =========================================================


    @api.model
    def action_apply_late_fees_cron(self):
        """Cron: aplica mora a cuotas vencidas que superaron los días de gracia."""
        today = fields.Date.today()
        # Busca cuotas sin mora aplicada, sin importar si tienen factura
        schedules = self.env['rst.loan.schedule'].search([
            ('state', 'in', ['pending', 'partial', 'overdue']),
            ('late_fee_applied', '=', False),
            ('date_due', '<', today),
        ])
        for schedule in schedules:
            contract = schedule.contract_id
            # Solo aplica mora si el contrato tiene configuración de mora
            if contract.late_fee_value <= 0:
                continue
            grace = contract.grace_days or 0
            grace_limit = schedule.date_due + relativedelta(days=grace)
            if today > grace_limit:
                try:
                    contract._apply_late_fee(schedule)
                except Exception:
                    pass
        return True

    @api.model
    def action_update_overdue_contracts(self):
        """Cron: marca contratos activos como vencidos si su fecha_end ya pasó."""
        today = fields.Date.today()
        contracts = self.search([('state', '=', 'active'), ('date_end', '<', today)])
        contracts.filtered(lambda c: c.balance_remaining > 0).write({'state': 'overdue'})
        return True

    # =========================================================
    # State Transition Actions
    # =========================================================

    def action_send_to_review(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Solo se pueden enviar a revisión contratos en Borrador.'))
            if not rec.partner_id:
                raise UserError(_('Debe seleccionar un cliente.'))
            rec.write({'state': 'in_review'})
            rec.activity_schedule(
                'mail.activity_data_todo',
                note=_('Contrato pendiente de revisión y aprobación.'),
                user_id=rec.loan_officer_id.id or self.env.user.id,
            )

    def action_approve(self):
        for rec in self:
            if rec.state != 'in_review':
                raise UserError(_('Solo se pueden aprobar contratos En Revisión.'))
            if rec.missing_documents > 0:
                raise UserError(_(
                    'Faltan %d documento(s) obligatorio(s) antes de aprobar.'
                ) % rec.missing_documents)
            rec.write({'state': 'approved', 'date_approved': fields.Date.today()})
            rec.message_post(body=_('✅ Contrato aprobado por %s') % self.env.user.name)

    def action_disburse(self):
        """Activa el préstamo y genera el cronograma. Una vez activo, no regresa."""
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Solo se pueden desembolsar contratos Aprobados.'))
            rec._generate_schedule()
            rec.write({'state': 'active', 'date_disbursed': fields.Date.today()})
            rec.message_post(
                body=_('💰 Préstamo desembolsado. Cronograma de %d cuotas generado.') % rec.schedule_count
            )
            rec.partner_id._compute_loan_classification()

    def action_request_cancel(self):
        """Oficial solicita cancelacion - notifica al supervisor asignado."""
        for rec in self:
            if rec.state in ('paid', 'cancelled'):
                raise UserError(_('Este contrato no puede cancelarse.'))
            if rec.cancel_state == 'requested':
                raise UserError(_('Ya existe una solicitud de cancelacion pendiente.'))
            if rec.cancel_state == 'approved':
                raise UserError(_('La cancelacion ya fue aprobada. Proceda con el pago total.'))

            # Determinar supervisor destino
            officer = rec.loan_officer_id or self.env.user
            assigned_supervisor = officer.rst_loan_supervisor_id

            if assigned_supervisor:
                # Supervisor asignado al oficial
                target_user = assigned_supervisor
            else:
                # Sin supervisor asignado: notificar a todos los supervisores
                supervisor_group = self.env.ref(
                    'rst_loan_management.group_rst_loan_supervisor', raise_if_not_found=False)
                supervisors = supervisor_group.users if supervisor_group else self.env['res.users']
                # Excluir al usuario actual si es oficial
                supervisors = supervisors.filtered(lambda u: u.id != self.env.user.id)
                target_user = supervisors[:1] if supervisors else self.env.user

            rec.write({'cancel_state': 'requested'})

            # Crear actividad para CADA supervisor si no hay uno asignado
            if assigned_supervisor:
                notify_users = assigned_supervisor
            else:
                supervisor_group = self.env.ref(
                    'rst_loan_management.group_rst_loan_supervisor', raise_if_not_found=False)
                notify_users = supervisor_group.users if supervisor_group else self.env.user

            for sup in notify_users:
                rec.activity_schedule(
                    'mail.activity_data_todo',
                    summary=_('Solicitud de cancelacion: %s') % rec.name,
                    note=_(
                        'Solicitud de cancelacion del contrato %s.<br/>'
                        'Solicitado por: %s<br/>'
                        'Cliente: %s<br/>'
                        'Saldo pendiente: %s %s<br/>'
                        'Penalidad estimada: %s %s<br/>'
                        'Total a liquidar: %s %s'
                    ) % (
                        rec.name, self.env.user.name,
                        rec.partner_id.name,
                        rec.currency_id.symbol, rec.balance_remaining,
                        rec.currency_id.symbol, rec.cancellation_penalty_amount,
                        rec.currency_id.symbol,
                        rec.balance_remaining + rec.cancellation_penalty_amount,
                    ),
                    user_id=sup.id,
                )

            # Notificar por mensaje tambien
            rec.message_post(
                body=_(
                    '<strong>Solicitud de Cancelacion</strong><br/>'
                    'Solicitado por: %s<br/>'
                    'Saldo: %s %s | Penalidad: %s %s<br/>'
                    'Total a liquidar: %s %s<br/>'
                    'Pendiente de aprobacion del supervisor.'
                ) % (
                    self.env.user.name,
                    rec.currency_id.symbol, rec.balance_remaining,
                    rec.currency_id.symbol, rec.cancellation_penalty_amount,
                    rec.currency_id.symbol,
                    rec.balance_remaining + rec.cancellation_penalty_amount,
                ),
                partner_ids=notify_users.mapped('partner_id').ids,
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Solicitud Enviada'),
                'message': _('Se notifico al supervisor. Pendiente de aprobacion.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_approve_cancel(self):
        """Supervisor aprueba la cancelacion - el cliente debe pagar saldo + penalidad."""
        is_supervisor = self.env.user.has_group('rst_loan_management.group_rst_loan_supervisor')
        if not is_supervisor:
            raise UserError(_('Solo un Supervisor puede aprobar cancelaciones.'))
        for rec in self:
            if rec.cancel_state != 'requested':
                raise UserError(_('No hay solicitud de cancelacion pendiente para este contrato.'))
            rec.write({'cancel_state': 'approved'})
            # Marcar actividades como completadas
            rec.activity_ids.filtered(
                lambda a: 'cancelacion' in (a.summary or '').lower()
            ).action_done()
            rec.message_post(
                body=_(
                    '<strong>Cancelacion Aprobada por %s</strong><br/>'
                    'El cliente debe liquidar el saldo pendiente (%s %s) '
                    'mas la penalidad (%s %s) para completar la cancelacion.<br/>'
                    '<strong>Total a pagar: %s %s</strong>'
                ) % (
                    self.env.user.name,
                    rec.currency_id.symbol, rec.balance_remaining,
                    rec.currency_id.symbol, rec.cancellation_penalty_amount,
                    rec.currency_id.symbol,
                    rec.balance_remaining + rec.cancellation_penalty_amount,
                )
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cancelacion Aprobada'),
                'message': _('El cliente debe pagar saldo + penalidad para finalizar.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reject_cancel(self):
        """Supervisor rechaza la solicitud de cancelacion."""
        is_supervisor = self.env.user.has_group('rst_loan_management.group_rst_loan_supervisor')
        if not is_supervisor:
            raise UserError(_('Solo un Supervisor puede rechazar cancelaciones.'))
        for rec in self:
            if rec.cancel_state != 'requested':
                raise UserError(_('No hay solicitud pendiente.'))
            rec.write({'cancel_state': 'rejected'})
            rec.activity_ids.filtered(
                lambda a: 'cancelacion' in (a.summary or '').lower()
            ).action_done()
            rec.message_post(
                body=_('Solicitud de cancelacion RECHAZADA por %s.') % self.env.user.name
            )

    def action_cancel(self):
        """Ejecuta la cancelacion final. Requiere cancel_state=approved y saldo en 0."""
        is_supervisor = self.env.user.has_group('rst_loan_management.group_rst_loan_supervisor')
        if not is_supervisor:
            raise UserError(_(
                'Solo un Supervisor puede ejecutar la cancelacion final.'
            ))
        for rec in self:
            if rec.state == 'paid':
                raise UserError(_('No se puede cancelar un contrato ya pagado.'))
            if rec.cancel_state != 'approved':
                raise UserError(_(
                    'La cancelacion debe ser aprobada antes de ejecutarla. '
                    'Estado actual: %s'
                ) % dict(rec._fields['cancel_state'].selection).get(rec.cancel_state, ''))
            if rec.state in ('active', 'overdue') and rec.balance_remaining > 0.01:
                raise UserError(_(
                    'El cliente debe liquidar el saldo pendiente (%s %s) '
                    'y la penalidad (%s %s) antes de cancelar.'
                ) % (
                    rec.currency_id.symbol, rec.balance_remaining,
                    rec.currency_id.symbol, rec.cancellation_penalty_amount,
                ))
            rec.write({'state': 'cancelled', 'cancel_state': 'none'})
            rec.message_post(
                body=_('Contrato CANCELADO por Supervisor %s.') % self.env.user.name
            )


    def action_reset_draft(self):
        for rec in self:
            if rec.state in ('active', 'overdue', 'paid'):
                raise UserError(_(
                    'Un contrato desembolsado no puede volver a Borrador.'
                ))
            if rec.state not in ('in_review', 'cancelled'):
                raise UserError(_('Solo se puede resetear desde En Revisión o Cancelado.'))
            rec.write({'state': 'draft'})

    def action_mark_paid(self):
        for rec in self:
            if rec.balance_remaining > 0.01:
                raise UserError(_(
                    'El contrato aún tiene saldo pendiente de %s.'
                ) % rec.balance_remaining)
            rec.write({'state': 'paid'})
            rec.message_post(body=_('🎉 Préstamo completamente pagado.'))
            rec.partner_id._compute_loan_classification()

    # =========================================================
    # Smart Button Actions
    # =========================================================

    def action_view_schedule(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cronograma - %s') % self.name,
            'res_model': 'rst.loan.schedule',
            'view_mode': 'tree,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id},
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pagos - %s') % self.name,
            'res_model': 'rst.loan.payment',
            'view_mode': 'tree,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'default_contract_id': self.id, 'default_partner_id': self.partner_id.id},
        }


    def action_register_payment(self):
        self.ensure_one()
        if self.state not in ('active', 'overdue'):
            raise UserError(_('Solo se pueden registrar pagos en contratos Activos o Vencidos.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Registrar Pago'),
            'res_model': 'rst.loan.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_amount': self.installment_amount,
            },
        }

    def action_print_contract(self):
        self.ensure_one()
        return self.env.ref('rst_loan_management.action_rst_loan_contract_report').report_action(self)

    def action_print_schedule(self):
        self.ensure_one()
        return self.env.ref('rst_loan_management.action_rst_loan_schedule_report').report_action(self)

    # =========================================================
    # Kanban group expand
    # =========================================================

    @api.model
    def _group_expand_states(self, states, domain, order):
        return [key for key, val in self._fields['state'].selection]
