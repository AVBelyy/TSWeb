
from flask import session
from functools import wraps
from copy import copy

from tsweb import util, testsys

def login_required(f):
    """
    This decorator aborts execution of function if user is not logged in.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not 'team' in session:
            return util.login_error()
        return f(*args, **kwargs)

    return wrapper

def channel_fetcher(request={}, auth=False):
    """
    This wrappper fetches data from testsys and calls decorated function with
    answer dict as first argument. It assumes function's first argument is
    channel instance, as done by @channel_user decorator. When auth == True,
    it automatically fills in authentication data.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(channel, *args, **kwargs):
            req = copy(request)
            if auth:
                #Fill in authenthication data
                req['Team'] = session['team']
                req['Password'] = session['password']
                req.setdefault('ContestId', session['contestid'])
            state, result = util.communicate(channel, req)
            if state == 'error':
                return result
            else:
                answer, id = result
                return f(answer, id, *args, **kwargs)
        return wrapper
    return decorator

def channel_user(chan):
    """
    This wrapper opens channel for function and closes it on function exit
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            channel = testsys.get_channel(chan)
            try:
                channel.open(1)
            except testsys.ConnectionFailedException as e:
                return util.error(e.message)

            try:
                return f(channel, *args, **kwargs)
            finally:
                channel.close()
        return wrapper
    return decorator
