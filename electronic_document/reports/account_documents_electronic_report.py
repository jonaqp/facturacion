from reportlab.graphics.barcode import code128
from reportlab.platypus import Frame, Paragraph, KeepInFrame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import enums
from reportlab.pdfgen import canvas


class AccountDocumentsElectronicReport:

    def __init__(self, object, name, image=None):
        self.object = object
        self.image = image
        self.name = name
        self.style_own14 = ParagraphStyle(name='Title',
                                     fontSize=14,
                                     leading=22,
                                     alignment=enums.TA_CENTER,
                                     spaceAfter=6)
        self.style_own10 = ParagraphStyle(name='Title',
                                     fontSize=10,
                                     leading=12,
                                     alignment=enums.TA_LEFT,
                                     spaceAfter=2)

    def generate_pdf(self):
        pdf = canvas.Canvas('%s-%s.pdf' % (self.name, self.object.number))
        pdf = self.put_corner_left_data(pdf)
        pdf = self.put_corner_right_data(pdf)
        if self.name.lower() == 'factura':
            pdf = self.put_middle_data_factura(pdf)
        elif self.name.lower() == 'nota de credito':
            pdf = self.put_middle_data_nc(pdf)
        elif self.name.lower() == 'nota de debito':
            pdf = self.put_middle_data_nd(pdf)
        elif self.name.lower() == 'comprobante de retencion':
            pdf = self.put_middle_data_withhold(pdf)
        else:
            pdf = self.put_middle_data_remission(pdf)
        pdf.showPage()
        pdf.save()

    def put_middle_data_factura(self, pdf):
        pdf.setFont('Times-Bold', 10)
        pdf.drawString(60, 580, 'Razon Social:')
        pdf.setFont('Times-Roman', 10)
        pdf.drawString(125, 580, self.object.partner_id.name)
        pdf.setFont('Times-Bold', 10)
        pdf.drawString(60, 560, 'Direccion:')
        pdf.setFont('Times-Roman', 10)
        pdf.drawString(125, 560, self.object.partner_id.street)
        pdf.setFont('Times-Bold', 10)
        pdf.drawString(60, 540, 'Cedula/RUC:')
        pdf.setFont('Times-Roman', 10)
        pdf.drawString(125, 540, self.object.partner_id.vat[2:])
        pdf.setFont('Times-Bold', 10)
        pdf.drawString(380, 580, 'Fecha de Emision:')
        pdf.setFont('Times-Roman', 10)
        pdf.drawString(465, 580, self.object.emission_date)
        pdf.setFont('Times-Bold', 10)
        pdf.drawString(380, 560, 'Telefono:')
        pdf.setFont('Times-Roman', 10)
        pdf.drawString(460, 520, self.object.partner_id.phone)
        pdf.rect(50, 530, 530, 65)
        return pdf

    def put_middle_data_nc(self, pdf):
        pass

    def put_middle_data_nd(self, pdf):
        pass

    def put_middle_data_withhold(self, pdf):
        pass

    def put_middle_data_remission(self, pdf):
        pass

    def put_corner_left_data(self, pdf):
        pdf.drawInlineImage(self.image, 100, 720, width=125, height=120)
        frame1 = Frame(50, 670, 220, 50)
        pa = Paragraph(self.object.company_id.name, self.style_own14)
        story_inframe = KeepInFrame(220, 70, [pa], hAlign='CENTER', vAlign='MIDDLE')
        frame1.addFromList([story_inframe], pdf)
        pdf.setFont('Times-Bold', 10)
        pdf.drawString(60, 680, 'Direccion:')
        pdf.setFont('Times-Roman', 10)
        frame2 = Frame(110, 646, 150, 50)
        pa = Paragraph(self.object.company_id.street, self.style_own10)
        story_inframe = KeepInFrame(150, 70, [pa], hAlign='CENTER', vAlign='MIDDLE')
        frame2.addFromList([story_inframe], pdf)
        pdf.setFont('Times-Bold', 10)
        pdf.drawString(60, 655, 'Telefono:')
        pdf.setFont('Times-Roman', 10)
        pdf.drawString(120, 655, self.object.company_id.phone)
        if self.object.company_id.must_account:
            pdf.drawString(60, 635, 'OBLIGADO A LLEVAR CONTABILIDAD')
        pdf.drawString(100, 615, self.object.company_id.email)
        pdf.rect(50, 600, 220, 115)
        return pdf

    def put_corner_right_data(self, pdf):
        pdf.setFont('Times-Bold', 12)
        pdf.drawString(350, 810, 'R.U.C ' + self.object.company_id.vat[2:])
        pdf.drawString(350, 790, self.name)
        pdf.drawString(350, 770, 'No. ' + self.object.number)
        pdf.setFont('Times-Bold', 10)
        pdf.drawString(350, 750, 'NUMERO DE AUTORIZACION')
        pdf.setFont('Times-Roman', 9)
        pdf.drawString(350, 730, self.object.electronic_authorization)
        pdf.setFont('Times-Bold', 10)
        env = 'PRODUCCION'
        if self.object.env['webservice.sri'].get_webservice_sri().environment == '1':
            env = 'PRUEBAS'
        pdf.drawString(350, 710, 'Fecha y hora de autorizacion: ' + str(self.object.authorization_date))
        pdf.drawString(350, 690, 'Ambiente: ' + env)
        pdf.drawString(350, 670, 'Emision: Normal')
        pdf.setFontSize(10)
        pdf.drawString(350, 655, 'CLAVE DE ACCESO')
        barcode = code128.Code128(self.object.access_key)
        barcode.drawOn(pdf, 350, 625)
        pdf.setFont('Times-Roman', 8)
        pdf.drawString(355, 610, self.object.access_key)
        pdf.rect(330, 600, 250, 230)
        return pdf



