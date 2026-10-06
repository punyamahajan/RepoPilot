from ..checkout import checkout_total


def test_checkout():
    assert checkout_total(100) == 103
