
import re
import testsys
from flask import Flask, render_template, request, session, redirect, url_for

tswebapp = Flask('tsweb')
tswebapp.secret_key = '123asd'

def redirector(url, **kwargs):
    res = redirect(url)
    res.response = [render_template("redirect.html", **kwargs)]

    return res

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

if __name__ == "__main__":
    tswebapp.debug = True
    tswebapp.run()
