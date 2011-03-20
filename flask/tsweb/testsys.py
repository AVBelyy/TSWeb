
import socket, fcntl, logging, re, random, select, errno
from flask import request

#FIXME: Use config engine
LOG_FILENAME = 'tsweb.log'
LOG_LEVEL = logging.DEBUG
TESTSYS_HOST = '127.0.0.1'
SEND_TIMEOUT = 10.0
TIMEOUT = 10.0

_channels = {}

encode_regex = re.compile(r'([\x00-\x1f])')
decode_regex = re.compile(r'\x18([\x40-\x5f])')

class ConnectionFailedException(Exception):
    pass

def dle_encode(s):
    repl = lambda match: "\x18" + chr(0x40+ord(match.group(1)))
    return encode_regex.sub(repl, str(s))

def dle_decode(s):
    repl = lambda match: chr(ord(match.group(1))-0x40)
    return decode_regex.sub(repl, s)

def client_triplet():
    ip = request.environ.get('REMOTE_ADDR', '')
    fip = request.environ.get('HTTP_X_FORWARDED_FOR', '')
    client = 'tsweb,' + ip if ip else 'tsweb-text'
    if fip:
        client += '<-' + fip

    return client, ip, fip

def makereq(p):
    client, ip, fip = client_triplet()

    l = ['', '---']
    p['ID'] = p.get('ID', '%.9d' % random.randint(0, 1000000000))
    p['Client'] = client
    if ip:
        p['Origin'] = fip if fip else ip

    for key in sorted(p):
        l.append("{0}={1}".format(key, dle_encode(p[key])))

    l+= ['+++', '']

    return '\0'.join(l)

def select_channels(timeout, write=False, *args):
    sockets = [chan.sock for chan in args if chan.sock]
    logging.debug("Selecting sockets for {0}: {1}".format("reading" if not write else "writing", sockets))
    r, w, e = select.select([] if write else sockets, sockets if write else [], sockets, timeout)
    return w if write else r
    #TODO: Some kind of error handling here

logging.basicConfig(filename=LOG_FILENAME, level=LOG_LEVEL)

def get_channel(name):
    if name in _channels and _channels[name].sock:
        return _channels[name]
    return Channel(name)

class Channel():
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
        self.debug = False #FIXME: Use config engine
        self.noblock = True
        self.flags = None

        _channels[name] = self

    def open(self, nb):
        if not self.sock:
            logging.debug('Connecting to {0}:{1}'.format(TESTSYS_HOST, self.port))
            self.sock = socket.socket()
            try:
                self.sock.connect((TESTSYS_HOST, self.port))
            except socket.error as e:
                logging.error("Connection failed, {0} {1}".format(*e))
                raise ConnectionFailedException()
            self.sock.setblocking(not nb)

    def close(self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                self.sock = None
            except socket.error as e:
                logging.error("Error while closing socket, {0} {1}".format(*e))

    def send(self, msg):
        req = makereq(msg)
        logging.debug("Socket: {0.sock}, port={0.port}".format(self))
        logging.debug("Request: {0}".format(req))

        tot = 0
        while req:
            res = self.sock.send(req, 0)
            tot = res if res < 0 else tot + res
            sockets = select_channels(SEND_TIMEOUT, True, self)
            if (not sockets) or (res <= 0 or res == len(req)):
                break
            req = req[res:]

        if tot < 0:
            raise Exception("send() returned {0}".format(tot))

    def _recv(self):
        try:
            buff = self.sock.recv(655360)
        except IOError as e:
            if e.errno == errno.EAGAIN:
                logging.debug("Non-blocking operation on not ready socket")
                return
            else:
                raise e

        logging.debug("(read {0} bytes)".format(len(buff)))
        logging.info("(BUFF: |{0}|)".format(buff))

        if self.partial:
            buff = self.partial + buf
            self.partial = None

        L = buff.split('\0')
        E = []
        on = 0
        for e in L:
            logging.debug("Got: {0}".format(e))
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
        if not self.queue:
            return None
        else:
            return self.queue.pop(0)

    def recv(self, f=False):
        R = self._read()
        while not R:
            sockets = select_channels(TIMEOUT, False, self)
            if not sockets:
                logging.debug('Timeout reached while receiveing from {0.sock} port {0.port}'.format(self))
                break

            self._recv()

            if self.partial:
                logging.debug("Partially recieved {0} bytes".format(len(self.partial)))

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
    return True
