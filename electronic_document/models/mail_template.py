from odoo import models, api


class MailTemplate(models.Model):
    '''
    Open ERP Model
    '''
    _inherit = 'mail.template'

    @api.multi
    def generate_email(self, res_id, fields=None):
        """Generates an email from the template for given (model, res_id) pair.

           :param template_id: id of the template to render.
           :param res_id: id of the record to use for rendering the template (model
                          is taken from template definition)
           :returns: a dict containing all relevant fields for creating a new
                     mail.mail entry, with one extra key ``attachments``, in the
                     format expected by :py:meth:`mail_thread.message_post`.
        """
        res = super(MailTemplate, self).generate_email(res_id, fields=fields)
        if isinstance(res_id, list):
            res_id = res_id[0]
        if self.model in ('account.invoice.electronic', 'account.withhold.electronic', 'remission.guide.electronic'):
            model_id = self.env[self.model].browse(res_id)
            result, report_name = model_id.xml_report, model_id.xml_name
            if result:
                if res_id in res:
                    res[res_id].setdefault('attachments', []).append((report_name, result))
                else:
                    res.setdefault('attachments', []).append((report_name, result))
        return res