from .pricing import calculate_fee


def checkout_total(amount):
    return amount + calculate_fee(amount)
