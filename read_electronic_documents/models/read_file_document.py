from odoo import fields, models, api
from odoo.exceptions import UserError
from electronic_tools import *
from datetime import datetime


class FileDocuments(models.Model):
    _name = 'file.documents'

    name = fields.Char(string="Nombre", require=True)
    data = fields.Binary(string="Archivo", required=True)
    errors = fields.Text(string="Errores")
    created_date = fields.Date(string="Fecha creacion", required=True, readonly=True, default=lambda *a: datetime.now().date())

    @api.model
    def create(self, values):
        data = values['data'].decode('base64')
        data = data.split("\n")
        delimiter = self.env['setting.read.file'].get_delimiter()
        document_type = data[0].strip("\r")
        if document_type in ('factura', 'credito', 'debito'):
            data, errors = read_file_invoice(data, delimiter)
            create_invoice_from_file(self, data, document_type)
        elif document_type == 'retencion':
            data, errors = read_file_withhold(self, data, delimiter)
            create_withhold_from_file(self, data)
        elif document_type == 'remision':
            data, errors = read_file_remission(data, delimiter)
            create_remission_from_file(self, data)
        else:
            raise UserError("""No es posible leer el archivo, no entiendo a que
                               documento pertenece. Asegurese de que en la primera
                               linea este el nombre del documento""")
        values['errors'] = "".join(errors)
        return super(FileDocuments, self).create(values)
