
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
result_t1_regex = re.compile(r'^\?(..)\?$')
result_t2_regex = re.compile(r'^[A-Z]{2}$')
result_t3_regex = re.compile(r'^((\d{1,3})|(\?\?)|(\-\-))$')

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
                mon_for = int(commands[0][1][0])
            except ValueError as e:
                main.tswebapp.logger.error("Bad argument '{0}' for command '{1}'".format(commands[0][1][0].encode('utf-8'), 'for'))
                raise ParsingError("Bad command format in monitor")
            commands.pop(0)
        else:
            mon_for = None

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

        config['problem_list'] = problems

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

            teams[id] = (monclass, monset, name)

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

            match = result_t1_regex.match(result)
            if match:
                result = match.group(1)
            elif result_t2_regex.match(result):
                ths = -1
            elif result_t3_regex.match(result):
                ths = 1

            if not ioi:
                ioi = ths
            if not ths:
                main.tswebapp.logger.error("Invalid result code '{0}'".format(result))
                raise ParsingError("Bad submission syntax")
            if ioi != ths:
                main.tswebapp.logger.error("Mixed acm/ioi monitor")
                raise ParsingError("Bad monitor format")
            if (result == 'OK' or result == 'OC') and test != 0:
                main.tswebapp.logger.error("Test number not expected for OK/OC result")
                raise ParsingError("Bad monitor format")
            if ioi > 0 and test != 0 and result != '--':
                main.tswebapp.logger.error("Test number not expected in ioi monitor")
                raise ParsingError("Bad monitor format")

            submissions.append({'team': team, 'problem': problem,
                    'attempt': attempt, 'time': time, 'result': result,
                    'htime': '%d:%02d:%02d' % (time/3600, (time/60) % 60, time % 60),
                    'test': test, 'team_name': teams[team][2]})
        subs = sorted(submissions, key=lambda x: x['time'], reverse=1)
        results = []
        rank = 1
        for team in sorted(teams):
            p_result = []
            solved = 0
            for problem in sorted(problems):
                #Get all submissions of 'problem' by 'team'
                p_t_subs = [i for i in submissions if i['team'] == team and i['problem'] == problem]
                if not p_t_subs:
                    p_result.append(('', 0, False, False))
                    continue
                #Strip all submissions after accepted one
                l = len(p_t_subs)
                succ = False
                for i, sub in enumerate(p_t_subs):
                    if sub['result'] in ('OK', 'OC', '--'):
                        l = i+1
                        solved += 1
                        succ = True
                        break
                htime = p_t_subs[l-1]['htime']
                attempted = htime != ''
                p_result.append((htime, l, succ, attempted))
            results.append([team, teams[team][2], p_result, solved, 0])
        results.sort(key=lambda x: x[3], reverse=1)
        rank = 1
        for e in results:
            e[4] = rank
            if e[3]:
                rank += 1
        config['last_success'] = filter(
            lambda x: True if x['result'] == 'OK' or x['result'] == 'OC' else False,
            subs)[0]
        config['last_submission'] = subs[0]
        config['results'] = results
    except ParsingError as e:
        config = {'error': e.message}
    return config
