
import re
import testsys
from flask import Flask, render_template, request, session, redirect, url_for

tswebapp = Flask('tsweb')
tswebapp.secret_key = '123asd'

@tswebapp.route('/', methods=['GET', 'POST'])
@tswebapp.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        if request.args.get('op', '') == 'logout':
            tm = ', {0}'.format(session['team']) if session.get('cookie_state', 0) > 0 else ''
            session.pop('cookie_state', None)
            return render_template("redirect.html", text="Thanks for logging out{0}!".format(tm))
        elif session.get('cookie_state', 0) <= 0:
            return render_template("index.html",
                    error="Your session data is missing, expired or invalid." if session.get('cookie_state', 0) < 0 else '')

        return format_main_page()
    else:
        if request.form['op'] == 'changecontest':
            session['contestid'] = request.form['newcontestid']
            session['cookie_state'] = 2
            return render_template("redirect.html", text="Your contest has been changed to {0}, {1}".format(session['contestid'], request.form['team']))
        elif request.form['op'] == 'login':
            if not testsys.valid_teamname(request.form['team']):
                return render_template("error.html", text="Invalid team name")
            if not request.form['password']:
                return render_template("error.html", text="Non-empty password expected")
            session['cookie_state'] = 2
            session['team'] = request.form['team']
            session['password'] = request.form['password']
            return render_template("redirect.html", text="Thank you for logging in, {0}!".format(request.form['team']))
        elif session['cookie_state'] <= 0:
            return render_template("index.html", error="Your session data is missing, expired or invalid.")

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
