# -*- coding: utf-8 -*-
from odoo import models, api


class RstLoanContractReport(models.AbstractModel):
    """Inyecta los colores de marca en el contexto de los reportes."""
    _name = 'report.rst_loan_management.report_rst_loan_contract_template'
    _description = 'Reporte Contrato de Prestamo'

    def _get_brand_colors(self):
        """Lee los colores configurados o retorna los defaults."""
        get = self.env['ir.config_parameter'].sudo().get_param
        return {
            'primary': get('rst_loan_management.primary_color', '#1a3a5c'),
            'secondary': get('rst_loan_management.secondary_color', '#2980b9'),
            'accent': get('rst_loan_management.accent_color', '#27ae60'),
            'danger': get('rst_loan_management.danger_color', '#c0392b'),
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['rst.loan.contract'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'rst.loan.contract',
            'docs': docs,
            'brand': self._get_brand_colors(),
        }


class RstLoanScheduleReport(models.AbstractModel):
    _name = 'report.rst_loan_management.report_loan_schedule_template'
    _description = 'Reporte Cronograma de Pagos'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['rst.loan.contract'].browse(docids)
        get = self.env['ir.config_parameter'].sudo().get_param
        return {
            'doc_ids': docids,
            'doc_model': 'rst.loan.contract',
            'docs': docs,
            'brand': {
                'primary': get('rst_loan_management.primary_color', '#1a3a5c'),
                'secondary': get('rst_loan_management.secondary_color', '#2980b9'),
                'accent': get('rst_loan_management.accent_color', '#27ae60'),
                'danger': get('rst_loan_management.danger_color', '#c0392b'),
            },
        }


class RstPaymentReceiptReport(models.AbstractModel):
    _name = 'report.rst_loan_management.report_rst_payment_receipt_template'
    _description = 'Boleta de Pago'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['rst.loan.payment'].browse(docids)
        get = self.env['ir.config_parameter'].sudo().get_param
        return {
            'doc_ids': docids,
            'doc_model': 'rst.loan.payment',
            'docs': docs,
            'brand': {
                'primary': get('rst_loan_management.primary_color', '#1a3a5c'),
                'secondary': get('rst_loan_management.secondary_color', '#2980b9'),
                'accent': get('rst_loan_management.accent_color', '#27ae60'),
                'danger': get('rst_loan_management.danger_color', '#c0392b'),
            },
        }
