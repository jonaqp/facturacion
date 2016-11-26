# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from odoo.addons_local.core_electronic_authorization.authorization_sri import authorization_document


class RemissionGuideElectronic(models.Model):
    _name = 'remission.guide.electronic'
    _rec_name = 'number'

    _order = 'number desc'

    number = fields.Char(string="Numero", size=17, required=True)
    emission_date_start = fields.Date(string="Fecha Inicio Transporte", required=True, default=datetime.now)
    emission_date_stop = fields.Date(string="Fecha Fin Transporte", required=True, default=datetime.now)
    access_key = fields.Char(string="Clave de Acceso", size=49)
    electronic_authorization = fields.Char(string="Autorización Electrónica", size=49)
    authorization_date = fields.Datetime(string="Fecha y Hora de Autorización")
    line_id = fields.One2many("remission.guide.electronic.line", "remission_id", required=True, string="Lineas")
    partner_id = fields.Many2one("res.partner", string="Cliente", required=True)
    vat = fields.Char(string="RUC/CEDULA", related='partner_id.vat')
    email = fields.Char(string="Email")
    street = fields.Char(string="Dirección LLegada", related='partner_id.street')
    sri_response = fields.Char(string="Respuesta SRI")
    xml_report = fields.Binary(string="Archivo XML")
    xml_name = fields.Char(string="Archivo XML")
    state = fields.Selection([('authorized', 'Autorizado'),
                              ('unathorized', 'No autorizado'),
                              ('loaded', 'Por Autorizar')], string="Estado", default='loaded')
    note = fields.Text(string="Informacion Adicional")
    motivo = fields.Text(string="Motivo")
    invoice = fields.Char(string="Factura", size=17)
    invoice_emission_date = fields.Date(string="Fecha Emision Factura")
    ruc_carrier = fields.Char(string="RUC Transportista", required=True)
    social_name = fields.Char(string="Razon Social Transportista", required=True)
    start_street = fields.Char(string="Direccion Partida", required=True)
    company_id = fields.Many2one('res.company', string="Compania", required=True)
    sent = fields.Boolean(string="Enviado")

    @api.multi
    def authorization_document_button(self):
        response = authorization_document(self)
        self.write(response)

    @api.multi
    def authorization_documents_cron(self, *args):
        remissions = self.search([('state', '=', 'loaded')], order='number asc')
        for remission in remissions:
            response = authorization_document(remission)
            remission.write(response)

    @api.multi
    def send_mail_document(self):
        context = {}
        ir_model_data = self.env['ir.model.data']
        template = 'email_template_remisison_guide_electronic'
        try:
            template_id = ir_model_data.get_object_reference('electronic_authorization', template)[1]
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