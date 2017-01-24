import os


path = os.getcwd()
if not os.path.exists('/etc/init.d/signature_electronic_sri'):
    os.chdir('../../../facturacion/facturacion/core_electronic_authorization/data')
    if not os.path.exists('/usr/local/signature'):
        os.popen('chmod 777 /usr/local/')
        os.popen('mkdir /usr/local/signature && chmod 777 /usr/local/signature')
    os.popen('cp signature_electronic_sri.jar /usr/local/signature')
    os.popen('cp signature_electronic_sri /etc/init.d/')
    os.popen('update-rc.d signature_electronic_sri defaults')
    os.popen('service signature_electronic_sri start')
    os.chdir(path)