"""Fee calculation used by checkout and reporting."""


def calculate_fee(amount, rate=0.03):
    if amount < 0:
        raise ValueError('Amount must be nonnegative')
    return round(amount * rate, 2)
