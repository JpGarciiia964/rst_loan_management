# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RstLoanVoucherSequence(models.Model):
    _name = 'rst.loan.voucher.sequence'
    _description = 'Secuencia de Comprobantes'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)
    prefix = fields.Char(string='Prefijo', default='')
    suffix = fields.Char(string='Sufijo', default='')
    padding = fields.Integer(string='Dígitos', default=8)
    next_number = fields.Integer(string='Próximo Número', default=1)
    use_year = fields.Boolean(string='Incluir Año', default=False)
    is_fiscal = fields.Boolean(string='Comprobante Fiscal', default=False)
    is_default = fields.Boolean(string='Por Defecto', default=False)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Descripción')

    preview = fields.Char(
        string='Vista Previa',
        compute='_compute_preview',
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'El código de secuencia debe ser único.'),
    ]

    @api.depends('prefix', 'suffix', 'padding', 'next_number', 'use_year')
    def _compute_preview(self):
        from datetime import date
        for rec in self:
            year = str(date.today().year) + '-' if rec.use_year else ''
            number = str(rec.next_number).zfill(rec.padding)
            rec.preview = f"{rec.prefix or ''}{year}{number}{rec.suffix or ''}"

    def get_next_number(self):
        """Consume y devuelve el próximo número de comprobante."""
        self.ensure_one()
        from datetime import date
        self.env.cr.execute(
            "SELECT next_number FROM rst_loan_voucher_sequence WHERE id = %s FOR UPDATE",
            (self.id,)
        )
        row = self.env.cr.fetchone()
        current = row[0]
        year = str(date.today().year) + '-' if self.use_year else ''
        number = str(current).zfill(self.padding)
        voucher = f"{self.prefix or ''}{year}{number}{self.suffix or ''}"
        self.next_number = current + 1
        return voucher
