from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    must_account = fields.Boolean(string="Obligado a llevar contabilidad?")
    contributed = fields.Char(string="Contribuyente especial")