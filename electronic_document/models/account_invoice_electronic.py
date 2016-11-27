# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import datetime
from core_electronic_authorization.authorization_sri import authorization_document


class AccountInvoiceElectronic(models.Model):
    _name = 'account.invoice.electronic'
    _rec_name = 'number'
    _order = 'number desc'

    number = fields.Char(string="Numero", size=17, required=True)
    emission_date = fields.Date(string="Fecha Emisión", required=True, default=datetime.now)
    type = fields.Selection([('factura', 'Factura'),
                             ('credito', 'Nota de Crédito'),
                             ('debito', 'Nota de Débito')], stirng='Tipo')
    access_key = fields.Char(string="Clave de Acceso", size=49)
    electronic_authorization = fields.Char(string="Autorización Electrónica", size=49)
    authorization_date = fields.Datetime(string="Fecha y Hora de Autorización")
    line_id = fields.One2many("account.invoice.electronic.line", "invoice_id", required=True, string="Lineas")
    partner_id = fields.Many2one("res.partner", string="Cliente", required=True)
    vat = fields.Char(string="RUC/CEDULA", related='partner_id.vat')
    email = fields.Char(string="Email")
    street = fields.Char(string="Dirección", related='partner_id.street')
    sri_response = fields.Char(string="Respuesta SRI")
    xml_report = fields.Binary(string="Archivo XML")
    xml_name = fields.Char(string="Archivo XML")
    state = fields.Selection([('authorized', 'Autorizado'),
                              ('unauthorized', 'No autorizado'),
                              ('loaded', 'Por Autorizar')], string="Estado", default='loaded')
    subtotal = fields.Float(string="Subtotal", required=True)
    subtotal_0 = fields.Float(string="Subtotal 0%", required=True)
    subtotal_taxed = fields.Float(string="Subtotal %", required=True)
    total_discount = fields.Float(string="Total Descuento")
    taxed = fields.Float(string="Iva %", required=True)
    total = fields.Float(string="Total", required=True)
    tax_comp_bool = fields.Boolean(string="Compensacion Iva")
    tax_comp = fields.Float(string="Compensacion Solidaria iva 2%")
    note = fields.Text(string="Informacion Adicional")
    motive = fields.Char(string="Motivo")
    number_fact = fields.Char(string="Factura", size=17)
    number_fact_date = fields.Char(string="Fecha Factura", size=17)
    payment_ids = fields.One2many('payment.method.invoice', 'invoice_id', string="Formas de Pago", required=True)
    company_id = fields.Many2one('res.company', string="Compania", required=True)
    sent = fields.Boolean(string="Enviado")
    remission_guide = fields.Char(string="Guia de Remision", size=17)

    @api.multi
    def authorization_document_button(self):
        response = authorization_document(self)
        self.write(response)

    @api.multi
    def authorization_documents_cron(self, *args):
        invoices = self.search([('state', '=', 'loaded')], order='type asc')
        for invoice in invoices:
            response = authorization_document(invoice)
            invoice.write(response)

    @api.multi
    def send_mail_document(self):
        context = {}
        ir_model_data = self.env['ir.model.data']
        if self.type =='factura':
            template='email_template_account_invoice_electronic'
        elif self.type =='credito':
            template='email_template_account_invoice_nc_electronic'
        else:
            template = 'email_template_account_invoice_nd_electronic'
        try:
            template_id = ir_model_data.get_object_reference('electronic_document', template)[1]
        except ValueError:
            template_id = False
        compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        context.update({
            'default_model': 'account.invoice.electronic',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_invoice_as_sent': True,
            'recipients': self.email
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': context,
        }


class AccountInvoiceElectronicLine(models.Model):
    _name = 'account.invoice.electronic.line'

    code = fields.Char(string="Codigo", required=True)
    name = fields.Char(string="Producto", required=True)
    quantity = fields.Float(string="Cantidad", required=True)
    price_unit = fields.Float(string="Precio Unitario", required=True)
    discount = fields.Float(string="Descuento")
    total = fields.Float(string="Total", required=True)
    tax = fields.Integer(string="Codigo Impuesto", required=True)
    invoice_id = fields.Many2one('account.invoice.electronic', string="Facturas")

