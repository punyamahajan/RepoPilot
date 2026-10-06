from ..reset import reset_password


def test_reset():
    assert reset_password('example123')
