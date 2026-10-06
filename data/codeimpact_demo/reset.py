from .auth import validate_password


def reset_password(password):
    if not validate_password(password):
        raise ValueError('Password does not meet policy')
    return True
