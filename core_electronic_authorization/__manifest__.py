# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Core Electronic Authorization',
    'version' : '1.0',
    'author': 'BPC INGENIEROS',
    'depends': [],
    'data': [
             'security/security.xml',
             'security/ir.model.access.csv',
             'views/parents_view_electronic.xml',
             'views/digital_signature_view.xml',
             'views/webservice_sri_view.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
