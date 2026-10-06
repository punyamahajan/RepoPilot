from .pricing import calculate_fee


def fee_report(amounts):
    return sum(calculate_fee(amount) for amount in amounts)
