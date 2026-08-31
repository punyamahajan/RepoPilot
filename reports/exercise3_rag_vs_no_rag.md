# Exercise 3 — RAG vs No-RAG Comparison

Generated: 2026-08-31 15:43

Each question below was sent to the same model (`codellama` via Ollama) twice: once with context retrieved from the vectorstore (RAG), and once with no context at all (baseline). Compare the two responses to see where retrieval improves accuracy and specificity.

---

## Question 1: What does the login function do?

### Retrieved context (RAG)

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

### Response WITH RAG

The `login` function in the `auth.py` chunk of code checks the provided `username` and `password` against the `users` table in the database, and if they match, it returns a session token that can be used to authenticate the user in future requests.

Here's a breakdown of what the function does:

1. It retrieves the user record from the `users` table using the `find_user` function, which looks up a user record by `username`.
2. It checks if the user record exists and if the provided `password` matches the `password_hash` stored in the database for that user.
3. If the password matches, it creates a new session token using the `create_session_token` function.
4. It returns the session token if successful, or `None` otherwise.

The session token is a signed JSON Web Token (JWT) that contains information about the user's authenticated state. It's used to authenticate the user in future requests, and it can be used to retrieve the user's ID, username, and other information from the `users` table.

### Response WITHOUT RAG (baseline)

The login function is a feature in many software programs that allows users to log in to their accounts using their usernames and passwords. When a user logs in, the program grants the user access to the account's resources and allows them to perform actions such as accessing their data, sending messages, or making transactions.

The login function typically involves the following steps:

1. Entering the user's username and password.
2. Verifying the user's credentials by checking them against the program's database.
3. If the credentials are valid, the program grants the user access to the account's resources.
4. If the credentials are invalid, the program displays an error message and the user is not granted access.

The login function is an important security feature that helps protect users' accounts and prevent unauthorized access to their data.

### Notes (fill in manually)

- Was the retrieved context actually relevant? 
- Did RAG produce a more specific / correct answer? 
- Did the no-RAG response hallucinate details? 

---

## Question 2: How is the payment fee calculated?

### Retrieved context (RAG)

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

### Response WITH RAG

The payment fee is calculated using the `calculate_fee` function, which takes the payment amount and a fee rate as arguments. The function returns the platform fee for the given payment amount.

In this case, the fee rate is hardcoded to 0.03, which means that for every payment made, a 3% fee will be charged. The `calculate_fee` function returns the calculated fee amount, which is then used to create a Stripe charge.

So, if a user makes a payment of $100, the platform fee will be $3, and the Stripe charge will be $97.

### Response WITHOUT RAG (baseline)

The payment fee is calculated based on the amount of money that you pay to your bank. The fee is typically a percentage of the amount you transfer, and it varies depending on the bank and the type of account you have.

For example, if you transfer $100 to your bank account, the payment fee might be $5 (5% of $100). This means that you would end up paying $95 for the transfer ($100 - $5).

It's important to check the fees for your specific bank and account type to see exactly how the fee is calculated. You can also try to avoid paying fees by using an online banking service that offers a lower fee structure or by transferring smaller amounts of money.

### Notes (fill in manually)

- Was the retrieved context actually relevant? 
- Did RAG produce a more specific / correct answer? 
- Did the no-RAG response hallucinate details? 

---

## Question 3: What fields does the User class have?

### Retrieved context (RAG)

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
```

### Response WITH RAG

The User class has the following fields:

* id
* username
* password_hash
* created_at

These fields are defined in the constructor for the User class.

### Response WITHOUT RAG (baseline)

The `User` class in the Laravel framework has the following fields:

* `id`: a unique identifier for the user, typically an integer.
* `name`: the user's name, typically a string.
* `email`: the user's email address, typically a string.
* `password`: the user's password, typically a string.
* `remember_token`: a token used to remember the user's login session, typically a string.
* `created_at`: the timestamp when the user was created, typically a datetime object.
* `updated_at`: the timestamp when the user was last updated, typically a datetime object.

These fields are typically defined in the `users` table of the application's database, and are used to store information about the user's identity, email address, and login credentials.

### Notes (fill in manually)

- Was the retrieved context actually relevant? 
- Did RAG produce a more specific / correct answer? 
- Did the no-RAG response hallucinate details? 

---

## Question 4: Which function verifies a password?

### Retrieved context (RAG)

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

### Response WITH RAG

The function that verifies a password is `verify_password` in the `auth.py` file. It takes two arguments: the plaintext password and the hashed password. It returns `True` if the plaintext password matches the hashed password, and `False` otherwise.

### Response WITHOUT RAG (baseline)

There are several functions that can be used to verify a password, depending on the specific requirements of the application or system. Some common functions include:

* `bcrypt()`: This is a password-hashing function that is widely used for storing passwords securely. It is designed to be slow and computationally expensive, making it difficult for attackers to perform a brute-force attack on the password hash.
* `hash()`: This is a general-purpose hashing function that can be used to create a unique hash value for a password. However, it is not as secure as `bcrypt()` and is not recommended for storing passwords.
* `scrypt()`: This is a password-hashing function that is similar to `bcrypt()`, but with a different design. It is also widely used for storing passwords securely.
* `argon2()`: This is a password-hashing function that is designed to be more secure than `bcrypt()` and `scrypt()`. It is also widely used for storing passwords securely.

It is important to note that there are many other functions that can be used to verify passwords, and the specific function used will depend on the requirements of the application or system.

### Notes (fill in manually)

- Was the retrieved context actually relevant? 
- Did RAG produce a more specific / correct answer? 
- Did the no-RAG response hallucinate details? 

---

## Question 5: How does the system log a transaction?

### Retrieved context (RAG)

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

### Response WITH RAG

The system logs a transaction by calling the `log_transaction` function, which writes a record of the payment to the `payments` table. The `log_transaction` function takes four arguments: `user_id`, `amount`, `fee`, and `charge_id`. It then inserts a new record into the `payments` table with these values.

The `log_transaction` function is called from the `process_payment` function, which is the entry point for the payment processing logic. When the `process_payment` function is called, it calculates the fee for the payment using the `calculate_fee` function, and then creates a charge for the payment using the Stripe API. Finally, it logs the transaction using the `log_transaction` function.

The `log_transaction` function is also called from the `register_user` function, which is used to create a new user record in the `users` table. When the `register_user` function is called, it generates a unique ID for the user and creates a new record in the `users` table with the user's username, password hash, and creation time. The `log_transaction` function is also called when the user logs in using the `login` function, which checks the user's credentials against the `users` table and returns a session token if the credentials are valid.

### Response WITHOUT RAG (baseline)

The system logs a transaction by writing information about the transaction to a log file. The log file is typically stored on a separate file system from the transaction data, and is used to track the history of transactions that have been processed by the system.

There are different types of logs that can be used to track transactions, depending on the specific needs of the system. Some common types of logs include:

* Access logs: These logs track all incoming requests to the system and the actions that are taken as a result.
* Error logs: These logs track any errors that occur during the processing of a transaction.
* Audit logs: These logs track all transactions that are processed by the system, including the data that is used in the transaction.
* Security logs: These logs track all security-related events, such as failed login attempts or unauthorized access to sensitive data.

The information that is logged about a transaction can vary depending on the specific needs of the system and the type of log. Some common items that may be logged include:

* The date and time of the transaction
* The user who initiated the transaction
* The data that was used in the transaction
* The result of the transaction
* Any errors that occurred during the transaction

The log file is typically stored in a central location, such as a dedicated log server or a file system that is shared by multiple systems. The log file is typically updated in real-time as the transactions occur, and may be rotated or archived periodically to prevent it from becoming too large.

The log file can be used for a variety of purposes, such as:

* Troubleshooting: The log file can be used to identify errors or issues that occur during the processing of transactions, and to troubleshoot problems as needed.
* Compliance: The log file can be used to track all transactions that are processed by the system, and can be used to demonstrate compliance with regulatory requirements or audit requirements.
* Security: The log file can be used to track all security-related events, such as failed login attempts or unauthorized access to sensitive data.
* Reporting: The log file can be used to generate reports on the transactions that have been processed by the system, such as reports on the number of transactions processed, the amount of data that was used, or the number of errors that occurred.

### Notes (fill in manually)

- Was the retrieved context actually relevant? 
- Did RAG produce a more specific / correct answer? 
- Did the no-RAG response hallucinate details? 

---

