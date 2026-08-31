def login(username, password):
    """Checks credentials against the users table and returns a session token."""
    user = find_user(username)
    if user and verify_password(password, user.password_hash):
        return create_session_token(user)
    return None


def find_user(username):
    """Looks up a user record by username in the users table."""
    return db.query(User).filter_by(username=username).first()


def verify_password(password, password_hash):
    """Checks a plaintext password against a stored hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_session_token(user):
    """Generates a signed session token for an authenticated user."""
    return jwt.encode({"user_id": user.id}, SECRET_KEY, algorithm="HS256")