
# -*- coding: utf-8 -*-

import os, logging
from ConfigParser import ConfigParser

config_dir = os.path.abspath(os.path.dirname(__file__))
config_file = os.path.join(config_dir, 'config.cfg')

config = ConfigParser()
config.read(config_file)

SECRET_KEY = config.get('General', 'secret_key')
DEBUG = config.getboolean('General', 'debug')
PRINTSOL = config.get('General', 'printsol')
CONTLIST_MASK = config.get('General', 'contlist_mask')

TESTSYS_HOST = config.get('Testsys', 'host')
TIMEOUT = config.getfloat('Testsys', 'timeout')
SEND_TIMEOUT = config.getfloat('Testsys', 'send_timeout')

LOG_TO_EMAIL = config.getboolean('Logging', 'email')
LOG_EMAILS = config.get('Logging', 'emails').split(',')
LOG_FILENAME = config.get('Logging', 'logfile')
LOG_LEVEL = {'debug': logging.DEBUG, 'error': logging.ERROR, 'warning': logging.WARNING}[config.get('Logging', 'loglevel')]
SMTP_SERVER = config.get('Logging', 'smtp_server')
SMTP_PORT = config.get('Logging', 'smtp_port')
EMAIL_FROM = config.get('Logging', 'email_from')
EMAIL_PASSWORD = config.get('Logging', 'email_password')

LANGUAGES = {
    'en': 'English',
    'ru': u'Русский',
}
