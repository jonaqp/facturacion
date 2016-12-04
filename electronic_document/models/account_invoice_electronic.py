# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import UserError
from core_electronic_authorization.authorization_sri import authorization_document, generate_access_key, update_xml_report


class AccountInvoiceElectronic(models.Model):
    _name = 'account.invoice.electronic'
    _rec_name = 'number'
    _order = 'number desc'

    @api.model
    def _get_company_id(self):
        company_id = self.env['res.users'].browse(self._uid).company_id.id
        return company_id

    @api.model
    def _get_number(self):
        context = self._context
        sequence = self.env['ir.sequence']
        printer_point = self.env['res.users'].browse(self._uid).printer_point
        return sequence.next_by_code(context.get('type') + printer_point)

    number = fields.Char(string="Numero", size=17, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)], 'unauthorized': [('readonly', True)], 'draft': [('required', False)]})
    emission_date = fields.Date(string="Fecha Emisión", required=True, default=datetime.now,  states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    type = fields.Selection([('factura', 'Factura'),
                             ('credito', 'Nota de Crédito'),
                             ('debito', 'Nota de Débito')], string='Tipo')
    access_key = fields.Char(string="Clave de Acceso", size=49, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    electronic_authorization = fields.Char(string="Autorización Electrónica", size=49, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    authorization_date = fields.Datetime(string="Fecha y Hora de Autorización", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    line_id = fields.One2many("account.invoice.electronic.line", "invoice_id", required=True, string="Lineas",states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    partner_id = fields.Many2one("res.partner", string="Cliente", required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    vat = fields.Char(string="RUC/CEDULA", related='partner_id.vat', states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    email = fields.Char(string="Email", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]}, related='partner_id.email')
    street = fields.Char(string="Dirección", related='partner_id.street', states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    sri_response = fields.Char(string="Respuesta SRI", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    xml_report = fields.Binary(string="Archivo XML", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    xml_name = fields.Char(string="Archivo XML", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    state = fields.Selection([('authorized', 'Autorizado'),
                              ('unauthorized', 'No autorizado'),
                              ('loaded', 'Por Autorizar'),
                              ('draft', 'Borrador')], string="Estado", default='draft')
    subtotal = fields.Float(string="Subtotal", required=True, compute='_get_total_invoice')
    subtotal_0 = fields.Float(string="Subtotal 0%", required=True, compute='_get_total_invoice')
    subtotal_taxed = fields.Float(string="Subtotal %", compute='_get_total_invoice')
    total_discount = fields.Float(string="Total Descuento")
    taxed = fields.Float(string="Iva %", required=True, compute='_get_total_invoice')
    total = fields.Float(string="Total", required=True, compute='_get_total_invoice')
    tax_comp_bool = fields.Boolean(string="Compensacion Iva?", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    tax_comp = fields.Float(string="Compensacion Solidaria iva 2%", compute='_get_tax_comp')
    note = fields.Text(string="Informacion Adicional", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    motive = fields.Char(string="Motivo", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    number_fact = fields.Char(string="Factura", size=17, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    number_fact_date = fields.Date(string="Fecha Factura", size=17, states={'authorized': [('readonly', True)]})
    payment_ids = fields.One2many('payment.method.invoice', 'invoice_id', string="Formas de Pago", required=True,
                                  states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    company_id = fields.Many2one('res.company', string="Compania", required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]},
                                 default=_get_company_id)
    sent = fields.Boolean(string="Enviado", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    remission_guide = fields.Char(string="Guia de Remision", size=17, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    modification_value = fields.Float(string="Valor de Modificacion", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    lock = fields.Boolean(string='Bloqueado')

    @api.one
    def change_access_key(self):
        self.access_key = generate_access_key(self, self)
        self.electronic_authorization = self.access_key

    @api.multi
    def unlink(self):
        if self.state in ('authorized', 'loaded'):
            raise UserError("No es posible eliminar un documento autorizado o por autorizar. Contacte con el administrador de sistema")
        return super(AccountInvoiceElectronic, self).unlink()

    @api.model
    def create(self, values):
        if not values.get('type'):
            values['type'] = self._context.get('type')
        return super(AccountInvoiceElectronic, self).create(values)

    @api.one
    @api.depends('tax_comp_bool', 'subtotal')
    def _get_tax_comp(self):
        if self.tax_comp_bool:
            self.tax_comp = round(self.subtotal_taxed * .02, 2)
        else:
            self.tax_comp = 0.0

    @api.one
    @api.depends('line_id.total', 'line_id.price_unit', 'line_id.quantity', 'line_id.discount', 'tax_comp',
                 'modification_value')
    def _get_total_invoice(self):
        tax = 0.0
        if self.type == 'debito':
            self.subtotal_taxed += self.modification_value
            tax += self.modification_value * 0.14
        else:
            for line in self.line_id:
                if line.tax.code == '0':
                    self.subtotal_0 += round(line.total, 2)
                else:
                    self.subtotal_taxed += round(line.total, 2)
                    tax += round(line.total * line.tax.percentage / 100, 2)
        self.taxed = tax
        self.subtotal = self.subtotal_taxed + self.subtotal_0
        self.total = self.taxed + self.subtotal - self.tax_comp

    @api.multi
    def change_state_to(self):
        for invoice in self:
            invoice.state = 'loaded'
            invoice.number = self._get_number()
            access_key = generate_access_key(self, invoice)
            invoice.access_key = access_key
            invoice.electronic_authorization = access_key


    @api.one
    def authorization_document_button(self):
        if not self.lock:
            self.lock = True
            response = authorization_document(self)
            self.write(response)
            if response['state'] != 'authorized':
                self.lock = False
            self.xml_report = update_xml_report(self)

    @api.multi
    def authorization_documents_cron(self, *args):
        invoices = self.search([('state', '=', 'loaded')], order='type asc')
        for invoice in invoices:
            if not invoice.lock:
                invoice.lock = True
                response = authorization_document(invoice)
                invoice.write(response)
                if response['state'] != 'authorized':
                    invoice.lock = False
                else:
                    self.xml_report = update_xml_report(self)

    @api.multi
    def send_mail_document(self):
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
        context = {
                    'default_model': 'account.invoice.electronic',
                    'default_res_id': self.id,
                    'default_use_template': bool(template_id),
                    'default_template_id': template_id,
                    'default_composition_mode': 'comment',
                    'mark_invoice_as_sent': True,
                    'recipients': self.email
                  }
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
    total = fields.Float(string="Total", required=True, compute='_get_total_line')
    tax = fields.Many2one('account.tax.electronic', string='Impuesto', required=True)
    # tax = fields.Selection([('0', '0%'),('2', '12%'), ('3', '14%')], string="Codigo Impuesto", required=True)
    invoice_id = fields.Many2one('account.invoice.electronic', string="Facturas")

    @api.one
    def _get_total_line(self):
        self.total = self.quantity * self.price_unit - self.discount
