# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import datetime
import pytz
from odoo.exceptions import UserError
from core_electronic_authorization.authorization_sri import authorization_document, generate_access_key, update_xml_report


class AccountInvoiceElectronic(models.Model):
    _name = 'account.invoice.electronic'
    _inherit = ['mail.thread']
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

    dat = pytz.utc.localize(datetime.now()).astimezone(pytz.timezone('America/Guayaquil'))
    number = fields.Char(string="Numero", size=17, states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)], 'unauthorized': [('readonly', True)], 'draft': [('required', False)]})
    emission_date = fields.Date(string="Fecha Emisión", required=True, default=dat.date,  states={'authorized': [('readonly', True)], 'loaded': [('readonly', True)]})
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
        access_key = generate_access_key(self, self)
        self.write({'access_key': access_key, 'electronic_authorization': access_key})

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
        subtotal_taxed = subtotal_0 = 0.0
        if self.type == 'debito':
            subtotal_taxed = self.modification_value
            tax += self.modification_value * 0.14
        else:
            for line in self.line_id:
                if line.tax.code == '0':
                    subtotal_0 += round(line.total, 2)
                else:
                    subtotal_taxed += round(line.total, 2)
                    tax += round(line.total * line.tax.percentage / 100, 2)
        self.taxed = tax
        self.subtotal_taxed = subtotal_taxed
        self.subtotal_0 = subtotal_0
        self.subtotal_taxed = subtotal_taxed + subtotal_0
        self.total = tax + subtotal_taxed + subtotal_0 - self.tax_comp

    @api.multi
    def change_state_to(self):
        for invoice in self:
            number = self._get_number()
            access_key = generate_access_key(self, invoice, number)
            invoice.write({'state': 'loaded', 'number': number,
                           'access_key': access_key, 'electronic_authorization': access_key})

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
    def send_mail_documents_cron(self, *args):
        invoices = self.search([('state', '=', 'authorized'), ('sent', '=', False)], order='type asc')
        ir_model_data = self.env['ir.model.data']
        for invoice in invoices:
            if invoice.type == 'factura':
                template = 'email_template_account_invoice_electronic'
            elif invoice.type == 'credito':
                template = 'email_template_account_invoice_nc_electronic'
            else:
                template = 'email_template_account_invoice_nd_electronic'
            try:
                template_id = ir_model_data.get_object_reference('electronic_document', template)[1]
            except ValueError:
                template_id = False
            template_id = self.env['mail.template'].browse(template_id)
            template_id.send_mail(invoice.id, force_send=True)
            invoice.sent = True

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

    @api.multi
    def print_document(self):
        from reportlab.pdfgen import canvas
        import base64
        import tempfile
        from reportlab.graphics.barcode import code128
        from reportlab.platypus import Frame, Paragraph, KeepInFrame
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import enums
        style_own14 = ParagraphStyle(name='Title',
                                  fontSize=14,
                                  leading=22,
                                  alignment=enums.TA_CENTER,
                                  spaceAfter=6)
        style_own10 = ParagraphStyle(name='Title',
                                     fontSize=10,
                                     leading=12,
                                     alignment=enums.TA_LEFT,
                                     spaceAfter=2)
        webservice_obj = self.env['webservice.sri']
        styles = getSampleStyleSheet()
        for invoice in self:
            if invoice.type == 'factura':
                tipo = 'FACTURA'
            elif invoice.type == 'credito':
                tipo = 'NOTA DE CREDITO'
            else:
                tipo = 'NOTA DE DEBITO'
            pdf = canvas.Canvas('test.pdf')
            path_in_xml = tempfile.NamedTemporaryFile(suffix='.png', mode='wb')
            path_in_xml.write(base64.decodestring(invoice.company_id.logo))
            path_in_xml.flush()
            ###### LADO SUPERIOR IZQUIERDO DEL PDF
            pdf.drawInlineImage(path_in_xml.name, 100, 720, width=125, height=120)
            frame1 = Frame(50, 670, 220, 50)
            pa = Paragraph(invoice.company_id.name, style_own14)
            story_inframe = KeepInFrame(220, 70, [pa], hAlign='CENTER', vAlign='MIDDLE')
            frame1.addFromList([story_inframe], pdf)
            # pdf.drawString(150, 700, invoice.company_id.name)
            pdf.setFont('Times-Bold', 10)
            pdf.drawString(60, 680, 'Direccion:')
            pdf.setFont('Times-Roman', 10)
            frame2 = Frame(110, 646, 150, 50)
            pa = Paragraph(invoice.company_id.street, style_own10)
            story_inframe = KeepInFrame(150, 70, [pa], hAlign='CENTER', vAlign='MIDDLE')
            frame2.addFromList([story_inframe], pdf)
            #pdf.drawString(120, 675, invoice.company_id.street)
            pdf.setFont('Times-Bold', 10)
            pdf.drawString(60, 655, 'Telefono:')
            pdf.setFont('Times-Roman', 10)
            pdf.drawString(120, 655, invoice.company_id.phone)
            if invoice.company_id.must_account:
                pdf.drawString(60, 635, 'OBLIGADO A LLEVAR CONTABILIDAD')
            pdf.drawString(100, 615, invoice.company_id.email)
            pdf.rect(50, 600, 220, 115)
            ######### LADO DERECHO DEL PDF
            pdf.setFont('Times-Bold', 12)
            pdf.drawString(350, 810, 'R.U.C ' + invoice.company_id.vat[2:])
            pdf.drawString(350, 790, tipo)
            pdf.drawString(350, 770, 'No. ' + invoice.number)
            pdf.setFont('Times-Bold', 10)
            pdf.drawString(350, 750, 'NUMERO DE AUTORIZACION')
            pdf.setFont('Times-Roman', 9)
            pdf.drawString(350, 730, invoice.electronic_authorization)
            pdf.setFont('Times-Bold', 10)
            env = 'PRODUCCION'
            if webservice_obj.get_webservice_sri().environment == '1':
                env = 'PRUEBAS'
            pdf.drawString(350, 710, 'Fecha y hora de autorizacion: ' + str(invoice.authorization_date))
            pdf.drawString(350, 690, 'Ambiente: ' + env)
            pdf.drawString(350, 670, 'Emision: Normal')
            pdf.setFontSize(10)
            pdf.drawString(350, 655, 'CLAVE DE ACCESO')
            barcode = code128.Code128(invoice.access_key)
            barcode.drawOn(pdf, 350, 625)
            pdf.setFont('Times-Roman', 8)
            pdf.drawString(355, 610, invoice.access_key)
            pdf.rect(330, 600, 250, 230)
            pdf.showPage()
            pdf.save()
        path_in_xml.close()


class AccountInvoiceElectronicLine(models.Model):
    _name = 'account.invoice.electronic.line'

    code = fields.Char(string="Codigo", required=True)
    name = fields.Char(string="Producto", required=True)
    quantity = fields.Float(string="Cantidad", required=True)
    price_unit = fields.Float(string="Precio Unitario", required=True)
    discount = fields.Float(string="Descuento")
    total = fields.Float(string="Total", required=True, compute='_get_total_line')
    tax = fields.Many2one('account.tax.electronic', string='Impuesto', required=True)
    invoice_id = fields.Many2one('account.invoice.electronic', string="Facturas")

    @api.one
    def _get_total_line(self):
        self.total = self.quantity * self.price_unit - self.discount
