# RAG Pipeline Analysis

Model: `codellama`. Source: the same recorded evaluation questions, retrieved chunks, and responses used in the quantitative comparison.

## Retrieval → context → response summary

| Observation | Count |
|---|---:|
| Relevant information was retrieved | 24/24 |
| Irrelevant information was retrieved first | 3/24 |
| Important information was missed | 0/24 |
| The LLM produced a correct answer | 9/24 |
| The LLM hallucinated despite having context | 4/24 |
## Controlled missed-information trace

The 24-question benchmark retrieves all three chunks from this three-file sample, so it cannot naturally demonstrate omitted context. This additional sensitivity case deliberately uses `k=1` for a question that requires two files; it is reported separately and is not mixed into the model-comparison scores.

- Retrieval depth: **1**
- Expected files: **auth.py, models.py**
- Retrieved files: **auth.py**
- Important information missed: **models.py**

### Question → Retrieved context → LLM response

**Question:** Which files and functions are involved in user authentication and registration?

**Retrieved context:**

```
auth.py (chunk 0):
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
```

**LLM response:**

The files and functions involved in user authentication and registration are:

* auth.py: This file contains the login() function, which checks credentials against the users table and returns a session token.
* find_user(): This function looks up a user record by username in the users table.
* verify_password(): This function checks a plaintext password against a stored hash.
* create_session_token(): This function generates a signed session token for an authenticated user.

Note that these functions are not necessarily involved in user registration, as registration typically involves creating a new user record in the database. However, these functions are involved in the authentication process, which is an important part of user registration.


## Relationship analysis

- The expected file was the top result for **21/24** questions.
- When the expected file ranked first, **8/21** answers were fully correct.
- Even with the expected file ranked first, **4/21** answers triggered the hallucination heuristic.
- When another file ranked first, **1/3** answers were still fully correct.

These counts separate three different failure points: retrieval can rank the wrong source, the assembled context can omit an important source, and the LLM can still misuse relevant context. A RAG call is therefore only successful when retrieval, context construction, and generation all succeed together.

## Representative traces

## Relevant information was retrieved

At least one retrieved chunk came from the expected source file.

### explain-01: What does login do?

- Category: **code explanation**
- Expected file: `auth.py`
- Top retrieval correct: **yes**
- Expected file present anywhere: **yes**
- Answer accuracy: **33.3%**
- Hallucination flag: **no**

#### Question → Retrieved context → LLM response

**Question:** What does login do?

**Retrieved context:**

```
auth.py (chunk 0):
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

payment.py (chunk 0):
def process_payment(user_id, amount):
    """Calls the Stripe API to charge a user and logs the transaction."""
    fee = calculate_fee(amount)
    charge = stripe.Charge.create(amount=amount, customer=user_id)
    log_transaction(user_id, amount, fee, charge.id)
    return charge


def calculate_fee(amount, rate=0.03):
    """Returns the platform fee for a given payment amount."""
    return round(amount * rate, 2)


def log_transaction(user_id, amount, fee, charge_id):
    """Writes a record of the payment to the payments table."""
    db.insert("payments", {
        "user_id": user_id,
        "amount": amount,
        "fee": fee,
        "charge_id": charge_id,
    })

models.py (chunk 0):
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
```

**LLM response:**

login() is a function that checks the credentials entered by the user against the users table in the database. If the user exists and the password entered matches the password stored in the database, the function returns a session token for the user. Otherwise, it returns None.

### explain-02: How is a payment processed?

- Category: **code explanation**
- Expected file: `payment.py`
- Top retrieval correct: **yes**
- Expected file present anywhere: **yes**
- Answer accuracy: **100.0%**
- Hallucination flag: **no**

#### Question → Retrieved context → LLM response

**Question:** How is a payment processed?

**Retrieved context:**

```
payment.py (chunk 0):
def process_payment(user_id, amount):
    """Calls the Stripe API to charge a user and logs the transaction."""
    fee = calculate_fee(amount)
    charge = stripe.Charge.create(amount=amount, customer=user_id)
    log_transaction(user_id, amount, fee, charge.id)
    return charge


def calculate_fee(amount, rate=0.03):
    """Returns the platform fee for a given payment amount."""
    return round(amount * rate, 2)


def log_transaction(user_id, amount, fee, charge_id):
    """Writes a record of the payment to the payments table."""
    db.insert("payments", {
        "user_id": user_id,
        "amount": amount,
        "fee": fee,
        "charge_id": charge_id,
    })

auth.py (chunk 0):
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

models.py (chunk 0):
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
```

**LLM response:**

A payment is processed by calling the `process_payment()` function, which takes a user ID and an amount as input. The function first calculates the platform fee using the `calculate_fee()` function, and then calls the Stripe API to charge the user and logs the transaction using the `log_transaction()` function. Finally, it returns the charge ID.

## Irrelevant information was retrieved first

Context was returned, but its top-ranked chunk did not come from the expected source file.

### dependency-03: Which functions depend on the database object?

- Category: **dependency understanding**
- Expected file: `auth.py`
- Top retrieval correct: **no**
- Expected file present anywhere: **yes**
- Answer accuracy: **33.3%**
- Hallucination flag: **no**

#### Question → Retrieved context → LLM response

**Question:** Which functions depend on the database object?

**Retrieved context:**

```
models.py (chunk 0):
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

payment.py (chunk 0):
def process_payment(user_id, amount):
    """Calls the Stripe API to charge a user and logs the transaction."""
    fee = calculate_fee(amount)
    charge = stripe.Charge.create(amount=amount, customer=user_id)
    log_transaction(user_id, amount, fee, charge.id)
    return charge


def calculate_fee(amount, rate=0.03):
    """Returns the platform fee for a given payment amount."""
    return round(amount * rate, 2)


def log_transaction(user_id, amount, fee, charge_id):
    """Writes a record of the payment to the payments table."""
    db.insert("payments", {
        "user_id": user_id,
        "amount": amount,
        "fee": fee,
        "charge_id": charge_id,
    })

auth.py (chunk 0):
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
```

**LLM response:**

The `register_user` and `process_payment` functions in the `payment.py` module depend on the `db` object, which is a database connection. Therefore, these functions have a dependency on the database.

The `login` function in the `auth.py` module depends on the `db` object and the `bcrypt` library. Therefore, these functions have a dependency on the database and the `bcrypt` library.

In summary, the functions `register_user`, `process_payment`, and `login` all depend on the database object.

### refactor-03: How could model creation be separated from persistence?

- Category: **refactoring suggestion**
- Expected file: `models.py`
- Top retrieval correct: **no**
- Expected file present anywhere: **yes**
- Answer accuracy: **66.7%**
- Hallucination flag: **no**

#### Question → Retrieved context → LLM response

**Question:** How could model creation be separated from persistence?

**Retrieved context:**

```
auth.py (chunk 0):
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

models.py (chunk 0):
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

payment.py (chunk 0):
def process_payment(user_id, amount):
    """Calls the Stripe API to charge a user and logs the transaction."""
    fee = calculate_fee(amount)
    charge = stripe.Charge.create(amount=amount, customer=user_id)
    log_transaction(user_id, amount, fee, charge.id)
    return charge


def calculate_fee(amount, rate=0.03):
    """Returns the platform fee for a given payment amount."""
    return round(amount * rate, 2)


def log_transaction(user_id, amount, fee, charge_id):
    """Writes a record of the payment to the payments table."""
    db.insert("payments", {
        "user_id": user_id,
        "amount": amount,
        "fee": fee,
        "charge_id": charge_id,
    })
```

**LLM response:**

It is possible to separate model creation from persistence by using a separate layer of abstraction between the model and the persistence layer. This can be achieved by using a repository pattern, where the repository is responsible for creating and persisting the models, while the models themselves are agnostic to the persistence layer.

For example, in the auth.py file, the `login` function could return a `User` object instead of a session token, and the `register_user` function could create and return a `User` object instead of persisting it directly. This would allow the `login` and `register_user` functions to be used in different contexts, where the persistence layer may vary.

Here is an example of how the `login` function could be modified to return a `User` object instead of a session token:
```
def login(username, password):
    """Checks credentials against the users table and returns a User object."""
    user = find_user(username)
    if user and verify_password(password, user.password_hash):
        return user
    return None
```
And here is an example of how the `register_user`

## Important information was missed

None of the retrieved chunks came from the expected source file.

**No example was observed in this run.** This is reported explicitly rather than inventing a failure case.

## The LLM produced a correct answer

The response contained every expected answer keyword.

### explain-02: How is a payment processed?

- Category: **code explanation**
- Expected file: `payment.py`
- Top retrieval correct: **yes**
- Expected file present anywhere: **yes**
- Answer accuracy: **100.0%**
- Hallucination flag: **no**

#### Question → Retrieved context → LLM response

**Question:** How is a payment processed?

**Retrieved context:**

```
payment.py (chunk 0):
def process_payment(user_id, amount):
    """Calls the Stripe API to charge a user and logs the transaction."""
    fee = calculate_fee(amount)
    charge = stripe.Charge.create(amount=amount, customer=user_id)
    log_transaction(user_id, amount, fee, charge.id)
    return charge


def calculate_fee(amount, rate=0.03):
    """Returns the platform fee for a given payment amount."""
    return round(amount * rate, 2)


def log_transaction(user_id, amount, fee, charge_id):
    """Writes a record of the payment to the payments table."""
    db.insert("payments", {
        "user_id": user_id,
        "amount": amount,
        "fee": fee,
        "charge_id": charge_id,
    })

auth.py (chunk 0):
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

models.py (chunk 0):
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
```

**LLM response:**

A payment is processed by calling the `process_payment()` function, which takes a user ID and an amount as input. The function first calculates the platform fee using the `calculate_fee()` function, and then calls the Stripe API to charge the user and logs the transaction using the `log_transaction()` function. Finally, it returns the charge ID.

### explain-03: What data does User store?

- Category: **code explanation**
- Expected file: `models.py`
- Top retrieval correct: **yes**
- Expected file present anywhere: **yes**
- Answer accuracy: **100.0%**
- Hallucination flag: **no**

#### Question → Retrieved context → LLM response

**Question:** What data does User store?

**Retrieved context:**

```
models.py (chunk 0):
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

payment.py (chunk 0):
def process_payment(user_id, amount):
    """Calls the Stripe API to charge a user and logs the transaction."""
    fee = calculate_fee(amount)
    charge = stripe.Charge.create(amount=amount, customer=user_id)
    log_transaction(user_id, amount, fee, charge.id)
    return charge


def calculate_fee(amount, rate=0.03):
    """Returns the platform fee for a given payment amount."""
    return round(amount * rate, 2)


def log_transaction(user_id, amount, fee, charge_id):
    """Writes a record of the payment to the payments table."""
    db.insert("payments", {
        "user_id": user_id,
        "amount": amount,
        "fee": fee,
        "charge_id": charge_id,
    })

auth.py (chunk 0):
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
```

**LLM response:**

User stores the following data:

* `id`: a unique identifier for the user
* `username`: the username for the user
* `password_hash`: the hashed password for the user
* `created_at`: the timestamp when the user was created

Note: This is based on the information retrieved from the models.py file.

## The LLM hallucinated despite having context

The response made an identifiable function or file claim absent from its retrieved context.

### explain-04: How does create_session_token work?

- Category: **code explanation**
- Expected file: `auth.py`
- Top retrieval correct: **yes**
- Expected file present anywhere: **yes**
- Answer accuracy: **33.3%**
- Hallucination flag: **yes**

#### Question → Retrieved context → LLM response

**Question:** How does create_session_token work?

**Retrieved context:**

```
auth.py (chunk 0):
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

payment.py (chunk 0):
def process_payment(user_id, amount):
    """Calls the Stripe API to charge a user and logs the transaction."""
    fee = calculate_fee(amount)
    charge = stripe.Charge.create(amount=amount, customer=user_id)
    log_transaction(user_id, amount, fee, charge.id)
    return charge


def calculate_fee(amount, rate=0.03):
    """Returns the platform fee for a given payment amount."""
    return round(amount * rate, 2)


def log_transaction(user_id, amount, fee, charge_id):
    """Writes a record of the payment to the payments table."""
    db.insert("payments", {
        "user_id": user_id,
        "amount": amount,
        "fee": fee,
        "charge_id": charge_id,
    })

models.py (chunk 0):
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
```

**LLM response:**

create_session_token is a function that generates a signed session token for an authenticated user. The function takes the user's ID as an argument and returns a signed JWT (JSON Web Token) that contains the user's ID. The JWT is signed with the secret key, which is stored in the SECRET_KEY variable.

The process of generating a session token involves several steps:

1. The function first creates a dictionary that contains the user's ID, which is passed as an argument.
2. The function then uses the jwt.encode function to encode the dictionary as a JWT, which is signed with the secret key.
3. The function returns the signed JWT as the session token.

The signed JWT contains the user's ID and a signature that is generated using the secret key. This signature ensures that the JWT is authentic and has not been tampered with.

When a user sends the session token to the server, the server can use the jwt.decode function to verify the signature and ensure that the JWT is authentic. If the signature is valid, the server can use the user's ID to authenticate the user and grant access

### dependency-01: What external libraries are used for authentication?

- Category: **dependency understanding**
- Expected file: `auth.py`
- Top retrieval correct: **yes**
- Expected file present anywhere: **yes**
- Answer accuracy: **100.0%**
- Hallucination flag: **yes**

#### Question → Retrieved context → LLM response

**Question:** What external libraries are used for authentication?

**Retrieved context:**

```
auth.py (chunk 0):
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

models.py (chunk 0):
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

payment.py (chunk 0):
def process_payment(user_id, amount):
    """Calls the Stripe API to charge a user and logs the transaction."""
    fee = calculate_fee(amount)
    charge = stripe.Charge.create(amount=amount, customer=user_id)
    log_transaction(user_id, amount, fee, charge.id)
    return charge


def calculate_fee(amount, rate=0.03):
    """Returns the platform fee for a given payment amount."""
    return round(amount * rate, 2)


def log_transaction(user_id, amount, fee, charge_id):
    """Writes a record of the payment to the payments table."""
    db.insert("payments", {
        "user_id": user_id,
        "amount": amount,
        "fee": fee,
        "charge_id": charge_id,
    })
```

**LLM response:**

The following external libraries are used for authentication:

1. bcrypt: Used for hashing and verifying passwords.
2. jwt: Used for generating and verifying JSON Web Tokens (JWTs).

## Conclusion

The measured evidence shows that retrieval quality influences which facts are available, but correct retrieval does not guarantee a correct or non-hallucinated response. Conversely, a model can sometimes answer despite a poor top result because another useful chunk is present or because the model already knows a plausible answer. The full Question → Retrieved Context → Response trace must therefore be inspected alongside quantitative retrieval and answer metrics.
