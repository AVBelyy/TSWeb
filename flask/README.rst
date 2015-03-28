============
TSWeb Client
============

Description
-----------

Web interface to TestSys written as Flask application, capable of running on
native WSGI server (mod_python or uwsgi, for example), or in any FastCGI server via
flup_.

.. _flup: http://www.saddi.com/software/flup/

Requirements
------------

* python 2 or 3 (3 is now preferred, 2 still works, but does not receive much testing)
* flask
* flask-babel (for internationalization)
* pygments (for code highlighting)
* beautifulsoup4
* chardet (for encoding detection in some of the TestSys responses)
* flup6 (for running in FastCGI mode)
* /dev/hands and /dev/brain ;)

All these packages can easily be installed with ``pip`` command.

Configuration
-------------

TSWeb is configured via ``flask/config.cfg`` file that is in INI syntax. You can configure TestSys address,
logging levels, email logs, etc. Documentation for config keys is coming :)

To get Russian translations, you need to run the following command::

    $ pybabel compile -d flask/tsweb/translations

Simple usage
------------

That's how you can test TSWeb w/o any web server::

    $ cd flask/
    $ python run.py

Now you have access to it via http://127.0.0.1:5000/.

Production usage
----------------

The best (and only tested) way to use TSWeb in production is with nginx web server, that is compatible both
Windows and with Linux. This is done through FastCGI interface and ``flup`` library.

First, modify ``flask/run_flup.py`` file to add path to ``tsweb`` package to python path if needed. Then run
the script. The FastCGI server will start to listen on ``127.0.0.1:3010``.

Now just point nginx to this server with ``fastcgi_pass`` directive and it should work.

Status of the project
---------------------

All features present in the original (perl) TSWweb are implemented:

* Submit
* Monitor
* Clarifications
* Feedbacks
* Submissions sources

Brand new features
------------------

This TSWeb has some improvements over original version:

* Modern look: Twitter Bootstrap (version 2) is used to create simple, but pleasant look
* i18n: the site is translated into Russian, with auto detection and possibility to set language
* Submit form remembers compiler and problem chosen last time, lowering the chances of mis-submit
* Monitor highlights solved problems and solutions that were first to get accepted
* Submission source is highlighted with Pygments
* Submission filter: you can filter submissions by result, task ID and team number
