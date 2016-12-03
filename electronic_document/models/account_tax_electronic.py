from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountTaxElectronic(models.Model):
    _name = 'account.tax.electronic'
    _rec_name = 'percentage'

    code = fields.Char(string='Codigo', required=True, size=2)
    percentage = fields.Integer(string='Porcentaje', required=True)

    @api.model
    def create(self, values):
        taxes = self.search([('code', '=', values.get('code'))])
        if taxes:
            raise UserError('Ya existe un impuesto con el codigo %s' % values.get('code'))
        return super(AccountTaxElectronic, self).create(values)