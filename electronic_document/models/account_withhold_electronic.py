# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from odoo.addons_local.core_electronic_authorization.authorization_sri import authorization_document


class AccountWithholdElectronic(models.Model):
    _name = 'account.withhold.electronic'
    _rec_name = 'number'

    number = fields.Char(string="Numero", size=17, required=True)
    emission_date = fields.Date(string="Fecha Emisión", required=True, default=datetime.now)
    access_key = fields.Char(string="Clave de Acceso", size=49)
    electronic_authorization = fields.Char(string="Autorización Electrónica", size=49)
    authorization_date = fields.Datetime(string="Fecha y Hora de Autorización")
    line_id = fields.One2many("account.withhold.electronic.line", "withhold_id", required=True, string="Lineas")
    partner_id = fields.Many2one("res.partner", string="Cliente", required=True)
    vat = fields.Char(string="RUC/CEDULA", related='partner_id.vat')
    email = fields.Char(string="Email")
    street = fields.Char(string="Dirección", related='partner_id.street')
    sri_response = fields.Char(string="Respuesta SRI")
    xml_report = fields.Binary(string="Archivo XML")
    xml_name = fields.Char(string="Archivo XML")
    state = fields.Selection([('authorized', 'Autorizado'),
                              ('unathorized', 'No autorizado'),
                              ('loaded', 'Por Autorizar')], string="Estado", default='loaded')
    total = fields.Float(string="Total", required=True)
    note = fields.Text(string="Informacion Adicional")
    fiscalyear = fields.Char(string="Año Fiscal")
    company_id = fields.Many2one('res.company', string="Compania", required=True)
    sent = fields.Boolean(string="Enviado")

    @api.multi
    def authorization_document_button(self):
        response = authorization_document(self)
        self.write(response)

    @api.multi
    def authorization_documents_cron(self, *args):
        withholds = self.search([('state', '=', 'loaded')], order='number asc')
        for withhold in withholds:
            response = authorization_document(withhold)
            withhold.write(response)

    @api.multi
    def send_mail_document(self):
        context = {}
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('electronic_authorization', 'email_template_withhold_electronic')[1]
        except ValueError:
            template_id = False
        compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        context.update({
            'default_model': 'account.withhold.electronic',
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


class AccountWithholdElectronicLine(models.Model):
    _name = 'account.withhold.electronic.line'

    base_amount = fields.Float(string="Base Imponible", required=True)
    tax = fields.Integer(string="Porcentaje", required=True)
    code = fields.Char(string="Codigo", required=True, size=3)
    tax_amount = fields.Float(string="Total a Retener", required=True)
    num_fact = fields.Char(sting="Numero Factura", required=True, size=15)
    tax_name = fields.Selection([('1', 'RENTA'),
                                ('2', 'IVA')], string="Impuesto", required=True)
    name = fields.Char(stirng="Comprobante", required=True)
    emission_date_fact = fields.Char(string="Fecha Emision Factura")
    withhold_id = fields.Many2one('account.withhold.electronic', string="Retencion")
