"""This module implements binary TestSys protocol"""

import socket, logging, re, random, select, errno
from flask import request
import main

_channels = {}

teamname_regex = re.compile(r'^[A-Za-z\-\_0-9]{1,8}$')

encode_regex = re.compile(r'([\x00-\x1f])')
decode_regex = re.compile(r'\x18([\x40-\x5f])')

class CommunicationException(Exception):
    """This exception is raised when error occurs on opened socket"""
    pass

class ConnectionFailedException(Exception):
    """This exception is raised when error occurs while opening socket"""
    pass

def dle_encode(string):
    """Encode *string* to TestSys binary protocol"""
    if not isinstance(string, basestring):
        string = str(string)
    if isinstance(string, unicode):
        string = string.encode('cp866')
    repl = lambda match: "\x18" + chr(0x40+ord(match.group(1)))
    return encode_regex.sub(repl, string)

def dle_decode(string):
    """Decode *string* from TestSys binary protocol"""
    repl = lambda match: chr(ord(match.group(1))-0x40)
    return decode_regex.sub(repl, string)

def client_triplet():
    """Return tuple (client_string, client_ip, origin_ip)"""
    ip = request.environ.get('REMOTE_ADDR', '')
    fip = request.environ.get('HTTP_X_FORWARDED_FOR', '')
    client = 'tsweb,' + ip if ip else 'tsweb-text'
    if fip:
        client += '<-' + fip

    return client, ip, fip

def makereq(req):
    """Convert dictionary *request* to TestSys binary protocol string"""
    client, ip, fip = client_triplet()

    result = ['', '---']
    req['ID'] = req.get('ID', '%.9d' % random.randint(0, 1000000000))
    req['Client'] = client
    if ip:
        req['Origin'] = fip if fip else ip

    for key in sorted(req):
        result.append("{0}={1}".format(key, dle_encode(req[key])))

    result += ['+++', '']

    return '\0'.join(result)

def select_channels(timeout, write=False, *args):
    """Run select() on sockets from *args*, which is list of :py:class:`Channel`"""
    sockets = [chan.sock for chan in args if chan.sock]
    main.tswebapp.logger.debug(
        "Selecting sockets for {0}: {1}".format(
            "reading" if not write else "writing", sockets))
    re, wr, exc = select.select(
        [] if write else sockets, sockets if write else [], sockets, timeout)
    return wr if write else re

def get_channel(name):
    """Create new channel with *name*, or return existing one"""
    if name in _channels and _channels[name].sock:
        return _channels[name]
    return Channel(name)

class Channel():
    """Class, representing socket to TestSys"""
    def __init__(self, name, port=0):
        if name in _channels and _channels[name].port:
            port = _channels[name].port
        else:
            port = port

        if not port:
            raise ValueError('Creating new channel without port')

        self.name = name
        self.port = port
        self.sock = None
        self.queue = []
        self.type = 'Channel'
        self.partial = None
        self.noblock = True
        self.flags = None

        _channels[name] = self

    def open(self, nb):
        """Open channel. *nb* specifies non-blocking mode fore socket"""
        if not self.sock:
            main.tswebapp.logger.debug(
                "Connecting to {0}:{1}".format(
                    main.tswebapp.config['TESTSYS_HOST'], self.port))
            self.sock = socket.socket()
            self.sock.settimeout(main.tswebapp.config['TIMEOUT'])
            try:
                self.sock.connect(
                    (main.tswebapp.config['TESTSYS_HOST'], self.port))
            except socket.timeout:
                main.tswebapp.logger.error("Connection failed: time-out")
                raise ConnectionFailedException()
            except socket.error as e:
                main.tswebapp.logger.error(
                    "Connection failed, {0} {1}".format(*e))
                raise ConnectionFailedException()
            self.sock.setblocking(not nb)

    def close(self):
        """Close a channel"""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                self.sock = None
            except socket.error as e:
                main.tswebapp.logger.error(
                    "Error while closing socket, {0} {1}".format(*e))

    def send(self, msg, timeout=0):
        """Send message *msg* to socket. *msg* must be dict"""
        if not timeout:
            timeout = main.tswebapp.config['TIMEOUT']
        req = makereq(msg)
        main.tswebapp.logger.debug(
            "Socket: {0.sock}, port={0.port}".format(self))
        main.tswebapp.logger.debug("Request: {0}".format(req))

        tot = 0
        while req:
            try:
                res = self.sock.send(req, 0)
            except IOError as e:
                main.tswebapp.logger.error(
                    "Error sending data to socket, {0}, {1}".format(
                        errno.errorcode.get(e.errno, ''), e.strerror))
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

    def _recv(self):
        """Internal function for recieving parts from socket"""
        try:
            buff = self.sock.recv(655360)
        except IOError as e:
            if e.errno == errno.EAGAIN:
                main.tswebapp.logger.debug(
                    "Non-blocking operation on not ready socket")
                return
            else:
                raise e

        main.tswebapp.logger.debug("(read {0} bytes)".format(len(buff)))
        main.tswebapp.logger.info("(BUFF: |{0}|)".format(buff))

        if self.partial:
            buff = self.partial + buff
            self.partial = None

        L = buff.split('\0')
        E = []
        on = 0
        for e in L:
            main.tswebapp.logger.debug("Got: {0}".format(e))
            if on:
                E.append(e)
            if e == '---':
                on = 1
                R = {}
                E = ['---']
            elif e == '+++':
                if on: self.queue.append(R)
                on = 0
                R = {}
                E = []
            elif on:
                match = re.match(r'^([A-Za-z_0-9]+)=(.*)$', e)
                if match:
                    R[match.group(1)] = dle_decode(match.group(2))

        if on:
            self.partial = '\0'.join(E)

        return len(buff)

    def _read(self):
        """Internal function for getting next waiting message in queue"""
        if not self.queue:
            return None
        else:
            return self.queue.pop(0)

    def recv(self, f=False):
        """Recieve message from socket"""
        R = self._read()
        while not R:
            sockets = select_channels(
                main.tswebapp.config['TIMEOUT'], False, self)
            if not sockets:
                main.tswebapp.logger.debug("Timeout reached while receiveing \
from {0.sock} port {0.port}".format(self))
                break

            if not self._recv():
                break

            if self.partial:
                main.tswebapp.logger.debug(
                    "Partially recieved {0} bytes".format(len(self.partial)))

            if f and self.partial == '':
                break

            R = self._read()

        if not R:
            R = self._read()

        return R

_channels = {
    'CONSOLE': Channel('CONSOLE', 17240),
    'SUBMIT': Channel('SUBMIT', 17241),
    'MSG': Channel('MSG', 17242),
    'MONITOR': Channel('MONITOR', 17243),
    'PRINTSOL': Channel('PRINTSOL', 17244)
}

def valid_teamname(name):
    """Check team name *name* for validity"""
    return teamname_regex.match(name) is not None
