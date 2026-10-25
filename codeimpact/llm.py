"""Model providers for CodeImpact: local Ollama or a user-supplied API key.

API keys live only in server memory (or, when the user opts in, in a local
credentials file with owner-only permissions). They are never written to
reports, logs, or responses sent back to the browser.
"""

import json
import os
from pathlib import Path
import re
import threading
import time

import requests


PROVIDERS = {
    'ollama': {'label': 'Local Ollama', 'kind': 'ollama', 'needs_key': False,
               'base_url': os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')},
    'openai': {'label': 'OpenAI', 'kind': 'openai', 'needs_key': True, 'base_url': 'https://api.openai.com/v1'},
    'anthropic': {'label': 'Anthropic Claude', 'kind': 'anthropic', 'needs_key': True, 'base_url': 'https://api.anthropic.com/v1'},
    'gemini': {'label': 'Google Gemini', 'kind': 'gemini', 'needs_key': True,
               'base_url': 'https://generativelanguage.googleapis.com/v1beta'},
    'groq': {'label': 'Groq', 'kind': 'openai', 'needs_key': True, 'base_url': 'https://api.groq.com/openai/v1'},
    'openrouter': {'label': 'OpenRouter', 'kind': 'openai', 'needs_key': True, 'base_url': 'https://openrouter.ai/api/v1'},
    'custom': {'label': 'Custom (OpenAI-compatible)', 'kind': 'openai', 'needs_key': False, 'base_url': ''},
}
ENV_KEYS = {'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY', 'gemini': 'GEMINI_API_KEY',
            'groq': 'GROQ_API_KEY', 'openrouter': 'OPENROUTER_API_KEY', 'custom': 'CUSTOM_LLM_API_KEY'}
MODEL_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,159}')
DEFAULT_MODEL = os.getenv('CODEIMPACT_DEFAULT_MODEL', 'codellama')


class LLMError(Exception):
    """A provider call failed; the message is safe to show (it never contains the key)."""


def mask(key):
    return ('•••• ' + key[-4:]) if key and len(key) > 8 else ('••••' if key else '')


def validate_model(model):
    if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model):
        raise ValueError('Model names may contain letters, digits, and . _ : / @ + - only.')
    return model


def validate_config(config):
    provider = config.get('provider', 'ollama')
    if provider not in PROVIDERS:
        raise ValueError('Unknown model provider.')
    base_url = (config.get('base_url') or '').strip().rstrip('/')
    if base_url and not re.fullmatch(r'https?://[^\s]+', base_url):
        raise ValueError('Base URL must start with http:// or https://.')
    if provider == 'custom' and not base_url:
        raise ValueError('A custom provider needs a base URL.')
    model = validate_model(config.get('model') or DEFAULT_MODEL)
    api_key = (config.get('api_key') or '').strip()
    if len(api_key) > 512 or any(c.isspace() for c in api_key):
        raise ValueError('That API key does not look valid.')
    return {'provider': provider, 'model': model, 'base_url': base_url, 'api_key': api_key}


class CredentialStore:
    """Per-browser-session model settings, with an optional machine-local default."""

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.sessions = {}
        self.saved = self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return validate_config(data)
        except Exception:
            return None

    def get(self, session_id):
        with self.lock:
            config = self.sessions.get(session_id) or self.saved
            if config is None:
                config = {'provider': 'ollama', 'model': DEFAULT_MODEL, 'base_url': '', 'api_key': ''}
            config = dict(config)
        if not config['api_key']:
            config['api_key'] = os.getenv(ENV_KEYS.get(config['provider'], ''), '')
        return config

    def set(self, session_id, config, remember=False):
        config = validate_config(config)
        with self.lock:
            previous = self.sessions.get(session_id) or self.saved or {}
            # An empty key field keeps the stored key for the same provider.
            if not config['api_key'] and previous.get('provider') == config['provider']:
                config['api_key'] = previous.get('api_key', '')
            self.sessions[session_id] = config
            if remember:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.path.with_suffix('.tmp')
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                    json.dump(config, handle)
                temporary.replace(self.path)
                self.saved = dict(config)
        return config

    def clear(self, session_id):
        with self.lock:
            self.sessions.pop(session_id, None)
            self.saved = None
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

    def public(self, session_id):
        config = self.get(session_id)
        provider = PROVIDERS[config['provider']]
        return {'provider': config['provider'], 'provider_label': provider['label'], 'model': config['model'],
                'base_url': config['base_url'] or provider['base_url'], 'has_key': bool(config['api_key']),
                'key_hint': mask(config['api_key']), 'needs_key': provider['needs_key'],
                'remembered': self.saved is not None}


def base_url(config):
    return (config.get('base_url') or PROVIDERS[config['provider']]['base_url']).rstrip('/')


def _require_key(config):
    if PROVIDERS[config['provider']]['needs_key'] and not config.get('api_key'):
        raise LLMError(f"Add an API key for {PROVIDERS[config['provider']]['label']} in Model settings.")


def _post(url, *, headers=None, payload=None, timeout=240, key=''):
    try:
        response = requests.post(url, headers=headers or {}, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise LLMError(_scrub(f'Could not reach the model provider: {exc}', key)) from None
    if response.status_code >= 400:
        try:
            detail = response.json()
            detail = detail.get('error', detail)
            if isinstance(detail, dict):
                detail = detail.get('message', detail)
        except ValueError:
            detail = response.text
        raise LLMError(_scrub(f'Provider error {response.status_code}: {str(detail)[:400]}', key))
    return response.json()


def _get(url, *, headers=None, timeout=20, key=''):
    try:
        response = requests.get(url, headers=headers or {}, timeout=timeout)
    except requests.RequestException as exc:
        raise LLMError(_scrub(f'Could not reach the model provider: {exc}', key)) from None
    if response.status_code >= 400:
        raise LLMError(_scrub(f'Provider error {response.status_code}: {response.text[:300]}', key))
    return response.json()


def _scrub(message, key):
    return message.replace(key, mask(key)) if key else message


def generate(config, prompt, *, json_mode=False, max_tokens=512, temperature=0.0, timeout=None):
    """Return {'text', 'prompt_tokens', 'completion_tokens', 'latency_seconds'} for one prompt."""
    _require_key(config)
    kind = PROVIDERS[config['provider']]['kind']
    key, model, root = config.get('api_key', ''), config['model'], base_url(config)
    timeout = timeout or int(os.getenv('CODEIMPACT_LLM_TIMEOUT', '240'))
    started = time.perf_counter()
    if kind == 'ollama':
        payload = {'model': model, 'prompt': prompt, 'stream': False,
                   'options': {'temperature': temperature, 'num_predict': max_tokens, 'num_ctx': 8192}}
        if json_mode:
            payload['format'] = 'json'
        data = _post(root + '/api/generate', payload=payload, timeout=timeout)
        text, prompt_tokens, completion_tokens = data.get('response', ''), data.get('prompt_eval_count', 0), data.get('eval_count', 0)
    elif kind == 'openai':
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        payload = {'model': model, 'messages': [{'role': 'user', 'content': prompt}],
                   'temperature': temperature, 'max_tokens': max_tokens}
        if json_mode:
            payload['response_format'] = {'type': 'json_object'}
        try:
            data = _post(root + '/chat/completions', headers=headers, payload=payload, timeout=timeout, key=key)
        except LLMError as exc:
            # Some compatible servers and newer models reject json mode or max_tokens.
            if 'response_format' not in str(exc) and 'max_tokens' not in str(exc):
                raise
            payload.pop('response_format', None)
            payload['max_completion_tokens'] = payload.pop('max_tokens')
            payload.pop('temperature', None)
            data = _post(root + '/chat/completions', headers=headers, payload=payload, timeout=timeout, key=key)
        choice = (data.get('choices') or [{}])[0]
        text = (choice.get('message') or {}).get('content') or ''
        usage = data.get('usage') or {}
        prompt_tokens, completion_tokens = usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0)
    elif kind == 'anthropic':
        headers = {'x-api-key': key, 'anthropic-version': '2023-06-01'}
        data = _post(root + '/messages', headers=headers, timeout=timeout, key=key, payload={
            'model': model, 'max_tokens': max_tokens, 'temperature': temperature,
            'messages': [{'role': 'user', 'content': prompt}]})
        text = ''.join(block.get('text', '') for block in data.get('content', []) if block.get('type') == 'text')
        usage = data.get('usage') or {}
        prompt_tokens, completion_tokens = usage.get('input_tokens', 0), usage.get('output_tokens', 0)
    else:  # gemini
        generation = {'temperature': temperature, 'maxOutputTokens': max_tokens}
        if json_mode:
            generation['responseMimeType'] = 'application/json'
        data = _post(f'{root}/models/{model}:generateContent', headers={'x-goog-api-key': key}, timeout=timeout, key=key,
                     payload={'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': generation})
        parts = ((data.get('candidates') or [{}])[0].get('content') or {}).get('parts') or []
        text = ''.join(part.get('text', '') for part in parts)
        usage = data.get('usageMetadata') or {}
        prompt_tokens, completion_tokens = usage.get('promptTokenCount', 0), usage.get('candidatesTokenCount', 0)
    return {'text': text.strip(), 'prompt_tokens': int(prompt_tokens or 0), 'completion_tokens': int(completion_tokens or 0),
            'latency_seconds': round(time.perf_counter() - started, 2)}


def list_models(config):
    """Return the model ids this provider and key can access."""
    _require_key(config)
    kind = PROVIDERS[config['provider']]['kind']
    key, root = config.get('api_key', ''), base_url(config)
    if kind == 'ollama':
        data = _get(root + '/api/tags')
        names = [m.get('name', '') for m in data.get('models', [])]
    elif kind == 'openai':
        data = _get(root + '/models', headers={'Authorization': f'Bearer {key}'} if key else {}, key=key)
        names = [m.get('id', '') for m in data.get('data', [])]
    elif kind == 'anthropic':
        data = _get(root + '/models?limit=100', headers={'x-api-key': key, 'anthropic-version': '2023-06-01'}, key=key)
        names = [m.get('id', '') for m in data.get('data', [])]
    else:
        data = _get(root + '/models?pageSize=200', headers={'x-goog-api-key': key}, key=key)
        names = [m.get('name', '').removeprefix('models/') for m in data.get('models', [])
                 if 'generateContent' in m.get('supportedGenerationMethods', [])]
    return sorted({n for n in names if n and MODEL_PATTERN.fullmatch(n)})


def extract_json(text):
    """Parse a JSON object from a reply that may wrap it in prose or a code fence."""
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        pass
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text or '', re.S)
    if match:
        try:
            return json.loads(match[1])
        except ValueError:
            pass
    start, end = (text or '').find('{'), (text or '').rfind('}')
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except ValueError:
            pass
    raise ValueError('The model did not return valid JSON.')
