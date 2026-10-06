from ..reporting import fee_report


def test_reporting():
    assert fee_report([100, 200]) == 9
