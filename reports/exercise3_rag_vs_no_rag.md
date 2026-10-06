# Exercise 3 — RAG vs No-RAG Comparison

Generated: 2026-09-17 03:59

Each question below was sent to the same model (`codellama` via Ollama) twice: once with context retrieved from the vectorstore (RAG), and once with no context at all (baseline). Compare the two responses to see where retrieval improves accuracy and specificity.

---

## Quantitative summary

| Measure | RAG | No-RAG baseline |
|---|---:|---:|
| Mean expected-keyword accuracy | 83.3% | 10.0% |
| Relevant top retrieval / questions | 5/5 | n/a |
| Contextual hallucination / ungrounded-claim flags | 0/5 | 3/5 |

RAG improved expected-keyword coverage for **5/5** questions, matched the baseline for **0/5**, and was worse for **0/5**. This evidence separates retrieval quality from answer quality: relevant context can improve grounding, but it does not guarantee that the model will use every relevant fact.

## Per-question evidence

## Question 1: What does the login function do?

- Top retrieval came from the expected file: **yes**
- RAG accuracy: **100.0%**
- No-RAG accuracy: **0.0%**
- RAG contextual hallucination flag: **no**
- No-RAG ungrounded-claim flag: **yes**

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

The login function in the repository evidence is defined in the `auth.py` file. It takes in two arguments, `username` and `password`, and it is used to check the credentials of a user against the users table in the database. If the user's credentials are valid, the function returns a session token. If the user's credentials are not valid, the function returns None.

The login function uses the `find_user` function to look up a user record by username in the users table, and then it verifies the password using the `verify_password` function. If the password is correct, the function creates a session token using the `create_session_token` function, which generates a signed session token for the authenticated user.

Overall, the login function is responsible for authenticating users and creating a session token for them.

### Response WITHOUT RAG (baseline)

The `login()` function in Node.js is used to authenticate a user with a specific username and password. It is typically used for authentication purposes in web applications, where the user needs to log in to access protected resources.

The `login()` function takes two arguments: the first is the username, and the second is the password. It returns a `Promise` object that resolves with a boolean value indicating whether the login was successful or not. If the login is successful, the promise resolves with `true`, otherwise it resolves with `false`.

Here is an example of how you might use the `login()` function:
```
const username = 'user1';
const password = 'password';

login(username, password).then((isLoggedIn) => {
  if (isLoggedIn) {
    console.log('Login successful');
  } else {
    console.log('Login failed');
  }
});
```
In this example, the `login()` function is called with the username and password as arguments, and the promise is used to handle the result of the login attempt. If the login is successful, the promise resolves with `true`, and the user is logged in. If the login fails, the promise resolves with `false`, and the user is not logged in.

### Evidence-based interpretation

The retrieved top chunk was relevant. Adding it improved expected-keyword coverage by 100.0%. The grounded response did not trigger the contextual hallucination heuristic, while the baseline contained identifiable code claims that could not be verified without supplied context.

---

## Question 2: How is the payment fee calculated?

- Top retrieval came from the expected file: **yes**
- RAG accuracy: **100.0%**
- No-RAG accuracy: **0.0%**
- RAG contextual hallucination flag: **no**
- No-RAG ungrounded-claim flag: **no**

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

The payment fee is calculated by the `calculate_fee` function in the `payment.py` file. This function takes the amount of the payment as an argument and returns the platform fee as a rounded value with two decimal places. The platform fee is calculated as a percentage of the payment amount, using the `rate` parameter, which is set to 0.03 by default.

Here is an example of how to call the `calculate_fee` function:
```
amount = 100
fee = calculate_fee(amount)
print(f"The fee for this payment is {fee}")
```
This would output:
```
The fee for this payment is 3.00
```

### Response WITHOUT RAG (baseline)

The payment fee is calculated based on the value of the item being purchased. The fee is typically a flat rate per transaction, and it may be charged on top of the total price of the item, including any taxes or shipping costs. The specific calculation of the payment fee will depend on the payment gateway and the merchant's policies. Some payment gateways may also offer a discount or rebate for certain types of purchases, such as those made with a credit card or a certain amount of money. It's always a good idea to check the payment gateway's website or contact them directly to understand their fee structure and any potential discounts or rebates they may offer.

### Evidence-based interpretation

The retrieved top chunk was relevant. Adding it improved expected-keyword coverage by 100.0%. The grounded response did not trigger the contextual hallucination heuristic, while the baseline did not contain identifiable code claims that could not be verified without supplied context.

---

## Question 3: What fields does the User class have?

- Top retrieval came from the expected file: **yes**
- RAG accuracy: **100.0%**
- No-RAG accuracy: **50.0%**
- RAG contextual hallucination flag: **no**
- No-RAG ungrounded-claim flag: **yes**

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

* `id`
* `username`
* `password_hash`
* `created_at`

### Response WITHOUT RAG (baseline)

The `User` class in the Django authentication system has the following fields:

* `id`: a unique identifier for the user (integer)
* `password`: the user's password (string)
* `last_login`: the date and time of the user's last login (datetime)
* `is_superuser`: a boolean indicating whether the user is a superuser (integer)
* `username`: the user's username (string)
* `first_name`: the user's first name (string)
* `last_name`: the user's last name (string)
* `email`: the user's email address (string)
* `is_staff`: a boolean indicating whether the user is a staff member (integer)
* `is_active`: a boolean indicating whether the user is active (integer)
* `date_joined`: the date and time the user was created (datetime)

Note that these fields may vary depending on the specific implementation of the `User` class in your Django project.

### Evidence-based interpretation

The retrieved top chunk was relevant. Adding it improved expected-keyword coverage by 50.0%. The grounded response did not trigger the contextual hallucination heuristic, while the baseline contained identifiable code claims that could not be verified without supplied context.

---

## Question 4: Which function verifies a password?

- Top retrieval came from the expected file: **yes**
- RAG accuracy: **50.0%**
- No-RAG accuracy: **0.0%**
- RAG contextual hallucination flag: **no**
- No-RAG ungrounded-claim flag: **yes**

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

The function that verifies a password is `verify_password` in the `auth.py` file.

### Response WITHOUT RAG (baseline)

The `password_verify()` function in PHP is used to verify a password. This function takes the plaintext password as an argument and compares it to the hashed password stored in the database. If the two match, it returns `true`. If they don't match, it returns `false`.

Here is an example of how to use the `password_verify()` function:
```
$password = "password";
$hashed_password = "$2y$10$8Zl5aq3.Ls3j8NdCxVp65u4vYGUXi7ZFx.YW3j7gN2/E7";

if (password_verify($password, $hashed_password)) {
    echo "Password is valid.";
} else {
    echo "Password is invalid.";
}
```
In this example, the plaintext password "password" is passed to the `password_verify()` function along with the hashed password stored in the database. If the two match, the function returns `true`, and the code inside the `if` statement is executed. If they don't match, the function returns `false`, and the code inside the `else` statement is executed.

It's important to note that the `password_verify()` function is a secure way to verify passwords, as it uses a cryptographic hash function to generate a hash of the password and compare it to the stored hash. This makes it much more difficult for an attacker to crack the password using brute force methods.

### Evidence-based interpretation

The retrieved top chunk was relevant. Adding it improved expected-keyword coverage by 50.0%. The grounded response did not trigger the contextual hallucination heuristic, while the baseline contained identifiable code claims that could not be verified without supplied context.

---

## Question 5: How does the system log a transaction?

- Top retrieval came from the expected file: **yes**
- RAG accuracy: **66.7%**
- No-RAG accuracy: **0.0%**
- RAG contextual hallucination flag: **no**
- No-RAG ungrounded-claim flag: **no**

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

The system logs a transaction by calling the `log_transaction` function, which writes a record of the payment to the `payments` table.

### Response WITHOUT RAG (baseline)

The system logs a transaction by writing information about the transaction to a database or a log file. The information that is written to the log can vary depending on the specific system and the type of transaction that is being logged.

For example, in a financial system, the log might include the date and time of the transaction, the amount of the transaction, the source and destination of the funds, and any other relevant information. The log is typically used to audit the system and ensure that transactions are accurate and complete.

In a web application, the log might include the user's IP address, the date and time of the transaction, the URL of the page that was accessed, and any other relevant information that is relevant to the transaction.

In general, the log is a record of all the transactions that have taken place in the system, and it can be used to track the system's activity and ensure that it is functioning correctly.

### Evidence-based interpretation

The retrieved top chunk was relevant. Adding it improved expected-keyword coverage by 66.7%. The grounded response did not trigger the contextual hallucination heuristic, while the baseline did not contain identifiable code claims that could not be verified without supplied context.

---

## Conclusion

Across this controlled comparison, RAG achieved 83.3% mean keyword accuracy versus 10.0% without retrieval. The top result came from the expected file for 5/5 questions. These results show the complete relationship: retrieval determines available context, context constrains the model, and the model can still omit facts or make unsupported claims. RAG therefore improves the evidence available to the LLM but is not, by itself, a guarantee of correctness.
