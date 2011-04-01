"""This is TestSys Web Client implemented as Flask WSGI application.
To use it, add direcotory with 'tsweb' subdir to sys.path and import 'tswebapp'
from 'tsweb' package."""

from tsweb.main import tswebapp
__all__ = ['tswebapp']
