# -*- coding: utf-8 -*-
{
    'name': 'RST Loan Management',
    'version': '16.0.7.1.0',
    'category': 'Finance',
    'summary': 'Gestión completa de préstamos - RST',
    'description': """
RST Loan Management
===================
Módulo completo para la gestión de préstamos financieros.

Funcionalidades:
- Catálogo de tipos de préstamos con configuración predefinida
- Gestión de contratos con flujo de aprobación
- Cronograma de cuotas con amortización francesa o interés simple
- Registro de pagos parciales y totales
- Clasificación automática de clientes (Preferencial / Normal / Moroso)
- Gestión de documentos obligatorios por tipo de préstamo
- Vista Kanban con semáforo de estado
- Dashboard con KPIs financieros
- Reportes en PDF
- Integración con contabilidad, correo y chatter
    """,
    'author': 'RST',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'contacts',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/voucher_sequence_access.xml',
        # Data
        'data/sequences.xml',
        'data/voucher_sequences.xml',
        'data/cron.xml',
        # Views
        'views/loan_type_views.xml',
        'views/loan_contract_views.xml',
        'views/loan_schedule_views.xml',
        'views/loan_payment_views.xml',
        'views/loan_document_views.xml',
        'views/loan_voucher_sequence_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/dashboard_views.xml',
        'views/menu_views.xml',
        # Wizards
        'wizards/loan_payment_wizard_views.xml',
        # Reports
        'reports/loan_report.xml',
        'reports/loan_schedule_report.xml',
        'reports/loan_report_template.xml',
        'reports/payment_receipt_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rst_loan_management/static/src/css/loan_kanban.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
}
