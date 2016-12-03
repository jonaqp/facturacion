# -*- coding: utf-8 -*-

""""
Eletronic Tools provide methods for read documents from files,
read documents from a database, search partner, payment_method
"""

import re
from core_electronic_authorization.authorization_sri import generate_access_key
import plantilla_factura
import plantilla_retencion
import plantilla_guia
import base64


def check_document(obj, number, model, document_type=''):
	args = []
	if document_type:
		args = [('type', '=', document_type)]
	return bool(obj.env[model].search([('number', '=', number)] + args))


def search_payment_method(obj, code):
	payment_id = obj.env['payment.method'].search([('code', '=', code)])
	return payment_id and payment_id.id


def search_partner(obj, vat, values):
	partner_obj = obj.env['res.partner']
	partner_id = partner_obj.search([('vat', '=', vat)])
	if partner_id:
		if re.match(".*@.*", values['email']):
			partner_id.write({'email': values['email']})
		return partner_id.id
	else:
		return partner_obj.create({'vat': vat, 'name': values['partner_name'],
                                   'street': values['street'], 'email': values['email']}).id


def check_format(fila, datas, count):
	errors = ''
	for index, cls in enumerate(fila):
		if hasattr(cls, 'match'):
			if not cls.match(datas[index]):
				errors += 'Linea %s: Error en columna %s. Verificar el formato; palabra clave(%s)\n' % (count, index + 1, datas[index])
		else:
			try:
				cls(datas[index])
			except UnicodeError as e:
				pass
			except ValueError as e:
				errors += 'Linea %s: Error en columna %s. Verificar el formato, no es un numero; palabra clave(%s)\n' % (count, index + 1, datas[index])
			except IndexError as e:
				errors += 'Linea %s: Falta un dato. Favor verificar la plantilla; palabra clave(%s)\n' % (count, datas[index-1])
	return errors


def read_file_invoice(datas, delimiter):
	""""
    Return data mapping for invoices, withhold and remission
    """
	value = {}
	number = ''
	errors = []
	i = 0
	for data in datas:
		i += 1
		data = unicode(data, 'utf-8')
		document_data = data.split(delimiter)
		if document_data[0] == 'n':
			if document_data[1] not in value:
				value[document_data[1]] = {}
				number = document_data[1]
				value[number]['fp'] = []
				value[number]['p'] = []
				error = check_format(plantilla_factura.n, document_data[1:], i)
				if error:
					errors.append(error)
					value[number]['errors'] = True
					continue
		elif document_data[0] == 'g':
			value[number]['remission_guide'] = document_data[0].strip()
		elif document_data[0] == 'i':
			error = check_format(plantilla_factura.i, document_data[1:], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
			value[number]['emission_date'] = document_data[1].strip()
			value[number]['partner_name'] = document_data[2].strip()
			value[number]['vat'] = document_data[3].strip()
			value[number]['street'] = document_data[4].strip()
			value[number]['email'] = document_data[5]
		elif document_data[0] == 'nc':
			error = check_format(plantilla_factura.nc, document_data[1:], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
			value[number]['number_fact'] = document_data[1]
			value[number]['motive'] = unicode(document_data[3].strip(), 'utf-8').encode('utf-8')
			value[number]['number_fact_date'] = document_data[2]
		elif document_data[0] == 'fp':
			error = check_format(plantilla_factura.fp, document_data[1:], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
			value[number]['fp'].append(
			                    {'name': document_data[1],
			                     'amount': float(document_data[2]),
			                     'plazo': document_data[3].strip() if len(document_data) > 2 else '',
			                     'unit': document_data[4].strip() if len(document_data) > 3 else ''}
			                    )
		elif document_data[0] == 't':
			error = check_format(plantilla_factura.t, document_data[1:], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
			value[number]['subtotal'] = float(document_data[1])
			value[number]['taxed'] = float(document_data[2])
			value[number]['total_discount'] = float(document_data[3])
			value[number]['total'] = float(document_data[4])
		elif document_data[0].strip('\r') == 'c':
			value[number]['tax_comp_bool'] = True
		elif document_data[0] == 'p':
			error = check_format(plantilla_factura.p, document_data[1:], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
			value[number]['p'].append({
										'code': document_data[1],
										'name': document_data[2],
										'quantity': document_data[3],
										'price_unit': document_data[4],
										'discount': document_data[5],
										'total': document_data[6],
										'tax': document_data[7]
										})
	return value, errors


def create_invoice_from_file(self, values, document_type):
	account_tax = self.env['account.tax.electronic']
	for number in values:
		if check_document(self, number, 'account.invoice.electronic', document_type=document_type):
			continue
		if values[number].get('errors'):
			continue
		partner_id = search_partner(self, values[number]['vat'], values[number])
		values[number]['partner_id'] = partner_id
		values[number].pop('partner_name')
		values[number]['number'] = number
		values[number]['type'] = document_type
		subtotal_iva = 0.0
		subtotal_0 = 0.0
		values[number]['subtotal_0'] = 0.0
		line_ids = []
		for product in values[number]['p']:
			if int(product['tax']) != 0:
				subtotal_iva += float(product['total'])
			else:
				subtotal_0 += float(product['total'])
			product['tax'] = account_tax.search([('code', '=', str(int(product['tax'])))])[0].id
			line_ids.append((0, 0, product))
		methods = []
		values[number]['subtotal_taxed'] = subtotal_iva
		values[number]['subtotal_0'] = subtotal_0
		for method in values[number]['fp']:
			method_id = search_payment_method(self, method['name'])
			method.pop('name')
			method['payment_id'] = method_id
			methods.append((0, 0, method))
		if values[number].get('tax_comp_bool'):
			values[number]['tax_comp'] = values[number]['taxed'] * .02
		values[number]['line_id'] = line_ids
		values[number]['payment_ids'] = methods
		values[number]['company_id'] = self.env['res.users'].browse(self._uid).company_id.id
		values[number]['state'] = 'loaded'
		invoice_id = self.env['account.invoice.electronic'].create(values[number])
		access_key = generate_access_key(self, invoice_id)
		invoice_id.write({'access_key': access_key, 'electronic_authorization': access_key})


def read_file_withhold(datas, delimiter):
	""""
    Return data mapping for invoices, withhold and remission
    """
	value = {}
	errors = []
	i = 0
	for data in datas:
		i += 1
		document_data = data.split(delimiter)
		if document_data[0] == 'n':
			if document_data[1] not in value:
				number = document_data[1]
				value[number] = {}
				value[number]['d'] = []
				error = check_format(plantilla_retencion.n, document_data[1:], i)
				if error:
					errors.append(error)
					value[number]['errors'] = True
					continue
		elif document_data[0] == 'i':
			error = check_format(plantilla_retencion.i, document_data[1:], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
			value[number]['emission_date'] = document_data[1].strip()
			value[number]['fiscalyear'] = document_data[2].strip()
			value[number]['partner_name'] = document_data[3].strip()
			value[number]['vat'] = document_data[4].strip()
			value[number]['street'] = document_data[5].strip()
			value[number]['email'] = document_data[6]
		elif document_data[0] == 'd':
			error = check_format(plantilla_retencion.d, document_data[1:], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
			value[number]['d'].append([{
	                            'name': document_data[1],
								'code': document_data[2],
	                            'base_amount': document_data[3],
	                            'tax': document_data[4],
	                            'tax_amount': document_data[5],
	                            'tax_name': document_data[6],
	                            'num_fact': document_data[7],
	                            'emission_date_fact': document_data[8]
	                           }])
	return value, errors


def create_withhold_from_file(self, values, document_type):
	for number in values:
		if check_document(self, number, 'account.withhold.electronic'):
			continue
		partner_id = search_partner(self, values[number]['vat'], values[number])
		values[number]['partner_id'] = partner_id
		values[number].pop('partner_name')
		values[number]['number'] = number
		line_ids = []
		for product in values[number]['d']:
			line_ids.append((0, 0, product))
		values[number]['line_id'] = line_ids
		values[number]['company_id'] = self.env['res.users'].browse(self._uid).company_id.id
		values[number]['state'] = 'loaded'
		withhold_id = self.env['account.withhold.electronic'].create(values[number])
		access_key = generate_access_key(self, withhold_id)
		withhold_id.write({'access_key': access_key, 'electronic_authorization': access_key})


def create_remission_from_file(self, values, document_type):
	for number in values:
		if check_document(self, number, 'account.remission.electronic'):
			continue
		partner_id = search_partner(self, values[number]['vat'], values[number])
		values[number]['partner_id'] = partner_id
		values[number].pop('partner_name')
		values[number]['number'] = number
		line_ids = []
		for product in values[number]['p']:
			line_ids.append((0, 0, product))
		values[number]['line_id'] = line_ids
		values[number]['company_id'] = self.env['res.users'].browse(self._uid).company_id.id
		values[number]['state'] = 'loaded'
		remission_id = self.env['remission.guide.electronic'].create(values[number])
		access_key = generate_access_key(self, remission_id)
		remission_id.write({'access_key': access_key, 'electronic_authorization': access_key})


def read_file_remission(datas, delimiter):
	""""
    Return data mapping for invoices, withhold and remission
    """
	value = {}
	errors = []
	i = 0
	for data in datas:
		i += 1
		document_data = data.split(delimiter)
		if document_data[0] == 'n':
			value[document_data[1]] = {}
			number = document_data[1]
			value['p'] = []
			error = check_format(plantilla_guia.n, document_data[:1], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
		elif document_data[0] == 'i':
			error = check_format(plantilla_guia.i, document_data[:1], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
			value[number]['vat'] = document_data[1].strip()
			value[number]['partner_name'] = document_data[2].strip()
			value[number]['street'] = document_data[3].strip()
			value[number]['motivo'] = document_data[4]
			value[number]['invoice'] = document_data[5]
			value[number]['invoice_emission_date'] = document_data[6]
			value[number]['email'] = document_data[6]
		elif document_data[0] == 't':
			error = check_format(plantilla_guia.t, document_data[:1], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
			value[number]['emission_date_start'] = document_data[1].strip()
			value[number]['emission_date_stop'] = document_data[2].strip()
			value[number]['ruc_carrier'] = document_data[3].strip()
			value[number]['social_name'] = document_data[5].strip()
			value[number]['start_street'] = document_data[6].strip
		elif document_data[0] == 'p':
			error = check_format(plantilla_guia.p, document_data[:1], i)
			if error:
				errors.append(error)
				value[number]['errors'] = True
				continue
			value['p'].append([{
                                'code': document_data[1],
                                'name': document_data[2],
                                'quantity': document_data[3],
                               }])
	return value, errors

