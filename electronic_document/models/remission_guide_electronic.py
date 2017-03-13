# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
import pytz
from odoo.exceptions import UserError
from core_electronic_authorization.authorization_sri import authorization_document, generate_access_key, update_xml_report


class RemissionGuideElectronic(models.Model):
    _name = 'remission.guide.electronic'
    _inherit = ['mail.thread']
    _rec_name = 'number'
    _order = 'number desc'

    @api.model
    def _get_company_id(self):
        company_id = self.env['res.users'].browse(self._uid).company_id.id
        return company_id

    @api.model
    def _get_number(self):
        sequence = self.env['ir.sequence']
        printer_point = self.env['res.users'].browse(self._uid).printer_point
        return sequence.next_by_code('remission' + printer_point)

    @api.multi
    def unlink(self):
        if self.state in ('authorized', 'loaded'):
            raise UserError("No es posible eliminar un documento autorizado o por autorizar. Contacte con el administrador de sistema")
        return super(RemissionGuideElectronic, self).unlink()

    dat = pytz.utc.localize(datetime.now()).astimezone(pytz.timezone('America/Guayaquil'))
    number = fields.Char(string="Numero", size=17, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)], 'unauthorized': [('readonly', True)], 'draft': [('required', False)]})
    emission_date = fields.Date(string="Fecha Inicio Transporte", required=True, default=dat.date,
                                      states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    emission_date_stop = fields.Date(string="Fecha Fin Transporte", required=True, default=dat.date,
                                     states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    access_key = fields.Char(string="Clave de Acceso", size=49, states={'authorized': [('readonly', True)],  'loaded': [('readonly', True)]})
    electronic_authorization = fields.Char(string="Autorización Electrónica", size=49, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    authorization_date = fields.Datetime(string="Fecha y Hora de Autorización",states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    line_id = fields.One2many("remission.guide.electronic.line", "remission_id", required=True, string="Lineas",
                              states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    partner_id = fields.Many2one("res.partner", string="Cliente", required=True, states={'authorized': [('readonly', True)],  'loaded': [('readonly', True)]})
    vat = fields.Char(string="RUC/CEDULA", related='partner_id.vat', states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]}, readonly=True)
    email = fields.Char(string="Email", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]}, related='partner_id.email', readonly=True)
    street = fields.Char(string="Dirección Llegada", related='partner_id.street', readonly=True)
    sri_response = fields.Char(string="Respuesta SRI", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    xml_report = fields.Binary(string="Archivo XML", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    xml_name = fields.Char(string="Archivo XML", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    state = fields.Selection([('authorized', 'Autorizado'),
                              ('unauthorized', 'No autorizado'),
                              ('loaded', 'Por Autorizar'),
                              ('draft', 'Borrador')], string="Estado", default='draft')
    note = fields.Text(string="Informacion Adicional", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    motivo = fields.Text(string="Motivo", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    invoice = fields.Char(string="Factura", size=17, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    invoice_emission_date = fields.Date(string="Fecha Emision Factura", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    ruc_carrier = fields.Char(string="RUC Transportista", required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    social_name = fields.Char(string="Razon Social Transportista", required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    start_street = fields.Char(string="Direccion Partida", required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    company_id = fields.Many2one('res.company', string="Compania", required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]}, default=_get_company_id)
    sent = fields.Boolean(string="Enviado", states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    lock = fields.Boolean(string='Bloqueado')
    transfer_motive = fields.Char(string='Motivo', required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
    license_plate = fields.Char(string='Placa', required=True, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})

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
    def change_state_to(self):
        for remission in self:
            number = self._get_number()
            access_key = generate_access_key(self, remission, number)
            remission.write({'state': 'loaded', 'number': number, 'access_key': access_key,
                             'electronic_authorization': access_key})

    @api.one
    def change_access_key(self):
        access_key = generate_access_key(self, self, self.number)
        self.write({'access_key': access_key, 'electronic_authorization': access_key})

    @api.multi
    def authorization_documents_cron(self, *args):
        remissions = self.search([('state', '=', 'loaded')], order='number asc')
        for remission in remissions:
            if not remission.lock:
                remission.lock = True
                response = authorization_document(remission)
                remission.write(response)
                if response['state'] != 'authorized':
                    remission.lock = False
                else:
                    self.xml_report = update_xml_report(self)

    @api.multi
    def send_mail_documents_cron(self, *args):
        remissions = self.search([('state', '=', 'authorized'), ('sent', '=', False)], order='number asc')
        ir_model_data = self.env['ir.model.data']
        for remission in remissions:
            try:
                template_id = ir_model_data.get_object_reference('electronic_document', 'email_template_remission_guide_electronic')[1]
            except ValueError:
                template_id = False
            template_id = self.env['mail.template'].browse(template_id)
            template_id.send_mail(remission.id, force_send=True)
            remission.sent = True

    @api.multi
    def print_document(self):
        for remission in self:
            att_id = self.env['ir.attachment'].search([('res_model', '=', remission._name), ('res_id', '=', remission.id)])
            if att_id:
                att_id.unlink()
            return self.env['report'].get_action([remission.id], 'electronic_document.remission_guide_electronic_report')

    @api.multi
    def send_mail_document(self):
        context = {}
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('electronic_document', 'email_template_remission_guide_electronic')[1]
        except ValueError:
            template_id = False
        compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        context.update({
            'default_model': 'remission.guide.electronic',
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


class RemissionGuideElectronicLine(models.Model):
    _name = 'remission.guide.electronic.line'

    code = fields.Char(string="Codigo", required=True)
    name = fields.Char(string="Producto", required=True)
    quantity = fields.Float(string="Cantidad", required=True)
    remission_id = fields.Many2one('remission.guide.electronic', string="Guias")