from odoo import models


class EmailTemplate(models.Model):
    '''
    Open ERP Model
    '''
    _inherit = 'email.template'

    def generate_email_batch(self, cr, uid, template_id, res_id, context=None, fields=None):
        """Generates an email from the template for given (model, res_id) pair.

           :param template_id: id of the template to render.
           :param res_id: id of the record to use for rendering the template (model
                          is taken from template definition)
           :returns: a dict containing all relevant fields for creating a new
                     mail.mail entry, with one extra key ``attachments``, in the
                     format expected by :py:meth:`mail_thread.message_post`.
        """
        res = super(EmailTemplate, self).generate_email_batch(cr, uid, template_id, res_id, context=context,
                                                              fields=fields)
        if context.get('active_model') in ('account.invoice', 'account.withhold'):
            model_id = self.pool.get(context.get('active_model')).browse(cr, uid, context.get('active_id'))
            result, report_name = model_id.xml_report, model_id.xml_name
            res[res_id[0]]['attachments'].append((report_name, result))
        return res