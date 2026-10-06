from unittest.mock import Mock, patch

from codeimpact.engine import ai_review


def test_model_output_requires_real_file_and_evidence_ids():
    response = Mock()
    response.json.return_value = {'response': '{"findings":[{"file":"invented.py","risk":"High","reasoning":"x","suggestion":"y","evidence_ids":["unknown"]},{"file":"core.py","risk":"Medium","reasoning":"Changing the fee could affect consumers","suggestion":"Test changed contract","evidence_ids":["e1"],"evidence_quote":"def fee(): return 3"}]}', 'eval_count':42}
    with patch('codeimpact.engine.requests.post', return_value=response):
        review = ai_review('Change fee', [{'id':'e1','file':'core.py','start':1,'end':1,'text':'def fee(): return 3'}])
    assert review['rejected_findings'] == 1
    assert review['findings'][0]['file'] == 'core.py'
    assert review['completion_tokens'] == 42


def test_malformed_model_output_is_not_accepted():
    response = Mock()
    response.json.return_value = {'response':'[]'}
    with patch('codeimpact.engine.requests.post', return_value=response):
        try:
            ai_review('change', [])
        except ValueError:
            pass
        else:
            raise AssertionError('Expected invalid structured output to be rejected')
