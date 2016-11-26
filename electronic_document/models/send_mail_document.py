from odoo import models, api, fields, tools


class SendMailDocument(models.TransientModel):
    _name = 'send.mail.document'

    recipients = fields.Char(string="Enviar a", help="Para varios correos separar por punto y coma(;)")
    subject = fields.Char(string="Asunto")
    body = fields.Html(string="Cuerpo",  sanitize=False, translate=True)
    sender = fields.Char(string="De", readonly=True)
    name = fields.Char(string="Nombre")
    attachment_ids = fields.Many2many('ir.attachment', string="Adjuntos")
    email_cc = fields.Char(string="CC", help="Para varios correos separar por punto y coma(;)")

    @api.model
    def default_get(self, fields_list):
        res = super(SendMailDocument, self).default_get(fields_list)
        context = self._context
        if not context.get('install_mode'):
            res['recipients'] = context['recipients']
            template_id = self.browse(context.get('default_template_id'))
            res['body'] = tools.html_sanitize(template_id.body)
            res['name'] = template_id.name
            res['subject'] = template_id.subject
            res['email_cc'] = ''
            partner_id = self.env['res.users'].browse(self._uid).partner_id
            res['sender'] = '%s <%s>' % (partner_id.name, partner_id.email)
        return res

    def _send_email(self):
        ir_mail_server_obj = self.env['ir.mail_server']
        email_to = self.recipients.split(";")
        email_cc = self.email_cc.split(";") if self.email_cc else []
        email_from = self.sender
        msg = ir_mail_server_obj.build_email(email_from, email_to, self.subject, self.body, email_cc=email_cc,
                                             subtype_alternative='plain')
        message_id = ir_mail_server_obj.send_email(msg)

    @api.multi
    def send_email_documents(self, *args, **kwargs):
        self._send_email()
