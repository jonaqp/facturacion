from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    printer_point = fields.Char(string='Punto de Impresion', help='xxx-xxx', required=True)