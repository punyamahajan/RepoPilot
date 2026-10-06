from ..auth import validate_password


def test_password_policy():
    assert validate_password('example123')
    assert not validate_password('short')
