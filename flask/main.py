
import testsys
from flask import Flask, render_template, request, session, redirect, url_for

tswebapp = Flask(__name__)
#tswebapp.secret_key = 'asdfgh'
tswebapp.secret_key = '123asd'

@tswebapp.route('/', methods=['GET', 'POST'])
@tswebapp.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template("index.html")
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
            return render_template("redirect.html", team=request.form['team'])
        elif request.form['op'] == 'logout':
            tm = ', {0}'.format(request.form['team']) if session['cookie_state'] > 0 else ''
            return render_template("redirect.html", "Thanks for loggin out{0}".format(tm))
        elif session['cookie_state'] <= 0:
           pass 
if __name__ == "__main__":
    tswebapp.debug = True
    tswebapp.run()
