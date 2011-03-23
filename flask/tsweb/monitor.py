
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
        config = {}
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

        config['commands'] = commands
    except ParsingError as e:
        config = {'error': e.message}
    config['last_success'] = {}
    return config
