# -*- coding: utf-8 -*-

from odoo import models, fields


class PaymentMethod(models.Model):
    _name = 'payment.method'
    _rec_name = 'name'

    code = fields.Char(string="Codigo", size=2, required=True)
    name = fields.Char(string="Forma de pago", size=64, required=True)


class PaymentMethodInvoice(models.Model):
    _name = 'payment.method.invoice'
    _rec_name = 'payment_id'

    payment_id = fields.Many2one('payment.method', string="Codigo", size=2, required=True)
    plazo = fields.Integer(string="Plazo")
    amount = fields.Float(string="Monto", required=True)
    unit = fields.Char(string="Unidad")
    invoice_id = fields.Many2one('account.invoice.electronic', string="Facturas")