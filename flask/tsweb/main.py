
# -*- coding: utf8; -*-

import re
from . import testsys, config, monitor, decorators, util
from .app import tswebapp, babel
from .compat import xrange
from flask import Flask, render_template, request, session, redirect, url_for, make_response
from werkzeug import secure_filename
from flask.ext.babel import Babel, gettext, refresh


@babel.localeselector
def get_locale():
    if 'lang' in session:
        return session['lang']
    else:
        lang = request.accept_languages.best_match(config.LANGUAGES.keys())
        session['lang'] = lang
        return lang

@tswebapp.route('/')
@tswebapp.route('/index')
def index():
    if 'team' in session:
        return format_main_page()
    else:
        return render_template("index.html")

@tswebapp.route('/logout')
def logout():
    tm = ', {0}'.format(session['team']) if 'team' in session else ''
    session.pop('team', None)
    response = util.redirector(url_for('index'), text="Thanks for logging out{0}!".format(tm))
    if 'purge' in request.args:
        session.clear()
        response.delete_cookie(tswebapp.session_cookie_name)

    return response

@tswebapp.route('/login', methods=['POST'])
def login():
    if not testsys.valid_teamname(request.form['team']):
        return render_template("error.html", text=gettext("Invalid team name"))

    if not request.form['password']:
        return render_template("error.html", text=gettext("Non-empty password expected"))

    state, answer = util.communicate('MSG', {
            'Team': request.form['team'],
            'Password': request.form['password'],
            'ContestId': request.form.get('contestid', ''),
            'AllMessages': 'Yes',
            'DisableUnrequested': 1})

    if state == 'error':
        return answer

    answer = answer[0]

    session['team'] = request.form['team']
    session['password'] = request.form['password']
    session['contestid'] = answer.get('ContestId', '')
    session['team_name'] = answer.get('TeamName', '')

    return util.redirector(url_for('index'), text=gettext("Thank you for logging in, {0}!").format(session['team']))

@decorators.channel_user('MSG')
@decorators.channel_fetcher({
    'AllMessages': 'Yes',
    'DisableUnrequested': 1}, auth=True)
def format_main_page(ans, ans_id):
    config = {}
    config['wtc'] = int(ans.get('WaitingCount', 0))
    config['jury'] = ans.get('JuryMode', False)
    config['statements'] = ans.get('StatementsLink', '')
    config['contlist_mask'] = tswebapp.config['CONTLIST_MASK']

    # TestSys is rather inconsistent with its encodings, so we need to recode
    # here
    if tswebapp.config['PUN']:
        config['messages'] = [mangle_result(msg) for msg in re.split('\r?\n',
            ans.get('AllMessages', '').encode('cp866').decode('cp1251'))]
    else:
        config['messages'] = re.split('\r?\n',
            ans.get('AllMessages', '').encode('cp866').decode('cp1251'))

    config['version'] = ans.get('Version', 0)
    config['contid'] = ans.get('ContestId', '')
    config['contname'] = ans.get('ContestName', '')
    config['contest_start'] = ans.get('ContestStart', '00:00:00')
    config['contest_duration'] = ans.get('ContestDuration', '00:00:00')
    config['server_now'] = ans.get('ServerNow', '00:00:00')
    session['team_name'] = ans.get('TeamName', session['team'])

    return render_template("main.html", **config)

def mangle_result(string):
    string = string.replace('Time Limit', u'Непунктуальность возмутительная')
    string = string.replace('Wrong Answer', u'Происки бесовские')
    string = string.replace('Accepted', u'Счастье вселенское')
    string = string.replace('Compilation Error', u'Ты бестолочь')
    return string


@decorators.channel_fetcher({'Request': 'ContestData'}, auth=True)
def get_compilers(ans, id):
    pmode = 0
    compilers, problems, extensions = [], {}, {}
    data = ans['Data']
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
@decorators.login_required
@decorators.channel_user('SUBMIT')
def submit(channel):
    try:
        problems, compilers, extensions = get_compilers(channel)
    except testsys.CommunicationException as e:
        return render_template("error.html", text=e.message)

    if request.method == 'GET':
        config = {}
        config['problems'] = problems
        config['compilers'] = compilers
        return render_template("submit.html", **config)
    elif request.method == 'POST':
        data = None
        if request.files['file']:
            data = util.detect_and_convert(request.files['file'].read())
            filepath = secure_filename(request.files['file'].filename)
            filename = ''.join(filepath.split('.')[:-1])
        if request.form['solution']:
            data = util.detect_and_convert(request.form['solution'])
            filepath = request.form['prob'] + '.' + request.form['lang']
            filename = request.form['prob']

        if not data:
            return util.error(gettext("No solution presented"))
#        if not filepath.split('.')[-1] in extensions:
#            return error("Invalid file type")
        if not request.form['prob'] in problems:
            return util.error(gettext("Unknown problem '{0}'").format(request.form['prob']))
        if not compilers[int(request.form.get('lang', '0')) - 1][0] in extensions:
            return util.error(gettext("Unknown compiler '{0}'").format(request.form['lang']))

        state, answer = util.communicate(channel, {
            'Team': session['team'],
            'Password': session['password'],
            'ContestId': session['contestid'],
            'Problem': request.form['prob'],
            'Contents': data,
            'Source': filename,
            'Compiler': compilers[int(request.form['lang']) - 1][1],
            'Extension': compilers[int(request.form['lang']) - 1][0]})

        if state == 'error':
            return answer

        session['last_problem'] = request.form['prob']
        session['last_compiler'] = request.form['lang']

        return render_template("submit_status.html")

@tswebapp.route('/monitor')
@decorators.login_required
@decorators.channel_user('MONITOR')
@decorators.channel_fetcher(auth=True, encoding=('cp1251', 'cp866'))
def monitor_page(ans, ans_id):
    config = monitor.gen_monitor(ans['History'], ans['Monitor'])
    return render_template("monitor.html", **config)

@tswebapp.route('/contest/<id>')
@decorators.login_required
def changecontest(id):
    session['contestid'] = id
    return util.redirector(url_for('index'), text=gettext("Your contest has been changed to {0}, {1}!").format(id, session['team']))

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
        'SubmLimit': request.args.get('limit', 1000),
        'Command': 'AllSubmits'})

    if state == 'error':
        return answer

    answer, id = answer

    submissions = []
    feed, score, team, tl, ml = False, False, False, False, False
    for i in xrange(int(answer.get('Submits', ''))):
        res = {
            'Problem': answer.get('SubmProb_'+str(i), ''),
            'ID': answer.get('SubmID_'+str(i), ''),
            'Time': answer.get('SubmTime_'+str(i), ''),
            'Result': answer.get('SubmRes_'+str(i), ''),
            'Test': answer.get('SubmTest_'+str(i), ''),
            # Encode back to let chardet guess
            'CE': util.detect_and_convert(
                answer.get('SubmCE_'+str(i), '').encode('cp866')),
            'Attempt': answer.get('SubmAtt_'+str(i), ''),
            'Feedback': answer.get('SubmFeed_'+str(i), ''),
            'Compiler': answer.get('SubmCompiler_'+str(i), ''),
            'TokenUsed': answer.get('SubmTokenUsed_'+str(i), ''),
            'Score': answer.get('SubmScore_'+str(i), ''),
            'Team': answer.get('SubmTeam_'+str(i), ''),
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

@tswebapp.route('/allsubmits/view/<int:id>')
@decorators.login_required
@decorators.channel_user('MSG')
def viewsubmit(channel, id):
    state, answer = util.communicate(channel, {
        'Team': session['team'],
        'Password': session['password'],
        'ContestId': session['contestid'],
        'DisableUnrequested': '1',
        'SubmID': id,
        'Command': 'SubmText'},
        encoding='detect')

    if state == 'error':
        return answer

    answer, ans_id = answer

    if request.args.get('raw', ''):
        resp = make_response(answer['SubmText'])
        resp.headers['Content-Type'] = 'text/plain'
        return resp
    else:
        css, text = util.highlight(answer['SubmText'], answer.get('FileName'))
        return render_template("viewsubmit.html", css=css, text=text, id=id)

@tswebapp.route('/allsubmits/feedback/<int:id>')
@decorators.login_required
@decorators.channel_user('MSG')
def feedback(channel, id):
    state, answer = util.communicate(channel, {
        'Team': session['team'],
        'Password': session['password'],
        'ContestId': session['contestid'],
        'SubmID': id,
        'Command': 'ViewFeedback'},
        encoding='detect')

    if state == 'error':
        return answer

    answer, ans_id = answer

    return render_template("feedback.html", hdr=answer.get('FeedbackAddHeader', ''),
                           feedback=answer.get('Feedback', ''),
                           id=id)

@tswebapp.route('/contests')
@decorators.login_required
@decorators.channel_user('MSG')
def contests(channel):
    state, answer = util.communicate(channel, {
        'Team': session['team'],
        'Password': session['password'],
        'ContestId': session['contestid'],
        'Command': 'ListContests',
        'Mask': request.args.get('mask', 1)})

    if state == 'error':
        return answer

    answer, ans_id = answer
    contests = util.parse_contests(answer['Contests'])
    return render_template("contests.html", contests=contests)

@tswebapp.route('/getnewmsg')
@decorators.login_required
@decorators.channel_user('MSG')
def getnewmsg(channel):
    state, answer = util.communicate(channel, {
        'Team': session['team'],
        'Password': session['password'],
        'ContestId': session['contestid'],
        'Command': 'WaitingCount'},
        encoding='cp1251')

    if state == 'error':
        return answer

    answer, id = answer
    if answer['ID'] == id:
        wtc = int(answer['WaitingCount'])
        if wtc == 0:
            return render_template("getnewmsg.html")
        if 'confirm' in request.args:
            state, answer = util.communicate(channel,
                {'ID': request.args['confirm'], 'Command': 'DisableUnrequested'},
                encoding='cp1251')
            if state == 'error':
                return answer
            if wtc > 1:
                return redirect(url_for("getnewmsg"))
            else:
                return redirect(url_for("index"))
        else:
            state, answer = util.communicate(channel, encoding='cp1251')

            if state == 'error':
                return answer

            answer, id = answer
            id = answer['ID']
    else:
        wtc = 0
        id = answer['ID']

    return render_template("getnewmsg.html", message=answer.get('Message', ''), id=id)

@tswebapp.route('/clars')
@decorators.login_required
@decorators.channel_user('MSG')
@decorators.channel_fetcher({'DisableUnrequested': 1, 'Command': 'AllClars'}, auth=True, encoding='cp1251')
@decorators.channel_user('SUBMIT')
def clars(channel, clars_data, ans_id):
    problems, compilers, extensions = get_compilers(channel)
    problems['*'] = 'Generic'
    clars = []
    for i in xrange(int(clars_data['Clars'])):
        clar = {}
        clar['from'] = clars_data.get('ClarFrom_'+str(i), '')
        clar['problem'] = clars_data.get('ClarProb_'+str(i), '')
        clar['question'] = clars_data.get('ClarQ_'+str(i), '')
        clar['answer'] = clars_data.get('ClarA_'+str(i), '')
        clar['answered'] = int(clars_data.get('ClarAnswd_'+str(i), 0))
        clar['broadcast'] = int(clars_data.get('ClarBCast_'+str(i), 0))
        clars.append(clar)
    return render_template("clars.html", problems=problems, clars=clars)

@tswebapp.route('/clars/submit', methods=['POST'])
@decorators.login_required
@decorators.channel_user('MSG')
def submit_clar(channel):
    state, answer = util.communicate(channel, {
        'Team': session['team'],
        'Password': session['password'],
        'ContestId': session['contestid'],
        'Problem': request.form['prob'],
        'Command': 'Clar',
        'Clar': request.form['clar']})
    if state == 'error':
        return answer

    return render_template("clar_status.html")

@tswebapp.route('/set_language')
def set_language():
    session['lang'] = request.args.get('lang', 'en')
    refresh()
    return redirect(url_for('index'))

if __name__ == "__main__":
    tswebapp.run(host='0.0.0.0')
