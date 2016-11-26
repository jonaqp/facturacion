from odoo import models, fields


class SettingReadFile(models.Model):
    _name = 'setting.read.file'

    delimiter = fields.Char(string="Delimitador", size=1, default='|')

    def get_delimiter(self):
        return self.search([])[0].delimiter