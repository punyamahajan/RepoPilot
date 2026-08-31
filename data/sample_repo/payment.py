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