============
TSWeb Client
============

Description
-----------
Web interface to TestSys written as Flask application, capable of running on
native WSGI server (mod_python, for example), or in any FastCGI server via
flup_: 

.. _flup: http://www.saddi.com/software/flup/

Requirements
------------

* Python
* Flask
* /dev/hands and /dev/brain ;)

Simple usage
------------
That's how you can test TSWeb w/o any web server::
 $ cd flask/

 $ python tsweb/main.py

Now you have access to it via http://127.0.0.1:5000/

Already implemented features
----------------------------
* Logging users in and out and storing their sessions server-side
* TestSys protocol implementation working at least with main page

Future plans
------------
* Implementaion of monitor, sumbit and other modules
* Final restruction of code and getting rid of perl-style page processing
