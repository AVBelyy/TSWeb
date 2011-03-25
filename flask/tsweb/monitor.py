
import re
import main

command_regex = re.compile(r"""
(?<!\\)" #match opening quot, unless it's escaped
.+? #match string contents
(?<!\\)" #match closing quot, unless it's escaped
| #or ordinal string
[^,]+ #match string between two delimeters""", re.X + re.U)
line_regex = re.compile(r'\@(.+?) (.+)', re.U)
crlf_regex = re.compile(r'\r?\n')
date_regex = re.compile(r'\d{2}\.\d{2}\.\d{2,4}\s\d{2}:\d{2}:\d{2}')
problem_id_regex = re.compile(r'^[A-Za-z0-9_\-]{1,16}$')
states = ('BEFORE', 'RUNNING', 'OVER', 'FROZEN', 'RESULTS')

class ParsingError(Exception):
    pass

def parse_line(line):
    match = line_regex.match(line)
    if not match:
        raise ParsingError("@command expected")

    args = command_regex.findall(match.group(2))
    main.tswebapp.logger.debug("'{0}' parsed to '{1} {2}'".format(line.encode('utf-8'), match.group(1).encode('utf-8'), args))
    return match.group(1), args

def gen_monitor(history, data):
    if data and not history:
        main.tswebapp.logger.debug(data.decode('cp866'))
        return {'pre': data.decode('cp866')}

    history = crlf_regex.split(history.decode('cp1251').strip())
    #Order of commands in valid monitor
    #Format: (name, converter, checker)
    command_order = [
        ('contest', lambda x: x.replace('"', ''), lambda x: True),
        ('startat', unicode, date_regex.match),
        ('contlen', int, lambda x: True),
        ('now', int, lambda x: True),
        ('state', unicode, lambda x: x in states),
        ('freeze', int, lambda x: True),
        ('problems', int, lambda x: True),
        ('teams', int, lambda x: True),
        ('submissions', int, lambda x: True)]

    try:
        commands = [parse_line(i) for i in history]
        config = {'commands': commands[:]}
        while command_order:
            real_command, args = commands.pop(0)
            expected_command, converter, checker = command_order.pop(0)

            if real_command != expected_command:
                main.tswebapp.logger.error("Unexpected command in monitor: {0} while waiting for {1}".format(real_command, expected_command))
                raise ParsingError("Bad command in monitor")

            try:
                arg = converter(args[0])
            except ValueError as e:
                raise e
                main.tswebapp.logger.error("Bad argument '{0}' for command '{1}': {2}".format(args[0].encode('utf-8'), real_command, e.message))
                raise ParsingError("Bad command format in monitor")

            if not checker(arg):
                main.tswebapp.logger.error("Bad argument '{0}' for command '{1}'".format(arg.encode('utf-8'), real_command))
                raise ParsingError("Bad command format in monitor")

            config[real_command] = arg

        if commands[0][0] == 'for':
            try:
                config['m_for'] = commands[0][1][0]
            except ValueError as e:
                main.tswebapp.logger.error("Bad argument '{0}' for command '{1}'".format(commands[0][1][0].encode('utf-8'), 'for'))
                raise ParsingError("Bad command format in monitor")
            commands.pop(0)

        problems = {}
        for i in xrange(config['problems']):
            p, problem = commands.pop(0)
            if p != 'p':
                raise ParsingError('Insufficient problem count')
            id, name, p1, p2 = problem
            if not problem_id_regex.match(id):
                main.tswebapp.logger.error("Bad problem id: '{0}'".format(id))
                raise ParsingError("Bad problem specification")
            try:
                p1 = int(p1)
                p2 = int(p2)
            except ValueError:
                main.tswebapp.logger.error("Invalid penalty: '{0}, {1}'".format(p1, p2))

            problems[id] = (name, p1, p2)

        teams = {}
        for i in xrange(config['teams']):
            t, team = commands.pop(0)
            if t != 't':
                raise ParsingError("Insufficient team count")
            id, monclass, monset, name = team
            if not problem_id_regex.match(id):
                main.tswebapp.logger.error("Bad team id: '{0}'".format(id))
                raise ParsingError("Bad team specification")
            try:
                monclass = int(monclass)
                monset = int(monset)
            except ValueError:
                main.tswebapp.logger.error("Invalid monclass or monset: '{0}, {1}'".format(monclass, monset))

            #Fields 3, 4 and 5 are prepared for future solved, score and rank counter
            teams[id] = [monclass, monset, name, 0, 0, 0]

        submissions = []
        ioi = 0
        for i in xrange(config['submissions']):
            s, submission = commands.pop(0)
            if s != 's':
                raise ParsingError("Insufficient submission count")
            team, problem, attempt, time, result = submission[:5]
            attempt = int(attempt)
            time = int(time)
            if len(submission) == 6:
                test = int(submission[5])
            else:
                test = 0

            if result == 'OK' and test != 0:
                main.tswebapp.logger.error("Test number not expected for OK result")
                raise ParsingError("Bad monitor format")

            submissions.append({'team': team, 'problem': problem,
                    'attempt': attempt, 'time': time, 'result': result,
                    'htime': '%d:%02d:%02d' % (time/3600, (time/60) % 60, time % 60),
                    'test': test, 'team_name': teams[team][2]})

        TeamsResults = {}
        for team in teams:
            results = []
            for problem in sorted(problems):
                #Get submissions of current problem by current team
                subs = filter(lambda x: x['team'] == team and x['problem'] == problem, submissions)
                #Sort them by attempts (secondary key)
                subs.sort(key=lambda x: x['attempt'])
                #And by time (primary key)
                subs.sort(key=lambda x: x['time'])

                if not subs:
                    result = (0, 0, 0, '', 0)
                else:
                    for i, sub in enumerate(subs):
                        if sub['result'] == 'OK':
                            del subs[i+1:]
                            break

                    sub = subs[-1]
                    attempts = len(subs)
                    #Format of result: (+-attempts, score, time, result, test number)
                    if sub['result'] == 'OK':
                        result = (attempts, problems[problem][1] * 60 * (attempts-1) + sub['time'], sub['time'], sub['result'], 0)
                    else:
                        result = (-attempts, problems[problem][2] * 60 * attempts, sub['time'], sub['result'], sub['test'])
                    #Increase proper counters for team
                    if result[0] > 0:
                        teams[team][3] += 1 #solved counter
                    teams[team][4] += result[1] #scores counter
                results.append(result)
            TeamsResults[team] = results

        #Sort teams by id (third key)
        teams_order = sorted(teams)
        #Then by scores (secondary key)
        teams_order = sorted(teams_order, key=lambda x: teams[x][4])
        #And by attempts (primary key)
        teams_order = sorted(teams_order, key=lambda x: teams[x][3], reverse=1)

        #Assign ranks to teams
        rank = 1
        for team in teams_order:
            teams[team][5] = rank
            if teams[team][3]: #If team has solved some task, next team's rank will increase, otherwise it'll be same
                rank += 1

        config['teams_list'] = [((i,)+tuple(teams[i])) for i in teams_order]
        config['results'] = TeamsResults
        config['problem_list'] = sorted(problems)

        config['last_success'] = filter(
            lambda x: True if x['result'] == 'OK' or x['result'] == 'OC' else False,
            sorted(submissions, key=lambda x: x['time']))[0]
        config['last_submission'] = subs[0]
    except ParsingError as e:
        config = {'error': e.message}
    return config
