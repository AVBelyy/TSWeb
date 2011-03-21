
import re
import testsys
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug import secure_filename

tswebapp = Flask('tsweb')
tswebapp.secret_key = '123asd'

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

@tswebapp.route('/')
@tswebapp.route('/index')
def index():
    if 'team' in session:
        return format_main_page()
    else:
        return render_template("index.html")
#    else:
#        if request.form['op'] == 'changecontest':
#            session['contestid'] = request.form['newcontestid']
#            session['cookie_state'] = 2
#            return render_template("redirect.html", text="Your contest has been changed to {0}, {1}".format(session['contestid'], request.form['team']))

@tswebapp.route('/logout')
def logout():
    tm = ', {0}'.format(session['team']) if 'team' in session else ''
    session.pop('team', None)
    return redirector(url_for('index'), text="Thanks for logging out{0}!".format(tm))

@tswebapp.route('/login', methods=['POST'])
def login():
    if not testsys.valid_teamname(request.form['team']):
        return render_template("error.html", text="Invalid team name")

    if not request.form['password']:
        return render_template("error.html", text="Non-empty password expected")

    MSG = testsys.Channel('MSG')
    try:
        MSG.open(1)
    except testsys.ConnectionFailedException:
        return render_template("error.html", text="Cannot connect to TESTSYS")

    try:
        MSG.send({
            'Team': request.form['team'],
            'Password': request.form['password'],
            'ContestId': request.form.get('contestid', ''),
            'AllMessages': 'Yes',
            'DisableUnrequested': 1})

        ans = MSG.recv()
        if 'Error' in ans:
            return render_template("error.html", text="Error logging in: {0}".format(ans['Error']))

        session['team'] = request.form['team']
        session['password'] = request.form['password']
        session['contestid'] = ans.get('ContestId', '')
        session['team_name'] = ans.get('TeamName', '').decode('cp866')

        return redirector(url_for('index'), text="Thank you for logging in, {0}!".format(session['team']))
    finally:
        MSG.close()

def format_main_page():
    MSG = testsys.Channel('MSG')
    try:
        MSG.open(1)
    except testsys.ConnectionFailedException:
        return render_template("main.html", error="Cannot connect to TESTSYS")

    MSG.send({
        'Team': session['team'],
        'Password': session['password'],
        'ContestId': session.get('contestid', ''),
        'AllMessages': 'Yes',
        'DisableUnrequested': 1})

    ans = MSG.recv()
    config = {}
    if not ans:
        config['error'] = 'Cannot connect to TESTSYS'
    elif ans.get('Error', ''):
        config['error'] = 'Testsys response: {0}'.format(ans['Error'])
    else:
        config['wtc'] = int(ans.get('WaitingCount', 0))
        config['jury'] = True if ans.get('JuryMode', False) else False
        config['statements'] = ans.get('StatementsLink', '')
        config['contlist_mask'] = 1 #FIXME: Get this from config file
        config['messages'] = re.split('\r?\n', ans.get('AllMessages', ''))
        config['version'] = ans.get('Version', 0)
        config['contid'] = ans.get('ContestId', '')
        config['contname'] = ans.get('ContestName', '').decode('cp866')
        config['contest_start'] = ans.get('ContestStart', '00:00:00')
        config['contest_duration'] = ans.get('ContestDuration', '00:00:00')
        config['server_now'] = ans.get('ServerNow', '00:00:00')
        session['team_name'] = ans.get('TeamName', session['team']).decode('cp866')

    return render_template("main.html", **config)

def get_compilers(SUBM):
    SUBM.send({
        'Team': session['team'],
        'Password': session['password'],
        'ContestId': session['contestid'],
        'Request': 'ContestData'})

    ans = SUBM.recv()
    if 'Error' in ans:
        raise testsys.CommunicationException(ans['Error'])

    pmode = 0
    compilers, problems, extensions = [], {}, {}
    data = ans['Data'].decode('cp866')
    for line in re.split('\r?\n', data):
        match = re.match('VERSION=(.*)', line)
        if match:
            ver = match.group(1)
        elif line == '':
            pmode = 2
        elif line == 'COMPILERS:':
            pmode = 1
        elif not pmode:
            contest_name = line
        elif pmode == 1 and re.match(r'^\.([a-z]+):(.*)', line):
            match = re.match(r'^\.([a-z]+):(.*)', line)
            extensions[match.group(1)] = match.group(2)
            compilers.append([match.group(1), match.group(2)])
        elif pmode == 2 and re.match(r'^([A-Za-z0-9_\-]+)=(.*)', line):
            match = re.match(r'^([A-Za-z0-9_\-]+)=(.*)', line)
            problems[match.group(1)] = match.group(2)
        else:
            raise testsys.CommunicationException("Unknown line '{0}' in ContestData response".format(line))

    if not problems:
        raise testsys.CommunicationException("No problems defined")
    if not compilers:
        raise testsys.CommunicationException("No compilers defined")

    return problems, compilers

@tswebapp.route('/submit', methods=['GET', 'POST'])
def sumbit():
    if not 'team' in session:
        return login_error()

    SUBM = testsys.get_channel('SUBMIT')
    try:
        SUBM.open(1)
    except testsys.ConnectionFailedException:
        return error("Cannot connect to TESTSYS")

    try:
        try:
            problems, compilers = get_compilers(SUBM)
        except testsys.CommunicationException as e:
            return render_template("error.html", text=e.message)

        if request.method == 'GET':
            config = {}
            config['problems'] = problems
            config['compilers'] = compilers
            return render_template("submit.html", **config)
        elif request.method == 'POST':
            if request.files['file']:
                data = request.files['file'].read().encode('cp866')
                filepath = secure_filename(request.files['file'].filename)
                filename = ''.join(filepath.split('.')[:-1])
            if request.form['solution']:
                data = request.form['solution']
                filepath = request.form['prob'] + '.' + request.form['lang']
                filename = request.form['prob']

            if not data:
                return error("No solution presented")
            if not filepath.split('.')[-1] in extensions:
                return error("Invalid file type")
            if not request.form['prob'] in problems:
                return error("Unknown problem '{0}'".format(request.form['prob']))
            if not request.form['lang'] in extensions:
                return error("Unknown compiler '{0}'".format(request.form['lang']))

            #FIXME: Add timeout from config
            timeout = len(data) / 16384
            if timeout > 4:
                timeout = 4

            id = SUBM.send({
                'Team': session['team'],
                'Password': session['password'],
                'ContestId': session['contestid'],
                'Problem': request.form['prob'],
                'Contents': data,
                'Source': filename,
                'Compiler': extensions[request.form['lang']],
                'Extension': request.form['lang']}, timeout)

            ans = SUBM.recv()
            outp = 0
            while ans:
                if ans['ID'] == id:
                    if 'Error' in ans:
                        return testsys_error(ans['Error'], title="Submit error")
                    else:
                        outp = 1
                        break
            return render_template("submit_status.html", error=outp)
    finally:
        SUBM.close()

if __name__ == "__main__":
    tswebapp.debug = True
    tswebapp.run()
