
import socket, fcntl, logging, re, random, select
from flask import request

#FIXME: Use config engine
LOG_FILENAME = 'tsweb.log'
LOG_LEVEL = logging.DEBUG
TESTSYS_HOST = '127.0.0.1'
SEND_TIMEOUT = 10.0

_channels = {}

encode_regex = re.compile(r'([\x00-\x1f])')
decode_regex = re.compile(r'\x18([\x40-\x5f])')

def dle_encode(s):
    repl = lambda match: "\x18" + chr(0x40+ord(match.group(1)))
    return encode_regex.sub(repl, s)

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
    sockets = [chan for chan in args if chan.sock]
    r, w, e = select.select([] if write else sockets, sockets if write else [], sockets, timeout)
    return w if write else r
    #TODO: Some kind of error handling here


logging.basicConfig(filename=LOG_FILENAME, level=LOG_LEVEL)

class Channel():
    def __init__(self, name, port=0):
        if name in _channels and _channels[name].sock:
            return _channels[name]

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
            sock = socket.socket()
            try:
                sock.connect((TESTSYS_HOST, self.port))
            except socket.error as e:
                logging.error("Connection failed, {0} {1}".format(*e))
            self.set_block(nb)

    def close(self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                self.sock = None
            except socket.error as e:
                logging.error("Error while closing socket, {0} {1}".format(*e))

    def set_block(self, nb):
        #TODO: Implement this
        pass

    def send(self, msg):
        req = makereq(msg)
        logging.debug("Socket: {0.sock}, port={0.port}".format(self))
        logging.debug("Request: {0}".format(req))

        tot = 0
        while req:
            res = self.sock.send(req, 0)
            tot = res if res < 0 else tot + res
            sockets = select_channels(SEND_TIMEOUT, self.sock)
            if (not sockets) or (res <= 0 or res == len(req)):
                break
            req = req[res:]

        if tot < 0:
            raise Exception("send() returned {0}".format(tot))

_channels = {
    'CONSOLE': Channel('CONSOLE', 17240),
    'SUBMIT': Channel('SUBMIT', 17241),
    'MSG': Channel('MSG', 17242),
    'MONITOR': Channel('MONITOR', 17243),
    'PRINTSOL': Channel('PRINTSOL', 17244)
}

def valid_teamname(name):
    return True
