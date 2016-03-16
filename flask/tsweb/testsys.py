"""This module implements binary TestSys protocol"""

import socket, re, random, select, errno
from flask import request
from chardet import detect
from flask.ext.babel import gettext
from .app import tswebapp
from .compat import unicode

from traceback import format_stack

teamname_regex = re.compile(r'^[A-Za-z\-\_0-9]{1,8}$')

encode_regex = re.compile(r'([\x00-\x1f])'.encode('ascii'))
decode_regex = re.compile(r'\x18([\x40-\x5f])'.encode('ascii'))

class CommunicationException(Exception):
    """This exception is raised when error occurs on opened socket"""
    pass

    def __str__(self):
        if not self.args:
            return gettext("Error while communicating with TestSys")
        else:
            return super(CommunicationException, self).__str__()

class ConnectionFailedException(Exception):
    """This exception is raised when error occurs while opening socket"""
    pass

    def __str__(self):
        if not self.args:
            return gettext("Can not connect to TestSys")
        else:
            return super(ConnectionFailedException, self).__str__()

def dle_encode(string, encoding):
    """Encode *string* to TestSys binary protocol"""

    if not isinstance(string, (str, bytes, unicode)):
        string = str(string)

    string = string.encode(encoding)

    repl = lambda match: b'\x18' + chr(0x40+ord(match.group(1))).encode('ascii')
    return encode_regex.sub(repl, string)

def dle_decode(string, encoding):
    """Decode *string* from TestSys binary protocol"""

    def fallback(res):
        try:
            enc = detect(res)['encoding']
            return res.decode(enc)
        except (UnicodeDecodeError, KeyError):
            # If everything fails, return escaped string...
            return repr(res).strip("b'")

    repl = lambda match: chr(ord(match.group(1))-0x40).encode('ascii')

    res = decode_regex.sub(repl, string)

    if isinstance(encoding, tuple):
        for enc in encoding:
            try:
                return res.decode(enc)
            except UnicodeDecodeError:
                continue
        return fallback(res)
    elif encoding == 'detect':
        return fallback(res)
    else:
        try:
            return res.decode(encoding)
        except UnicodeDecodeError:
            return fallback(res)

    return decode_regex.sub(repl, string).decode(encoding)

def client_triplet():
    """Return tuple (client_string, client_ip, origin_ip)"""
    ip = request.environ.get('REMOTE_ADDR', '')
    fip = request.environ.get('HTTP_X_FORWARDED_FOR', '')
    client = 'tsweb,' + ip if ip else 'tsweb-text'
    if fip:
        client += '<-' + fip

    return client, ip, fip

def makereq(req, encoding='cp866'):
    """Convert dictionary *request* to TestSys binary protocol string"""
    client, ip, fip = client_triplet()

    result = [b'', b'---']
    req['ID'] = req.get('ID', '%.9d' % random.randint(0, 1000000000))
    req['Client'] = client
    if ip:
        req['Origin'] = fip if fip else ip

    for key in sorted(req):
        result.append(key.encode(encoding) + b'=' + dle_encode(req[key], encoding))

    result += [b'+++', b'']

    return b'\0'.join(result)

def select_channels(timeout, write=False, *args):
    """Run select() on sockets from *args*, which is list of :py:class:`Channel`"""
    sockets = [chan.sock for chan in args if chan.sock]
    tswebapp.logger.debug(
        "Selecting sockets for {0}: {1}".format(
            "reading" if not write else "writing", sockets))
    re, wr, exc = select.select(
        [] if write else sockets, sockets if write else [], sockets, timeout)
    return wr if write else re

class Channel():
    """Class, representing socket to TestSys"""
    def __init__(self, name, port=0):
        if not port:
            port = ports.get(name, 0)

        if not port:
            raise ValueError('Unknown port for channel {}'.format(name))

        self.name = name
        self.port = port
        self.sock = None
        self.queue = []
        self.type = 'Channel'
        self.partial = None
        self.noblock = True
        self.flags = None

    def open(self, nb):
        """Open channel. *nb* specifies non-blocking mode fore socket"""
        if not self.sock:
            tswebapp.logger.debug(
                "Connecting to {0}:{1}".format(
                    tswebapp.config['TESTSYS_HOST'], self.port))
            self.sock = socket.socket()
            self.sock.settimeout(tswebapp.config['TIMEOUT'])
            try:
                self.sock.connect(
                    (tswebapp.config['TESTSYS_HOST'], self.port))
            except socket.timeout:
                tswebapp.logger.error("Connection failed: time-out")
                self.close()
                raise ConnectionFailedException()
            except socket.error as e:
                tswebapp.logger.error(
                    "Connection failed, {0}".format(e))
                self.close()
                raise ConnectionFailedException()
            self.sock.setblocking(not nb)

    def close(self):
        """Close a channel"""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except socket.error as e:
                tswebapp.logger.error(
                    "Error while closing socket, {0}".format(e))
            finally:
                self.sock = None

    def send(self, msg, timeout=0, encoding='cp866'):
        """Send message *msg* to socket. *msg* must be dict"""
        if not timeout:
            timeout = tswebapp.config['TIMEOUT']
        req = makereq(msg)
        tswebapp.logger.debug(
            "Socket: {0.sock}, port={0.port}".format(self))
        tswebapp.logger.debug("Request: {0}".format(repr(req)))

        tot = 0
        while req:
            try:
                res = self.sock.send(req, 0)
            except IOError as e:
                tswebapp.logger.error(
                    "Error sending data to socket, {0}, {1}.\n{2} \n{3}".format(
                        errno.errorcode.get(e.errno, ''), e.strerror, e, ''.join(format_stack()))
                )
                self.close()
                raise CommunicationException(
                    "Error on socket, may be TestSys is down?")
            tot = res if res < 0 else tot + res
            sockets = select_channels(timeout, True, self)
            if (not sockets) or (res <= 0 or res == len(req)):
                break
            req = req[res:]

        if tot < 0:
            raise CommunicationException("send() returned {0}".format(tot))

        return msg['ID']

    def _recv(self, encoding):
        """Internal function for recieving parts from socket"""
        try:
            buff = self.sock.recv(655360)
        except IOError as e:
            # 10035 is WSAEWOULDBLOCK, Windows EAGAIN variant
            if e.errno in (errno.EAGAIN, 10035):
                tswebapp.logger.debug(
                    "Non-blocking operation on not ready socket")
                return
            else:
                self.close()
                raise e

        tswebapp.logger.debug("(read {0} bytes)".format(len(buff)))
        tswebapp.logger.debug("(BUFF: |{0}|)".format(buff))

        if self.partial:
            buff = self.partial + buff
            self.partial = None

        L = buff.split(b'\0')
        E = []
        on = 0
        for e in L:
            tswebapp.logger.debug("Got: {0}".format(e))
            if on:
                E.append(e)
            if e == b'---':
                on = 1
                R = {}
                E = [b'---']
            elif e == b'+++':
                if on: self.queue.append(R)
                on = 0
                R = {}
                E = []
            elif on:
                match = re.match(r'^([A-Za-z_0-9]+)=(.*)$'.encode('ascii'), e)
                if match:
                    R[match.group(1).decode('ascii')] = dle_decode(match.group(2), encoding)

        if on:
            self.partial = b'\0'.join(E)

        return len(buff)

    def _read(self):
        """Internal function for getting next waiting message in queue"""
        if not self.queue:
            return None
        else:
            return self.queue.pop(0)

    def recv(self, f=False, encoding='cp866'):
        """Recieve message from socket"""
        R = self._read()
        while not R:
            sockets = select_channels(
                tswebapp.config['TIMEOUT'], False, self)
            if not sockets:
                tswebapp.logger.debug("Timeout reached while receiveing \
from {0.sock} port {0.port}".format(self))
                self.close()
                break

            if not self._recv(encoding):
                break

            if self.partial:
                tswebapp.logger.debug(
                    "Partially recieved {0} bytes".format(len(self.partial)))

            if f and self.partial == '':
                break

            R = self._read()

        if not R:
            R = self._read()

        return R

ports = {
    'CONSOLE': 17240,
    'SUBMIT': 17241,
    'MSG': 17242,
    'MONITOR': 17243,
    'PRINTSOL': 17244
}

def valid_teamname(name):
    """Check team name *name* for validity"""
    return teamname_regex.match(name) is not None
