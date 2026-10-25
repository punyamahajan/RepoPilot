import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from codeimpact import llm, remote
from codeimpact.graph import build_graph, propagate
from dashboard.app import CREDENTIALS, app


def reply(payload, status=200):
    response = Mock(status_code=status)
    response.json.return_value = payload
    response.text = json.dumps(payload)
    return response


class ProviderTests(unittest.TestCase):
    def test_config_validation_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            llm.validate_config({'provider': 'nope', 'model': 'x'})
        with self.assertRaises(ValueError):
            llm.validate_config({'provider': 'openai', 'model': 'gpt; rm -rf /'})
        with self.assertRaises(ValueError):
            llm.validate_config({'provider': 'custom', 'model': 'm'})
        config = llm.validate_config({'provider': 'openrouter', 'model': 'meta-llama/llama-3.1-8b-instruct:free',
                                      'api_key': ' sk-test-123456 '})
        self.assertEqual(config['api_key'], 'sk-test-123456')

    def test_store_never_exposes_key_and_remembers_with_owner_only_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'credentials.json'
            store = llm.CredentialStore(path)
            store.set('s1', {'provider': 'openai', 'model': 'gpt-4o-mini', 'api_key': 'sk-secret-abcdef1234'}, remember=True)
            public = store.public('s1')
            self.assertNotIn('sk-secret-abcdef1234', json.dumps(public))
            self.assertEqual(public['key_hint'], '•••• 1234')
            self.assertTrue(public['has_key'])
            if os.name != 'nt':
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            # A blank key keeps the stored key for the same provider.
            store.set('s1', {'provider': 'openai', 'model': 'gpt-4.1', 'api_key': ''})
            self.assertEqual(store.get('s1')['api_key'], 'sk-secret-abcdef1234')
            self.assertEqual(llm.CredentialStore(path).get('other')['model'], 'gpt-4o-mini')
            store.clear('s1')
            self.assertFalse(path.exists())
            self.assertEqual(store.get('s1')['provider'], 'ollama')

    def test_generate_supports_each_provider_shape(self):
        cases = [
            ({'provider': 'openai', 'model': 'gpt-4o-mini', 'api_key': 'k' * 12, 'base_url': ''},
             {'choices': [{'message': {'content': 'hi'}}], 'usage': {'prompt_tokens': 3, 'completion_tokens': 1}},
             'https://api.openai.com/v1/chat/completions'),
            ({'provider': 'anthropic', 'model': 'claude-sonnet-4-5', 'api_key': 'k' * 12, 'base_url': ''},
             {'content': [{'type': 'text', 'text': 'hi'}], 'usage': {'input_tokens': 3, 'output_tokens': 1}},
             'https://api.anthropic.com/v1/messages'),
            ({'provider': 'gemini', 'model': 'gemini-2.5-flash', 'api_key': 'k' * 12, 'base_url': ''},
             {'candidates': [{'content': {'parts': [{'text': 'hi'}]}}],
              'usageMetadata': {'promptTokenCount': 3, 'candidatesTokenCount': 1}},
             'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'),
            ({'provider': 'ollama', 'model': 'codellama', 'api_key': '', 'base_url': 'http://ollama:11434'},
             {'response': 'hi', 'prompt_eval_count': 3, 'eval_count': 1}, 'http://ollama:11434/api/generate'),
        ]
        for config, payload, url in cases:
            with self.subTest(provider=config['provider']), patch('codeimpact.llm.requests.post', return_value=reply(payload)) as post:
                result = llm.generate(config, 'question', json_mode=True)
                self.assertEqual(post.call_args.args[0], url)
                self.assertEqual((result['text'], result['prompt_tokens'], result['completion_tokens']), ('hi', 3, 1))

    def test_missing_key_and_provider_errors_never_leak_the_key(self):
        with self.assertRaises(llm.LLMError):
            llm.generate({'provider': 'groq', 'model': 'llama', 'api_key': '', 'base_url': ''}, 'q')
        key = 'sk-leaky-key-987654'
        error = reply({'error': {'message': f'Incorrect API key provided: {key}'}}, status=401)
        with patch('codeimpact.llm.requests.post', return_value=error):
            with self.assertRaises(llm.LLMError) as caught:
                llm.generate({'provider': 'openai', 'model': 'gpt-4o', 'api_key': key, 'base_url': ''}, 'q')
        self.assertNotIn(key, str(caught.exception))
        self.assertIn('401', str(caught.exception))

    def test_list_models_and_json_extraction(self):
        with patch('codeimpact.llm.requests.get', return_value=reply({'data': [{'id': 'gpt-4o'}, {'id': 'gpt-4o-mini'}]})):
            models = llm.list_models({'provider': 'openai', 'model': 'x', 'api_key': 'k' * 12, 'base_url': ''})
        self.assertEqual(models, ['gpt-4o', 'gpt-4o-mini'])
        self.assertEqual(llm.extract_json('Here:\n```json\n{"findings": []}\n```'), {'findings': []})
        with self.assertRaises(ValueError):
            llm.extract_json('no json here')


class DashboardProviderTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.get('/')

    def tearDown(self):
        with CREDENTIALS.lock:
            CREDENTIALS.sessions.clear()

    def test_saved_key_is_masked_and_used_for_questions(self):
        response = self.client.post('/api/llm/config', json={'provider': 'openai', 'model': 'gpt-4o-mini',
                                                              'api_key': 'sk-dashboard-secret-42'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('sk-dashboard-secret-42', response.get_data(as_text=True))
        self.assertTrue(response.get_json()['has_key'])
        generated = {'text': 'Fee is computed in pricing.py', 'prompt_tokens': 5, 'completion_tokens': 6, 'latency_seconds': 0.1}
        with patch('dashboard.app.llm.generate', return_value=generated) as generate:
            answer = self.client.post('/api/ask', json={'question': 'How is the payment fee calculated?',
                                                        'model': 'active', 'repository': 'data/codeimpact_demo'})
        self.assertEqual(answer.status_code, 200)
        data = answer.get_json()
        self.assertEqual(data['model'], 'gpt-4o-mini')
        self.assertEqual(data['results'][0]['provider'], 'openai')
        self.assertEqual(generate.call_args.args[0]['api_key'], 'sk-dashboard-secret-42')
        self.assertEqual(len(data['results']), 1)

    def test_benchmark_models_still_use_ollama_when_comparing(self):
        self.client.post('/api/llm/config', json={'provider': 'openai', 'model': 'gpt-4o-mini', 'api_key': 'sk-x-12345678'})
        generated = {'text': 'answer', 'prompt_tokens': 1, 'completion_tokens': 1, 'latency_seconds': 0.1}
        with patch('dashboard.app.llm.generate', return_value=generated) as generate:
            data = self.client.post('/api/ask', json={'question': 'How is the payment fee calculated?', 'model': 'all',
                                                      'repository': 'data/codeimpact_demo'}).get_json()
        self.assertEqual([r['model'] for r in data['results']], ['codellama', 'starcoder2', 'qwen2.5-coder'])
        self.assertEqual({call.args[0]['provider'] for call in generate.call_args_list}, {'ollama'})

    def test_cross_origin_writes_are_blocked(self):
        response = self.client.post('/api/llm/config', json={'provider': 'ollama', 'model': 'codellama'},
                                    headers={'Origin': 'https://evil.example'})
        self.assertEqual(response.status_code, 403)

    def test_invalid_model_name_is_rejected(self):
        response = self.client.post('/api/ask', json={'question': 'q', 'model': 'bad model name'})
        self.assertEqual(response.status_code, 400)


class RemoteRepositoryTests(unittest.TestCase):
    def test_parse_url_accepts_web_urls_and_branches(self):
        self.assertEqual(remote.parse_url('https://github.com/punyamahajan/Margdarshak'),
                         ('https://github.com/punyamahajan/Margdarshak.git', 'punyamahajan', 'Margdarshak', None))
        self.assertEqual(remote.parse_url('github.com/owner/repo/tree/feature/x')[3], 'feature/x')
        self.assertEqual(remote.parse_url('https://gitlab.com/group/proj/-/tree/dev')[3], 'dev')

    def test_parse_url_rejects_unsafe_urls(self):
        for url in ('http://github.com/a/b', 'https://evil.example/a/b', 'git@github.com:a/b.git',
                    'https://user:pass@github.com/a/b', 'https://github.com/a', 'https://github.com/a/b/tree/--upload-pack=x',
                    'https://github.com/../b'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                remote.parse_url(url)

    def test_dashboard_rejects_bad_remote_url(self):
        response = app.test_client().post('/api/repositories/remote', json={'url': 'https://evil.example/a/b'})
        self.assertEqual(response.status_code, 400)


class MonorepoGraphTests(unittest.TestCase):
    def test_absolute_imports_resolve_inside_project_subfolders(self):
        files = {
            'backend/app/__init__.py': '',
            'backend/app/models/__init__.py': '',
            'backend/app/models/ticket.py': 'class Ticket: pass\n',
            'backend/app/services/tickets.py': 'from app.models.ticket import Ticket\n\ndef open_ticket():\n    return Ticket()\n',
            'backend/tests/test_tickets.py': 'from app.services.tickets import open_ticket\n',
        }
        graph = build_graph(files)
        paths = propagate(graph, ['backend/app/models/ticket.py'])
        self.assertIn('backend/app/services/tickets.py', paths)
        self.assertIn('backend/tests/test_tickets.py', paths)


if __name__ == '__main__':
    unittest.main()
