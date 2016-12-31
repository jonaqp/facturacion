# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Electronic Authorization',
    'author': 'BPC INGENIEROS',
    'version' : '1.0',
    'data': [
             'security/security.xml',
             'security/ir.model.access.csv',
             'reports/report.xml',
             'reports/account_invoice_electronic_report.xml',
             'views/account_invoice_electronic_view.xml',
             'views/account_withhold_electronic_view.xml',
             'views/remission_guide_electronic.xml',
             'views/payment_method_view.xml',
             'views/res_company_view.xml',
             'views/send_mail_document_view.xml',
             'views/res_users_view.xml',
             'views/account_tax_electronic_view.xml',
             'data/data_payment_method.xml',
             'data/cron_jobs.xml',
             'data/email_template_data.xml'],
    'depends': ['base', 'mail', 'core_electronic_authorization'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
