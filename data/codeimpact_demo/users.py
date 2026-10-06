from .auth import validate_password


def register_user(username, password):
    if not validate_password(password):
        raise ValueError('Password does not meet policy')
    return {'username': username, 'registered': True}
