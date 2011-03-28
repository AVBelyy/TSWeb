
from flask import redirect, render_template
from pygments.lexers import guess_lexer
from pygments.formatters import HtmlFormatter
from pygments import highlight as p_highlight

from tsweb import testsys

def redirector(url, **kwargs):
    res = redirect(url)
    res.response = [render_template("redirect.html", **kwargs)]

    return res

def login_error():
    return render_template("error.html", text="Login error: session data missing or expired", title="Authentification Error")

def error(msg):
    return render_template("error.html", text=msg)

def testsys_error(msg):
    return render_template("error.html", text="TestSys reports following error: {0}".format(msg) if msg else "TestSys reports unknown error", title="TestSys error")

def communicate(chan, request=None, check_empty=True):
    if isinstance(chan, testsys.Channel):
        channel = chan
    else:
        channel = testsys.get_channel(chan)
        try:
            channel.open(1)
        except testsys.ConnectionFailedException as e:
            return ('error', error(e.message))

    if request:
        try:
            id = channel.send(request)
        except testsys.CommunicationException as e:
            return ('error', error(e.message))
    else:
        id = 0
 
    answer = channel.recv()
    if not answer and check_empty:
        return ('error', error("Empty response from testsys"))
    if 'Error' in answer:
        return ('error', testsys_error(answer['Error']))
 
    return ('ok', (answer, id))

def highlight(text):
    lexer = guess_lexer(text)
    return p_highlight(text, lexer, HtmlFormatter(full=True, style='manni'))
