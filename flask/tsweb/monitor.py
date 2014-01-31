"""This module is used to parse raw monitor data from TestSys to bunch of
dictionaries and lists"""

import re
import tsweb

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
acm_result_regex = re.compile(r'[A-Z][A-Z]')
ioi_result_1_regex = re.compile(r'(\?\?)|(\-\-)')
ioi_result_2_regex = re.compile(r'\d{1,3}')
states = ('BEFORE', 'RUNNING', 'OVER', 'FROZEN', 'RESULTS')

class ParsingError(Exception):
    "This exception is raised when parsing function finds wrong input format"
    pass

def parse_line(line):
    """Parse line in form of '@command arg1, "arg 2", arg3' to
    tuple (command, [args])"""
    match = line_regex.match(line)
    if not match:
        raise ParsingError("@command expected")

    args = command_regex.findall(match.group(2))
    return match.group(1), args

def gen_monitor(history, data):
    """Generate config suitable for monitor.html template from raw history and
    monitor data"""
    if data and not history:
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
                tsweb.main.tswebapp.logger.error(
                    "Unexpected command in monitor: \
{0} while waiting for {1}".format(real_command, expected_command))
                raise ParsingError("Bad command in monitor")

            try:
                arg = converter(args[0])
            except ValueError as e:
                tsweb.main.tswebapp.logger.error(
                    "Bad argument '{0}' for command \
'{1}': {2}".format(args[0].encode('utf-8'), real_command, e.message))
                raise ParsingError("Bad command format in monitor")

            if not checker(arg):
                tsweb.main.tswebapp.logger.error(
                    "Bad argument '{0}' for command \
'{1}'".format(arg.encode('utf-8'), real_command))
                raise ParsingError("Bad command format in monitor")

            config[real_command] = arg

        if commands[0][0] == 'for':
            try:
                config['m_for'] = commands[0][1][0]
            except ValueError as e:
                tsweb.main.tswebapp.logger.error(
                    "Bad argument '{0}' for command \
'{1}'".format(commands[0][1][0].encode('utf-8'), 'for'))
                raise ParsingError("Bad command format in monitor")
            commands.pop(0)

        problems = {}
        for i in xrange(config['problems']):
            p, problem = commands.pop(0)
            if p != 'p':
                tsweb.main.tswebapp.logger.error(
                    "Expected problem {} of {}, got '{} {}",
                    i, config['problems'], p, problem)
                continue
            id, name, p1, p2 = problem
            if not problem_id_regex.match(id):
                tsweb.main.tswebapp.logger.error(
                    "Bad problem id: '{0}'".format(id))
                raise ParsingError("Bad problem specification")
            try:
                p1 = int(p1)
                p2 = int(p2)
            except ValueError:
                tsweb.main.tswebapp.logger.error("Invalid penalty: '{0}, \
{1}'".format(p1, p2))

            problems[id] = (name, p1, p2)

        teams = {}
        for i in xrange(config['teams']):
            t, team = commands.pop(0)
            if t != 't':
                tsweb.main.tswebapp.logger.error(
                    "Expected team {} of {}, got '{} {}",
                    i, config['teams'], t, team)
                continue

            id, monclass, monset, name = team

            # remove double quotes from name (if needed)
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]

            if not problem_id_regex.match(id):
                tsweb.main.tswebapp.logger.error(
                    "Bad team id: '{0}'".format(id))
                raise ParsingError("Bad team specification")
            try:
                monclass = int(monclass)
                monset = int(monset)
            except ValueError:
                tsweb.main.tswebapp.logger.error("Invalid monclass or monset: \
'{0}, {1}'".format(monclass, monset))

            #Fields 3, 4, 5 and 6 are prepared for future solved, score, rank counters and table row classifier
            teams[id] = [monclass, monset, name, 0, 0, 0, 0]

        submissions = []
        IOI = 0
        IOIScores = 0
        for i in xrange(config['submissions']):
            s, submission = commands.pop(0)
            if s != 's':
                tsweb.main.tswebapp.logger.error(
                    "Expected submission {} of {}, got '{} {}",
                    i, config['submissions'], s, submission)
                continue

            team, problem, attempt, time, result = submission[:5]
            attempt = int(attempt)
            time = int(time)
            if len(submission) == 6:
                test = int(submission[5])
            else:
                test = 0

            mode = 0
            if acm_result_regex.match(result):
                mode = -1
            elif ioi_result_1_regex.match(result):
                mode = 1
            elif ioi_result_2_regex.match(result):
                mode = 1
                IOIScores = 1

            if not IOI:
                IOI = mode

            if not mode:
                tsweb.main.tswebapp.logger.error(
                    "Invalid result code {}".format(result))
                raise ParsingError("Bad monitor format")

            if mode != IOI:
                tsweb.main.tswebapp.logger.error("Mixed acm/ioi monitor")
                raise ParsingError("Bad monitor format")

            if (result == 'OK' or result == "OC" or (IOI > 0 and result != "--")) and test != 0:
                tsweb.main.tswebapp.logger.error(
                    "Test number not expected for OK/OC result or IOI monitor")
                tsweb.main.tswebapp.logger.debug("{}".format(submission))

            submissions.append({'team': team, 'problem': problem,
                'attempt': attempt, 'time': time, 'result': result,
                'htime': '%d:%02d:%02d' % (time/3600, (time/60) % 60, time % 60),
                'test': test, 'team_name': teams[team][2]})

        if IOI < 0:
            IOI = 0

        TeamsResults = {}
        accepted_counters = dict(zip(problems.keys(), [0]*len(problems)))
        rejected_counters = dict(zip(problems.keys(), [0]*len(problems)))

        active_teams = []
        for team in teams:
            results = []
            active_team = False
            for problem in sorted(problems):
                #Get submissions of current problem by current team
                subs = filter(
                    lambda x: x['team'] == team and x['problem'] == problem,
                    submissions)
                #Sort them by attempts (secondary key)
                subs.sort(key=lambda x: x['attempt'])
                #And by time (primary key)
                subs.sort(key=lambda x: x['time'])

                if not subs:
                    result = (0, 0, 0, '', 0)
                else:
                    ioi_cutoff = len(subs)
                    for i, sub in enumerate(subs):
                        if sub['result'] in ('OK', 'OC'):
                            del subs[i+1:]
                            break
                        if sub['result'] != '--':
                            ioi_cutoff = i

                    if IOI:
                        del subs[ioi_cutoff+1:]

                    sub = subs[-1]
                    attempts = len(subs)
                    #Format of result: (+-attempts, score, time, result, test number)
                    if sub['result'] == 'OC':
                        result = (1, 0, sub['time'], sub['result'], 0)
                    elif IOI:
                        if sub['result'] != '--':
                            result = (attempts, '??' if sub['result'] == '??' else int(sub['result']), sub['time'], sub['result'], 0)
                        else:
                            result = (-attempts, 0, sub['time'], sub['result'], 0)
                    else:
                        if sub['result'] == 'OK':
                            result = (attempts,
                                problems[problem][1] * 60 * (attempts-1) + sub['time'],
                                sub['time'], sub['result'], 0)
                        else:
                            result = (-attempts,
                                problems[problem][2] * 60 * attempts, sub['time'],
                                sub['result'], sub['test'])

                    #Increase proper counters for team
                    if result[0] > 0:
                        teams[team][3] += 1  # solved counter
                        #Set global statistic counters
                        accepted_counters[problem] += 1
                        rejected_counters[problem] += attempts-1
                    else:
                        rejected_counters[problem] += attempts

                    if not IOI:
                        teams[team][4] += result[1] #time for ACM rules contests
                    if IOIScores and result[1] != '??':
                        teams[team][4] += result[1]  # scores counter
                results.append(result)
                if result != (0, 0, 0, '', 0):
                    active_team = True
            if active_team:
                TeamsResults[team] = results
                active_teams.append((team, teams[team][2]))

        active_teams.sort(key=lambda x: x[1])

        if IOI:
            #Sort teams by id
            teams_order = sorted(teams)
            #Sort teams by score or solved count
            teams_order = sorted(teams_order,
                                 key=lambda x: teams[x][4 if IOIScores else 3],
                                 reverse=1)
        else:
            #Sort teams by id (third key)
            teams_order = sorted(teams)
            #Then by scores (secondary key)
            teams_order = sorted(teams_order, key=lambda x: teams[x][4])
            #And by attempts (primary key)
            teams_order = sorted(teams_order, key=lambda x: teams[x][3], reverse=1)

        #Assing ranks
        rank = 0
        straight_rank = 0
        prob = 0
        solved = -1
        score = -1
        for i, team in enumerate(teams_order):
            #Rank is not increased only if this team has the same score and
            #solved count as the previous one
            if teams[team][3] != solved:
                prob += 1
            if not (teams[team][4] == score and
                    (IOIScores or teams[team][3] == solved)):
                rank = i + 1
                straight_rank += 1
            teams[team][5] = rank
            teams[team][6] = straight_rank if IOIScores else prob
            solved = teams[team][3]
            score = teams[team][4]

        config['teams_list'] = [((i,)+tuple(teams[i])) for i in teams_order]
        config['active_teams'] = active_teams
        config['results'] = TeamsResults
        config['problem_list'] = (problems)
        config['accepts'] = accepted_counters
        config['rejects'] = rejected_counters
        config['total_accepts'] = sum(accepted_counters.itervalues())
        config['total_rejects'] = sum(rejected_counters.itervalues())
        config['IOI'] = IOI == 1

        if len(submissions) > 0:
            succ = filter(
                lambda x: True if x['result'] == 'OK' or x['result'] == 'OC' else False,
                sorted(submissions, key=lambda y: y['time'], reverse=1))
            if succ == []:
                config['last_success'] = None
            else:
                config['last_success'] = succ[0]
            config['last_submission'] = sorted(submissions,
                key=lambda x: x['time'], reverse=1)[0]
        else:
            config['last_success'] = None
            config['last_submission'] = None
    except ParsingError as e:
        config = {'error': e.message}
    return config
