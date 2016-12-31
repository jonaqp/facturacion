# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Read Electronic Authorization',
    'version' : '1.0',
    'author': 'BPC INGENIEROS',
    'data': [
             'security/security.xml',
             'security/ir.model.access.csv',
             'views/file_document_view.xml',
             'views/setting_file_view.xml',
             'data/settings_data.xml'],
    'depends': ['base', 'electronic_document'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
