
from flask import session
from functools import wraps

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

def channel_fetcher(chan, request):
    """
    This wrappper fetches data from testsys and calls decorated function with
    answer dict as first argument.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            state, result = util.communicate(chan, request)
            if state == 'error':
                return result
            else:
                answer, channel, id = answer
                res = f(answer, channel, id, *args, **kwargs)
                channel.close()
                return res
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
