from ..registration import submit_registration


def test_registration():
    assert submit_registration('alice', 'example123')['status'] == 201
