# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RstLoanDocument(models.Model):
    """Documentos adjuntos a los contratos de préstamo."""
    _name = 'rst.loan.document'
    _description = 'Documento de Préstamo RST'
    _order = 'contract_id, document_type_id'

    # ── Relación ─────────────────────────────────────────────────────────
    contract_id = fields.Many2one(
        'rst.loan.contract', string='Contrato', required=True,
        ondelete='cascade', index=True
    )
    partner_id = fields.Many2one(
        related='contract_id.partner_id', store=True
    )

    # ── Tipo de documento ─────────────────────────────────────────────────
    document_type_id = fields.Many2one(
        'rst.loan.document.type', string='Tipo de Documento',
        required=True,
        domain="[('loan_type_id', '=', parent.loan_type_id)]"
    )
    is_mandatory = fields.Boolean(
        related='document_type_id.is_mandatory', store=True
    )
    document_type_name = fields.Char(
        related='document_type_id.name', store=True
    )

    # ── Archivo ───────────────────────────────────────────────────────────
    attachment_id = fields.Many2one(
        'ir.attachment', string='Archivo Adjunto', ondelete='cascade'
    )
    file_name = fields.Char('Nombre del Archivo')
    file_data = fields.Binary('Documento', attachment=True)
    
    # ── Metadatos ─────────────────────────────────────────────────────────
    date_uploaded = fields.Date(
        'Fecha de Carga', default=fields.Date.today, readonly=True
    )
    uploaded_by = fields.Many2one(
        'res.users', string='Cargado por',
        default=lambda self: self.env.user, readonly=True
    )
    expiry_date = fields.Date('Fecha de Vencimiento del Documento')
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('uploaded', 'Cargado'),
        ('verified', 'Verificado'),
        ('expired', 'Vencido'),
        ('rejected', 'Rechazado'),
    ], string='Estado', default='pending', tracking=True)
    notes = fields.Text('Observaciones')

    # ── Computed ──────────────────────────────────────────────────────────
    is_expired = fields.Boolean(compute='_compute_is_expired', store=True)

    # =========================================================
    # Constrains
    # =========================================================

    @api.constrains('contract_id', 'document_type_id')
    def _check_unique_doc_type(self):
        for rec in self:
            duplicates = self.search([
                ('contract_id', '=', rec.contract_id.id),
                ('document_type_id', '=', rec.document_type_id.id),
                ('id', '!=', rec.id),
            ])
            if duplicates:
                raise ValidationError(_(
                    'Ya existe un documento del tipo "%s" para este contrato.'
                ) % rec.document_type_id.name)

    # =========================================================
    # Computed
    # =========================================================

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_expired = bool(rec.expiry_date and rec.expiry_date < today)

    # =========================================================
    # Onchange
    # =========================================================

    @api.onchange('file_data')
    def _onchange_file_data(self):
        if self.file_data:
            self.state = 'uploaded'

    # =========================================================
    # Actions
    # =========================================================

    def action_verify(self):
        self.write({'state': 'verified'})

    def action_reject(self):
        self.write({'state': 'rejected'})


class RstLoanDocumentTypeCedula(models.Model):
    """Extension to enforce cedula (national ID) as always mandatory."""
    _inherit = 'rst.loan.document.type'

    is_cedula = fields.Boolean(
        'Es Cédula de Identidad', default=False,
        help='Marque este campo si este tipo de documento es la cédula. '
             'La cédula siempre será obligatoria y no puede desactivarse.'
    )

    @api.constrains('is_mandatory', 'is_cedula')
    def _check_cedula_mandatory(self):
        for rec in self:
            if rec.is_cedula and not rec.is_mandatory:
                raise ValidationError(
                    _('La Cédula de Identidad siempre debe ser obligatoria.')
                )

    def write(self, vals):
        # Prevent unmarking cedula as non-mandatory
        if 'is_mandatory' in vals and vals['is_mandatory'] is False:
            cedulas = self.filtered('is_cedula')
            if cedulas:
                raise ValidationError(
                    _('No se puede desmarcar como obligatoria la Cédula de Identidad.')
                )
        return super().write(vals)
