# -*- coding: utf-8 -*-

""""
AUTORIZACION CON EL SRI, CREACION DEL XML, WEBSERVICES
"""
from odoo import models, fields, api
from odoo.exceptions import UserError
from xml.etree.ElementTree import Element, SubElement, tostring
from suds.client import Client
import random
import re
import os
import base64
from datetime import datetime

NUMBERS = [i for i in range(10)]


def digito_verificador_md11(numeros):
    resultado = 0
    mult = '234567'
    numeros = numeros[::-1]
    for i in range(len(numeros)):
        resultado += int(numeros[i]) * int(mult[i%6])
    resultado = 11 - resultado % 11
    return str(resultado)


def generate_access_key(obj, document_id):
    ruc_company = document_id.company_id.vat
    if not ruc_company:
        raise UserError("Favor configurar el RUC de la compañia para generar la clave de acceso")
    ruc_company = ruc_company[2:]
    webservice_id = obj.env['webservice.sri'].get_webservice_sri()
    environment = webservice_id.environment
    number = document_id.number
    if document_id._name == 'account.withhold.electronic':
        compr = '07'
    else:
        if document_id.type == 'factura':
            compr = '01'
        elif document_id.type == 'credito':
            compr = '04'
        else:
            compr = '05'
    dia, mes, anio = document_id.emission_date.split("-")[::-1]
    clave_aleatoria = ''.join(str(random.choice(NUMBERS)) for i in xrange(8))
    clave_acceso = dia + mes + anio + compr + ruc_company + environment + number.replace("-", "") + clave_aleatoria + '1'# '1' Emision
    clave_acceso += digito_verificador_md11(clave_acceso)
    return clave_acceso


def indent(elem, level=0, context=None):
    if not context: context = {}
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
            if level == 0 and not context.get('out_sri'):
                elem.attrib["id"] = "comprobante"
                if context.get('retention'):
                    elem.attrib["version"] = "1.0.0"
                else:
                    elem.attrib["version"] = "1.1.0"
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def get_vat_type(vat):
    tam = len(vat)
    if tam == 10:
        return '05'
    elif vat == '9'*13:
        return '07'
    elif tam == 13:
        return '04'
    else:
        return '06'


def get_percentage(tax):
    if tax == 2:
        return '12'
    elif tax == 3:
        return '14'
    elif tax == 0:
        return '0'
    return ''


def do_digital_signature(obj, document_xml, type_document):
    from py4j.java_gateway import JavaGateway, GatewayClient
    digital_signature = obj.env['digital.signature'].search([])
    if not digital_signature:
        raise UserError("No tiene una firma digital configurada")
    path, key = digital_signature.path_digital_signature, digital_signature.password_signature
    path_in_xml = open("in_xml.xml", "w")
    document_xml = '<?xml version="1.0" encoding="UTF-8" ?>' + tostring(document_xml)
    document_xml = document_xml
    path_in_xml.write(document_xml)
    path_in_xml.close()
    current_directory = os.getcwd()
    try:
        gateway = JavaGateway(GatewayClient(port=10010))
        entrypt = gateway.entry_point.getGenericXMLSignature()
        entrypt.execute(current_directory+'/'+'in_xml.xml', current_directory+'/', 'out_xml.xml', type_document, path, key)
        document_xml = open('out_xml.xml', 'r')
        data = document_xml.read()
        document_xml.close()
        return data
    except Exception as e:
        return False


def format_date(date):
    return re.sub("([0-9]{4})-([0-9]{2})-([0-9]{2})", r"\3/\2/\1", date)


def authorization_document(document_id):
    environment = document_id.env['webservice.sri'].get_webservice_sri().environment
    if document_id._name == 'account.invoice.electronic':
        document_xml, type_document = generate_xml_invoice(document_id, environment)
    elif document_id._name == 'account.withhold.electronic':
        document_xml, type_document = generate_xml_withhold(document_id, environment)
    else:
        document_xml, type_document = generate_xml_remission(document_id, environment)
    document_signed = do_digital_signature(document_id, document_xml, type_document)
    signed_document_xml = base64.b64encode(document_signed)
    document_id.write({'xml_report': signed_document_xml, 'xml_name': document_id.access_key + '.xml'})
    webservice_obj = document_id.env['webservice.sri']
    response = webservice_obj.send_xml_document_reception(document_signed)
    if response['state'] == 'pass':
        response = webservice_obj.send_xml_document_authorization(document_id.access_key)
    return response


def generate_xml_invoice(invoice, environment):
    if invoice.type == 'factura':
        type_document = 'factura'
        cod_doc = '01'
    elif invoice.type == 'credito':
        type_document = "notaCredito"
        cod_doc = '04'
    else:
        type_document = "notaDebito"
        cod_doc = '05'
    est, pto, sec = invoice.number.split("-")
    clave_acceso = invoice.access_key
    root = Element(type_document)
    tributaria = SubElement(root, "infoTributaria")
    SubElement(tributaria, "ambiente").text = environment
    SubElement(tributaria, "tipoEmision").text = '1'
    SubElement(tributaria, "razonSocial").text = invoice.company_id.name
    SubElement(tributaria, "nombreComercial").text = invoice.company_id.name
    SubElement(tributaria, "ruc").text = invoice.company_id.partner_id.vat[2:]
    SubElement(tributaria, "claveAcceso").text = clave_acceso
    SubElement(tributaria, "codDoc").text = cod_doc
    SubElement(tributaria, "estab").text = est
    SubElement(tributaria, "ptoEmi").text = pto
    SubElement(tributaria, "secuencial").text = sec
    SubElement(tributaria, "dirMatriz").text = invoice.company_id.street
    if type_document == "factura":
        factura = SubElement(root, "infoFactura")
    elif type_document == "notaCredito":
        factura = SubElement(root, "infoNotaCredito")
    else:
        factura = SubElement(root, "infoNotaDebito")
    SubElement(factura, "fechaEmision").text = format_date(invoice.emission_date)
    SubElement(factura, "dirEstablecimiento").text = invoice.company_id.street
    if type_document != "debito":
        if invoice.company_id.contributed:
            SubElement(factura, "contribuyenteEspecial").text = str(invoice.company_id.contributed)
        SubElement(factura, "obligadoContabilidad").text = "NO" if not invoice.company_id.must_account else "SI"
    else:
        SubElement(factura, "obligadoContabilidad").text = "NO" if not invoice.company_id.must_account else "SI"
        if invoice.company_id.contributed:
            SubElement(factura, "contribuyenteEspecial").text = str(invoice.company_id.contributed)
    SubElement(factura, "tipoIdentificacionComprador").text = get_vat_type(invoice.partner_id.vat)
    if invoice.type == 'factura' and invoice.remission_guide:
        SubElement(factura, "guiaRemision").text = invoice.remission_guide
    SubElement(factura, "razonSocialComprador").text = invoice.partner_id.name
    SubElement(factura, "identificacionComprador").text = invoice.partner_id.vat[2:]
    SubElement(factura, "direccionComprador").text = invoice.street
    if type_document == "notaCredito":
        SubElement(factura, "codDocModificado").text = "01"
        SubElement(factura, "numDocModificado").text = invoice.number_fact
        SubElement(factura, "fechaEmisionDocSustento").text = invoice.number_fact_date
    SubElement(factura, "totalSinImpuestos").text = str(invoice.subtotal)
    if type_document == "notaCredito":
        SubElement(factura, "valorModificacion").text = str(invoice.total)
    if type_document == "factura":
        SubElement(factura, "totalDescuento").text = str(invoice.total_discount)
    line_id = invoice.line_id
    if line_id:
        ttconimpuestos = SubElement(factura, "totalConImpuestos")
        for taxe in line_id:
            ttimpuesto = SubElement(ttconimpuestos, "totalImpuesto")
            SubElement(ttimpuesto, "codigo").text = '2'
            SubElement(ttimpuesto, "codigoPorcentaje").text = str(taxe.tax)
            SubElement(ttimpuesto, "baseImponible").text = str(round(taxe.price_unit * taxe.quantity, 2))
            SubElement(ttimpuesto, "valor").text = str(taxe.total)
    if type_document == "factura":
        SubElement(factura, "propina").text = "0.0"
        SubElement(factura, "importeTotal").text = str(invoice.total)
        SubElement(factura, "moneda").text = "DOLAR"
        # formas de pago
        if invoice.payment_ids:
            pagos = SubElement(factura, "pagos")
            for waypay in invoice.payment_ids:
                pago = SubElement(pagos, "pago")
                SubElement(pago, "formaPago").text = str(waypay.payment_id.code)
                SubElement(pago, "total").text = str(waypay.amount)
                if waypay.plazo:
                    SubElement(pago, "plazo").text = str(waypay.plazo)
                if waypay.unit:
                    SubElement(pago, "unidadTiempo").text = waypay.unit
    if type_document == "notaCredito":
        SubElement(factura, "motivo").text = "DEVOLUCION"
    detalles = SubElement(root, "detalles")
    if line_id:
        for line in line_id:
            dttline = SubElement(detalles, "detalle")
            cPrincipal = line.code
            if len(line.name) > 25:
                cPrincipal = line.code[:25]
            if type_document == "factura":
                SubElement(dttline, "codigoPrincipal").text = cPrincipal.encode('ascii', 'ignore')
            if type_document == "notaCredito":
                SubElement(dttline, "codigoInterno").text = cPrincipal.encode('ascii', 'ignore')
            SubElement(dttline, "descripcion").text = line.name.encode('ascii', 'ignore')
            SubElement(dttline, "cantidad").text = str(line.quantity)
            SubElement(dttline, "precioUnitario").text = str(line.price_unit)
            SubElement(dttline, "descuento").text = str(line.discount)
            SubElement(dttline, "precioTotalSinImpuesto").text = str(round(line.price_unit * line.quantity, 2))
            detalle_impuestos = SubElement(dttline, "impuestos")
            dtle_impuesto = SubElement(detalle_impuestos, "impuesto")
            SubElement(dtle_impuesto, "codigo").text = '2'
            SubElement(dtle_impuesto, "codigoPorcentaje").text = str(line.tax)
            SubElement(dtle_impuesto, "tarifa").text = get_percentage(line.tax)
            SubElement(dtle_impuesto, "baseImponible").text = str(round(line.price_unit * line.quantity, 2))
            SubElement(dtle_impuesto, "valor").text = str(line.total)
    indent(root)
    return root, type_document


def generate_xml_withhold(withhold_id, environment):
    type_document = "comprobanteRetencion"
    est, pto, sec = withhold_id.number.split("-")
    access_key = withhold_id.access_key
    root = Element(type_document)
    tributaria = SubElement(root, "infoTributaria")
    SubElement(tributaria, "ambiente").text = environment
    SubElement(tributaria, "tipoEmision").text = '1'
    SubElement(tributaria, "razonSocial").text = withhold_id.company_id.name
    SubElement(tributaria, "nombreComercial").text = withhold_id.company_id.name
    SubElement(tributaria, "ruc").text = withhold_id.company_id.vat
    SubElement(tributaria, "claveAcceso").text = access_key
    SubElement(tributaria, "codDoc").text = '07'
    SubElement(tributaria, "estab").text = est
    SubElement(tributaria, "ptoEmi").text = pto
    SubElement(tributaria, "secuencial").text = sec
    SubElement(tributaria, "dirMatriz").text = withhold_id.company_id.street
    retencion = SubElement(root, "infoCompRetencion")
    SubElement(retencion, "fechaEmision").text = format_date(withhold_id.emission_date)
    SubElement(retencion, "dirEstablecimiento").text = withhold_id.company_id.street
    SubElement(retencion, "tipoIdentificacionSujetoRetenido").text = get_vat_type(withhold_id.partner_id.vat[2:])
    SubElement(retencion, "razonSocialSujetoRetenido").text = withhold_id.partner_id.name
    SubElement(retencion, "identificacionSujetoRetenido").text = withhold_id.partner_id.vat[2:]
    SubElement(retencion, "periodoFiscal").text = withhold_id.fiscalyear
    detalle_impuestos = SubElement(root, "impuestos")
    for line in withhold_id.line_id:
        impuesto = SubElement(detalle_impuestos, "impuesto")
        SubElement(impuesto, "codigo").text = line.tax_name
        SubElement(impuesto, "codigoRetencion").text = line.code
        SubElement(impuesto, "baseImponible").text = str(line.base_amount)
        SubElement(impuesto, "porcentajeRetener").text = str(line.tax)
        SubElement(impuesto, "valorRetenido").text = str(line.tax_amount)
        SubElement(impuesto, "codDocSustento").text = '01'
        SubElement(impuesto, "numDocSustento").text = line.num_fact.replace("-", "")
        SubElement(impuesto, "fechaEmisionDocSustento").text = format_date(line.emission_date_fact)
    indent(root, context={'retention': True})
    return root, type_document


def generate_xml_remission(remission, environment):
    pass


class WebserviceSri(models.Model):
    _name = 'webservice.sri'
    _rec_name = 'name'

    name = fields.Char(string="Webservices", readonly=True, default='WEBSERVICES SRI')
    url_reception = fields.Char(string="URL Recepcion", required=True)
    url_authorization = fields.Char(string="URL Autorización", required=True)
    motive_reception = fields.Char(string="Razón", readonly=True)
    motive_authorization = fields.Char(string="Razón", readonly=True)
    state_url_authorization = fields.Selection([('up', 'Activo'),
                                                ('down', 'Inactivo')], string='Estado Autorización', readonly=True,
                                               default='up')
    state_url_reception = fields.Selection([('up', 'Activo'),
                                            ('down', 'Inactivo')], string='Estado Recepción', readonly=True,
                                           default='up')
    environment = fields.Selection([('2', 'Produccion'),
                                    ('1', 'Pruebas')], string='Ambiente', required=True, default='2')
    activo = fields.Boolean(string="En uso")

    def _format_response_sri(self, response, reception=False):
        result = {}
        mensaje = response.comprobantes.comprobante[0].mensajes[0]
        if mensaje[0].tipo == 'ERROR':
            result['sri_response'] = mensaje[0].mensaje + mensaje[0].informacionAdicional
            result['state'] = 'unauthorized'
        elif not reception:
            result['sri_response'] = 'DOCUMENTO AUTORIZADO'
            result['state'] = 'authorized'
            result['authorized_date'] = datetime.now()
        else:
            result['state'] = 'pass'
        return result

    def send_xml_document_reception(self, xml_document):
        webservice = self.get_webservice_sri()
        sri_reception = Client(webservice.url_reception)
        return self._format_response_sri(sri_reception.service.validarComprobante(xml_document), reception=True)

    def send_xml_document_authorization(self, access_key):
        webservice = self.get_webservice_sri()
        sri_authorization = Client(webservice.url_authorization)
        return self._format_response_sri(
            sri_authorization.service.autorizacionComprobante(claveAccesoComprobante=access_key))

    def update_state(self, message, url='authorization', state='down'):
        vals = {}
        if url == 'reception':
            vals['motive_reception'] = message
            vals['state_url_reception'] = state
        else:
            vals['motive_authorization'] = message
            vals['state_url_authorization'] = state
        self.write(vals)

    @api.model
    def create(self, vals):
        if vals['activo']:
            webservice = self.search([('activo', '=', True)])
            if webservice:
                raise UserError("Ya tiene un webservice activo, favor desactivarla primero y "
                                "luego activar la que esta creando")
        return super(WebserviceSri, self).create(vals)

    @api.one
    def write(self, vals):
        if vals.get('activo'):
            webservice = self.search([('activo', '=', True)])
            if webservice:
                raise UserError("Ya tiene un webservice activo, favor desactivarla primero y "
                                "luego activar la que esta creando")
        return super(WebserviceSri, self).write(vals)

    @api.model
    def get_webservice_sri(self):
        return self.search([('activo', '=', True)])


class DigitalSignature(models.Model):
    _name = 'digital.signature'
    _rec_name = 'name'

    electronic_signature = fields.Binary(string="Firma Digital", help="Aqui se carga la firma digital", required=True)
    password_signature = fields.Char(string="Password", required=True)
    expiration_date = fields.Date(string="Fecha de Expiracion", required=True)
    email_notification = fields.Char(string="Correo Electronico a Notificar", required=True,
                                     help="Se enviara notificaciones cuando la firma este cerca de caducarse "
                                          "y debe renovarlo")
    name = fields.Char(string="Nombre")
    path_digital_signature = fields.Char(string="Ruta firma digital")

    def _send_mail_notification_expiration(self, email_notification, days):
        ir_mail_server_obj = self.env['ir.mail_server']
        email_to = [email_notification]
        email_from = self.env['res.users'].browse(self._uid).company_id.email
        subject = 'Expiracion de la Firma Digital'
        body = 'La firma digital expirara en %s dias' % days
        msg = ir_mail_server_obj.build_email(self, email_from, email_to, subject, body,
                                             subtype_alternative='plain')
        ir_mail_server_obj.send_email(msg)

    @api.model
    def send_mail_notification_expiration(self):
        digital_signature = self.get_digital_signature()
        expiration_date = datetime.strptime(digital_signature.expiration_date, "%Y-%m-%d")
        now = datetime.now().date()
        difference = expiration_date - now
        if difference.days <= 30:
            self._send_mail_notification_expiration(digital_signature.email_notification, difference.days)

    @api.model
    def create(self, values):
        with open(values.get('name'), 'w+') as fp:
            fp.write(base64.b64decode(values['electronic_signature']))
        values['path_digital_signature'] = os.getcwd() + '/' + values.get('name')
        return super(DigitalSignature, self).create(values)

    @api.model
    def get_digital_signature(self):
        digital_signature = self.search([])
        return digital_signature

    @api.one
    def write(self, values):
        if 'electronic_signature' in values:
            with open(values.get('name'), 'w+') as fp:
                fp.write(base64.b64decode(values['electronic_signature']))
            values['path_digital_signature'] = os.getcwd() + '/' + values.get('name')
        return super(DigitalSignature, self).write(values)
