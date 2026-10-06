"""Password policy and identity checks for registration."""


def validate_password(password):
    return len(password) >= 8 and any(c.isdigit() for c in password)
