# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class RstLoanDocumentType(models.Model):
    """Tipos de documentos requeridos por cada tipo de préstamo."""
    _name = 'rst.loan.document.type'
    _description = 'Tipo de Documento Requerido'
    _order = 'sequence, name'

    name = fields.Char('Nombre del Documento', required=True)
    sequence = fields.Integer('Secuencia', default=10)
    loan_type_id = fields.Many2one(
        'rst.loan.type', string='Tipo de Préstamo',
        ondelete='cascade', required=True
    )
    is_mandatory = fields.Boolean('Obligatorio', default=True)
    description = fields.Char('Descripción')

class RstLoanType(models.Model):
    """Catálogo de productos financieros / tipos de préstamos."""
    _name = 'rst.loan.type'
    _description = 'Tipo de Préstamo RST'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ── Información general ─────────────────────────────────────────────
    name = fields.Char('Nombre', required=True, tracking=True)
    code = fields.Char('Código', required=True, copy=False)
    active = fields.Boolean('Activo', default=True, tracking=True)
    notes = fields.Text('Descripción / Notas')
    color = fields.Integer('Color')

    # ── Condiciones financieras ──────────────────────────────────────────
    interest_rate = fields.Float(
        'Tasa de Interés Anual (%)', required=True, tracking=True,
        help='Tasa de interés anual en porcentaje (ej: 12 para 12%)'
    )
    min_term = fields.Integer('Plazo Mínimo (meses)', required=True, default=1)
    max_term = fields.Integer('Plazo Máximo (meses)', required=True, default=60)
    min_amount = fields.Monetary(
        'Monto Mínimo', required=True, currency_field='currency_id'
    )
    max_amount = fields.Monetary(
        'Monto Máximo', required=True, currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.company.currency_id
    )
    payment_frequency = fields.Selection([
        ('monthly', 'Mensual'),
        ('biweekly', 'Quincenal'),
        ('weekly', 'Semanal'),
    ], string='Frecuencia de Pago', default='monthly', required=True, tracking=True)
    amortization_method = fields.Selection([
        ('french', 'Francés (Cuota Fija)'),
        ('simple', 'Interés Simple'),
    ], string='Método de Amortización', default='french', required=True,
        tracking=True,
        help='Francés: cuota fija mensual.\nSimple: interés calculado sobre el capital original.'
    )

    # ── Mora y días de gracia ────────────────────────────────────────────
    grace_days = fields.Integer(
        'Días de Gracia', default=0,
        help='Días después del vencimiento antes de aplicar mora.'
    )
    late_fee_type = fields.Selection([
        ('fixed',      'Monto Fijo'),
        ('percentage', 'Porcentaje sobre cuota'),
    ], string='Tipo de Mora', default='percentage')
    late_fee_value = fields.Float(
        'Valor de Mora', default=0.0,
        help='Porcentaje (ej: 5 = 5%) o monto fijo según el tipo.'
    )

    # ── Documentos requeridos ────────────────────────────────────────────
    required_document_ids = fields.One2many(
        'rst.loan.document.type', 'loan_type_id',
        string='Documentos Requeridos'
    )

    # ── Estadísticas ─────────────────────────────────────────────────────
    contract_count = fields.Integer(
        compute='_compute_contract_count', string='Contratos'
    )

    DEFAULT_DOCUMENTS = [
        {'name': 'Cedula de Identidad', 'sequence': 1, 'is_mandatory': True,
         'description': 'Copia de la cedula de identidad y electoral del solicitante.'},
        {'name': 'Carta Laboral', 'sequence': 2, 'is_mandatory': True,
         'description': 'Carta de trabajo indicando cargo, salario y antiguedad.'},
        {'name': 'Estados de Cuenta', 'sequence': 3, 'is_mandatory': True,
         'description': 'Estados de cuenta bancarios de los ultimos 3 meses.'},
    ]

    # ── Constrains ───────────────────────────────────────────────────────
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El código del tipo de préstamo debe ser único.'),
        ('interest_rate_positive', 'CHECK(interest_rate > 0)', 'La tasa de interés debe ser mayor a 0.'),
        ('min_amount_positive', 'CHECK(min_amount > 0)', 'El monto mínimo debe ser mayor a 0.'),
        ('max_amount_gt_min', 'CHECK(max_amount >= min_amount)', 'El monto máximo debe ser mayor o igual al mínimo.'),
        ('max_term_gt_min', 'CHECK(max_term >= min_term)', 'El plazo máximo debe ser mayor o igual al mínimo.'),
    ]

    @api.constrains('min_term', 'max_term')
    def _check_terms(self):
        for rec in self:
            if rec.min_term < 1:
                raise ValidationError(_('El plazo mínimo debe ser al menos 1 mes.'))

    # ── Computes ─────────────────────────────────────────────────────────
    def _compute_contract_count(self):
        Contract = self.env['rst.loan.contract']
        for rec in self:
            rec.contract_count = Contract.search_count([('loan_type_id', '=', rec.id)])

    # ── ORM Overrides ─────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._create_default_documents()
        return records

    def _create_default_documents(self):
        """Crea los documentos requeridos por defecto si no existen."""
        self.ensure_one()
        existing_names = self.required_document_ids.mapped('name')
        DocType = self.env['rst.loan.document.type'].sudo()
        for doc_vals in self.DEFAULT_DOCUMENTS:
            if doc_vals['name'] not in existing_names:
                DocType.create({
                    'loan_type_id': self.id,
                    'name': doc_vals['name'],
                    'sequence': doc_vals['sequence'],
                    'is_mandatory': doc_vals['is_mandatory'],
                    'description': doc_vals['description'],
                })

    def action_add_default_documents(self):
        """Boton para agregar documentos por defecto a tipos existentes."""
        for rec in self:
            rec._create_default_documents()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Documentos Agregados'),
                'message': _('Se agregaron los documentos por defecto que faltaban.'),
                'type': 'success',
                'sticky': False,
            }
        }

    # ── Actions ──────────────────────────────────────────────────────────
    def action_view_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contratos - %s') % self.name,
            'res_model': 'rst.loan.contract',
            'view_mode': 'kanban,tree,form',
            'domain': [('loan_type_id', '=', self.id)],
            'context': {'default_loan_type_id': self.id},
        }
