# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import pytz
from odoo.exceptions import UserError
from core_electronic_authorization.authorization_sri import authorization_document, generate_access_key, update_xml_report


class AccountWithholdElectronic(models.Model):
    _name = 'account.withhold.electronic'
    _inherit = ['mail.thread']
    _rec_name = 'number'
    _order = 'number'

    @api.model
    def _get_company_id(self):
        company_id = self.env['res.users'].browse(self._uid).company_id.id
        return company_id

    @api.model
    def _get_number(self):
        sequence = self.env['ir.sequence']
        printer_point = self.env['res.users'].browse(self._uid).printer_point
        return sequence.next_by_code('withhold' + printer_point)

    dat = pytz.utc.localize(datetime.now()).astimezone(pytz.timezone('America/Guayaquil'))
    number = fields.Char(string="Numero", size=17,  states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)], 'unauthorized': [('readonly', True)], 'draft': [('required', False)]})
    emission_date = fields.Date(string="Fecha Emisión", required=True, default=dat.date, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    access_key = fields.Char(string="Clave de Acceso", size=49, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    electronic_authorization = fields.Char(string="Autorización Electrónica", size=49, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    authorization_date = fields.Datetime(string="Fecha y Hora de Autorización", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    line_id = fields.One2many("account.withhold.electronic.line", "withhold_id", required=True, string="Lineas", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    partner_id = fields.Many2one("res.partner", string="Cliente", required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    vat = fields.Char(string="RUC/CEDULA", readonly=True, related='partner_id.vat', states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    email = fields.Char(string="Email", readonly=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]}, related='partner_id.email')
    street = fields.Char(string="Dirección", related='partner_id.street', states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    sri_response = fields.Char(string="Respuesta SRI", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    xml_report = fields.Binary(string="Archivo XML", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    xml_name = fields.Char(string="Archivo XML", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    state = fields.Selection([('authorized', 'Autorizado'),
                              ('unauthorized', 'No autorizado'),
                              ('loaded', 'Por Autorizar'),
                              ('draft', 'Borrador')], string="Estado", default='draft')
    total = fields.Float(string="Total a retener", required=True, compute='_get_total_withhold')
    note = fields.Text(string="Informacion Adicional", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    fiscalyear = fields.Char(string="Año Fiscal", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]}, help='MM/YYYY', required=True)
    company_id = fields.Many2one('res.company', string="Compania", required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]},
                                 default=_get_company_id)
    sent = fields.Boolean(string="Enviado", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    lock = fields.Boolean(string='Bloqueado')

    @api.one
    @api.depends('line_id.tax', 'line_id.base_amount', 'line_id.tax_amount')
    def _get_total_withhold(self):
        total = 0
        for line in self.line_id:
            total += line.tax_amount
        self.total = total

    @api.one
    def change_access_key(self):
        access_key = generate_access_key(self, self, self.number)
        self.write({'access_key': access_key, 'electronic_authorization': access_key})

    @api.multi
    def unlink(self):
        if self.state in ('authorized', 'loaded'):
            raise UserError("No es posible eliminar un documento autorizado o por autorizar. Contacte con el administrador de sistema")
        return super(AccountWithholdElectronic, self).unlink()

    @api.multi
    def change_state_to(self):
        for withhold in self:
            number = self._get_number()
            access_key = generate_access_key(self, withhold, number)
            withhold.write({'state': 'loaded', 'access_key': access_key, 'electronic_authorization': access_key,
                            'number': number})

    @api.one
    def authorization_document_button(self):
        if not self.lock:
            self.lock = True
            response = authorization_document(self)
            self.write(response)
            if response['state'] != 'authorized':
                self.lock = False
            else:
                self.xml_report = update_xml_report(self)

    @api.multi
    def authorization_documents_cron(self, *args):
        withholds = self.search([('state', '=', 'loaded')], order='number asc')
        for withhold in withholds:
            if not withhold.lock:
                withhold.lock = True
                response = authorization_document(withhold)
                withhold.write(response)
                if response['state'] != 'authorized':
                    withhold.lock = False
                else:
                    self.xml_report = update_xml_report(self)

    @api.multi
    def send_mail_documents_cron(self, *args):
        withholds = self.search([('state', '=', 'authorized'), ('sent', '=', False)], order='number asc')
        ir_model_data = self.env['ir.model.data']
        for withhold in withholds:
            try:
                template_id = ir_model_data.get_object_reference('electronic_document', 'email_template_account_withhold_electronic')[1]
            except ValueError:
                template_id = False
            template_id = self.env['mail.template'].browse(template_id)
            template_id.send_mail(withhold.id, force_send=True)
            withhold.sent = True

    @api.multi
    def print_document(self):
        for withhold in self:
            att_id = self.env['ir.attachment'].search([('res_model', '=', withhold._name), ('res_id', '=', withhold.id)])
            if att_id:
                att_id.unlink()
            return self.env['report'].get_action([withhold.id], 'electronic_document.account_withhold_electronic_report')

    @api.multi
    def send_mail_document(self):
        context = {}
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('electronic_document', 'email_template_withhold_electronic')[1]
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
    tax_amount = fields.Float(string="Total", required=True, compute='_get_tax_amount')
    num_fact = fields.Char(sting="Numero Factura", required=True, size=15)
    tax_name = fields.Selection([('1', 'RENTA'),
                                ('2', 'IVA')], string="Impuesto", required=True)
    name = fields.Char(string="Comprobante", required=True)
    emission_date_fact = fields.Date(string="Fecha Emision Factura")
    withhold_id = fields.Many2one('account.withhold.electronic', string="Retencion")

    @api.one
    @api.depends('tax', 'base_amount')
    def _get_tax_amount(self):
        self.tax_amount = self.base_amount * self.tax/100.0