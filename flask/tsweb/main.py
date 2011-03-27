
import re, logging, logging.handlers
import testsys, config, monitor
from tsweb import decorators, util
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug import secure_filename

tswebapp = Flask(__name__)
tswebapp.secret_key = '123asd'
tswebapp.config.from_object(config)
tswebapp.logger.setLevel(tswebapp.config['LOG_LEVEL'])
tswebapp.logger.addHandler(logging.handlers.RotatingFileHandler(
              tswebapp.config['LOG_FILENAME'], maxBytes=2**20, backupCount=5))



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
    return util.redirector(url_for('index'), text="Thanks for logging out{0}!".format(tm))

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

        return util.redirector(url_for('index'), text="Thank you for logging in, {0}!".format(session['team']))
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
        config['contlist_mask'] = tswebapp.config['CONTLIST_MASK']
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

    return problems, compilers, extensions

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
            problems, compilers, extensions = get_compilers(SUBM)
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

            timeout = len(data) / 16384
            if timeout > 4:
                timeout = 4

            timeout = (timeout+2)*tswebapp.config['TIMEOUT']

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
                        return util.testsys_error(ans['Error'])
                    else:
                        outp = 1
                        break
                ans = SUBM.recv()
            return render_template("submit_status.html", error=not outp)
    finally:
        SUBM.close()

@tswebapp.route('/monitor')
def monitor_page():
    if not 'team' in session:
        return login_error()

    MON = testsys.get_channel('MONITOR')
    try:
        MON.open(1)
    except testsys.ConnectionFailedException:
        return error("Cannot connect to testsys")

    try:
        id = MON.send({
            'Team': session['team'],
            'Password': session['password'],
            'ContestId': session['contestid']})
        ans = MON.recv()
    except testsys.CommunicationException as e:
        return error(e.message)
    finally:
        MON.close()

    if 'Error' in ans:
        return error(ans['Error'])
    else:
        config = monitor.gen_monitor(ans['History'], ans['Monitor'])
        return render_template("monitor.html", **config)

@tswebapp.route('/allsubmits')
@decorators.login_required
@decorators.channel_user('MSG')
def submits(channel):
    state, answer = util.communicate(channel, {
        'Team': session['team'],
        'Password': session['password'],
        'ContestId': session['contestid'],
        'DisableUnrequested': '1',
        'AllSubm': request.args.get('all', 0),
        'Command': 'AllSubmits'})

    if state == 'error':
        return answer

    answer, id = answer

    submissions = []
    feed, score, team, tl, ml = False, False, False, False, False
    for i in xrange(1, int(answer['Submits'])):
        res = {
            'Problem': answer.get('SubmProb_'+str(i), ''),
            'ID': answer.get('SubmID_'+str(i), ''),
            'Time': answer.get('SubmTime_'+str(i), ''),
            'Result': answer.get('SubmRes_'+str(i), ''),
            'Test': answer.get('SubmTest_'+str(i), ''),
            'CE': answer.get('SubmCE_'+str(i), '').decode('cp866'),
            'Attempt': answer.get('SubmAtt_'+str(i), ''),
            'Feedback': answer.get('SubmFeed_'+str(i), ''),
            'Compiler': answer.get('SubmCompiler_'+str(i), ''),
            'TokenUsed': answer.get('SubmTokenUsed_'+str(i), ''),
            'Score': answer.get('SubmScore_'+str(i), ''),
            'Team': answer.get('SubmTeam_'+str(i), '').decode('cp866'),
            'TL': answer.get('SubmTL_'+str(i), ''),
            'ML': answer.get('SubmML_'+str(i), '')}
        if res['Feedback']:
            feed = True
        if res['Score']:
            score = True
        if res['Team']:
            team = True
        if res['TL']:
            tl = True
        if res['ML']:
            ml = True
        submissions.append(res)

    if team:
        submissions.sort(key=lambda x: int(x['ID']), reverse=1)
    else:
        submissions.sort(key=lambda x: int(x['ID']))

    return render_template("allsubmits.html", feed=feed, score=score, team=team,
            tl=tl, ml=ml, submissions=submissions)

@tswebapp.route('/getnewmsg')
@decorators.login_required
@decorators.channel_user('MSG')
def getnewmsg(channel):
    state, answer = util.communicate(channel, {
        'Team': session['team'],
        'Password': session['password'],
        'ContestId': session['contestid'],
        'Command': 'WaitingCount'})

    if state == 'error':
        return answer

    answer, id = answer
    if answer['ID'] == id:
        wtc = int(answer['WaitingCount'])
        tswebapp.logger.debug('Got wtc: '+str(wtc))
        if wtc == 0:
            return render_template("getnewmsg.html")
        if 'confirm' in request.args:
            state, answer = util.communicate(channel, {'ID': request.args['confirm'], 'Command': 'DisableUnrequested'})
            if state == 'error':
                return answer
            return render_template("msg_confirm.html", wtc=wtc - 1)
        else:
            state, answer = util.communicate(channel)

            if state == 'error':
                return answer

            answer, id = answer
            id = answer['ID']
    else:
        wtc = 0
        id = answer['ID']

    return render_template("getnewmsg.html", message=answer['Message'], id=id)

if __name__ == "__main__":
    tswebapp.run()
