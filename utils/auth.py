from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(roles):
    """
    Decorator to restrict access to specific roles.
    :param roles: List of roles allowed or a single role string.
    """
    if isinstance(roles, str):
        roles = [roles]
        
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
