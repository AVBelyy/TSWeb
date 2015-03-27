from flup.server.fcgi import WSGIServer

# Add tsweb to sys.path if needed
# Example:
#import sys
#sys.path.append('C:/nginx/tsweb/flask/')

from tsweb import tswebapp

if __name__ == '__main__':
        print('************************')
        print('  TSWEB PYTHON SERVER   ')
        print('DO NOT STOP THIS PROGRAM')
        print('************************')
        WSGIServer(tswebapp, bindAddress=('127.0.0.1', 3010)).run()
