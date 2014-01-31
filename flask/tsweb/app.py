"""Logging setup for testsys"""

import logging, logging.handlers
from flask import Flask, session
from flask.ext.babel import Babel

from . import config

tswebapp = Flask(__name__)
tswebapp.config.from_object(config)
tswebapp.logger.setLevel(tswebapp.config['LOG_LEVEL'])
fileFormatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
fileHandler = logging.handlers.RotatingFileHandler(
    tswebapp.config['LOG_FILENAME'], maxBytes=2**20, backupCount=5)
fileHandler.setFormatter(fileFormatter)
tswebapp.logger.addHandler(fileHandler)

babel = Babel(tswebapp)

class TswebFormatter(logging.Formatter):
    """Special formatter that adds team and contest id to LogRecord"""

    def format(self, record):
        try:
            record.team = session.get('team', '??')
            record.contestid = session.get('contestid', '??')
        except:
            # Suppress potential erorrs from Flask or others
            record.team = '??'
            record.contestid = '??'

        return super(TswebFormatter, self).format(record)

if tswebapp.config['LOG_TO_EMAIL']:
    smtpFormatter = TswebFormatter('''
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s
    Team:               %(team)s
    Contest ID:         %(contestid)s

    Message:

    %(message)s
    ''')
    smtpHandler = logging.handlers.SMTPHandler((tswebapp.config['SMTP_SERVER'], tswebapp.config['SMTP_PORT']),
                                                tswebapp.config['EMAIL_FROM'],
                                                tswebapp.config['LOG_EMAILS'],
                                                'TSWeb log',
                                                (tswebapp.config['EMAIL_FROM'], tswebapp.config['EMAIL_PASSWORD']),
                                                tuple())
    smtpHandler.setFormatter(smtpFormatter)
    tswebapp.logger.addHandler(smtpHandler)
