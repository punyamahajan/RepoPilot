from .users import register_user


def submit_registration(username, password):
    return {'user': register_user(username, password), 'status': 201}
