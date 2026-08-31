class User:
    """Represents an application user."""

    def __init__(self, id, username, password_hash, created_at):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at


def register_user(username, password):
    """Creates a new user record with a hashed password."""
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(id=generate_id(), username=username, password_hash=password_hash, created_at=now())
    db.insert("users", user)
    return user