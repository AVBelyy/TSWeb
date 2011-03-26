
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
                return f(answer, *args, **kwargs)
        return wrapper
    return decorator

