
import os, logging
from ConfigParser import ConfigParser

config_dir = os.path.abspath(os.path.dirname(__file__))
config_file = os.path.join(config_dir, 'config.cfg')

config = ConfigParser()
config.read(config_file)

DEBUG = config.getboolean('General', 'debug')
LOG_FILENAME = config.get('General', 'logfile')
LOG_LEVEL = {'debug': logging.DEBUG, 'error': logging.ERROR, 'warning': logging.WARNING}[config.get('General', 'loglevel')]
PRINTSOL = config.get('General', 'printsol')
CONTLIST_MASK = config.get('General', 'contlist_mask')

TESTSYS_HOST = config.get('Testsys', 'host')
TIMEOUT = config.getfloat('Testsys', 'timeout')
SEND_TIMEOUT = config.getfloat('Testsys', 'send_timeout')
