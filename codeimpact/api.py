"""Local FastAPI service: jobs, persisted reports, repository browsing, and watcher."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .engine import analyze, markdown_report
from .graph import build_graph
from .repository import snapshot


ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.getenv('CODEIMPACT_STATE_DIR', str(ROOT / '.codeimpact'))).resolve()
ALLOWED_ROOT = Path(os.getenv('CODEIMPACT_REPO_ROOT', str(ROOT))).resolve()
FRONTEND = Path(os.getenv('CODEIMPACT_FRONTEND', str(ROOT / 'codeimpact/frontend/dist')))


class AnalysisRequest(BaseModel):
    repository: str = '.'
    description: str = Field(default='', max_length=20000)
    diff: str = Field(default='', max_length=500000)
    changed_files: list[str] = Field(default_factory=list, max_length=200)
    use_git: bool = False
    base: str = Field(default='HEAD', max_length=160)
    semantic: bool = True
    use_llm: bool = True
    model: str = 'codellama'


class WatchRequest(BaseModel):
    repository: str = '.'
    enabled: bool
    semantic: bool = True
    use_llm: bool = False


def resolve_repository(value):
    path = (ALLOWED_ROOT / value).resolve()
    if not path.is_relative_to(ALLOWED_ROOT) or not path.is_dir():
        raise ValueError('Choose an existing directory inside the configured repository root.')
    return path


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


class Service:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='codeimpact')
        self.lock = threading.RLock()
        self.jobs = {}
        self.stopping = threading.Event()
        self.watch = {'enabled': False, 'repository': '.', 'last_job': None}
        self.last_fingerprint = None
        self.pending_fingerprint = None
        self.watcher = threading.Thread(target=self.watch_loop, daemon=True)

    def submit(self, request, trigger='manual'):
        root = resolve_repository(request.repository)
        job_id = uuid.uuid4().hex
        with self.lock:
            if sum(j['status'] in {'queued', 'running'} for j in self.jobs.values()) >= 4:
                raise ValueError('Analysis queue is full. Wait for an active job to finish.')
            self.jobs[job_id] = {'id': job_id, 'status': 'queued', 'message': 'Waiting for analysis',
                                 'trigger': trigger, 'created_at': datetime.now(timezone.utc).isoformat()}
            # Keep bounded in-memory history; completed reports are retained on disk.
            if len(self.jobs) > 100:
                oldest = next((k for k, j in self.jobs.items() if j['status'] not in {'queued', 'running'}), None)
                if oldest:
                    del self.jobs[oldest]
        self.executor.submit(self.run, job_id, root, request)
        return dict(self.jobs[job_id])

    def run(self, job_id, root, request):
        def update(message):
            with self.lock:
                self.jobs[job_id].update(status='running', message=message)
        try:
            arguments = request.model_dump(exclude={'repository'})
            report = analyze(root, STATE, progress=update, **arguments)
            report['trigger'] = self.jobs[job_id]['trigger']
            atomic_json(STATE / 'reports' / (report['id'] + '.json'), report)
            with self.lock:
                self.jobs[job_id].update(status='completed', message='Report ready', report_id=report['id'])
        except Exception as exc:
            with self.lock:
                self.jobs[job_id].update(status='failed', message=str(exc)[:1200])

    def watch_loop(self):
        while not self.stopping.wait(5):
            with self.lock:
                config = dict(self.watch)
                busy = any(j['status'] in {'queued', 'running'} for j in self.jobs.values())
            if not config['enabled'] or busy:
                continue
            try:
                fingerprint = snapshot(resolve_repository(config['repository']))['fingerprint']
                with self.lock:
                    if config != self.watch:
                        continue
                    if self.last_fingerprint is None:
                        self.last_fingerprint = fingerprint
                    elif fingerprint != self.last_fingerprint:
                        # Wait for two identical observations to debounce editor saves.
                        if self.pending_fingerprint != fingerprint:
                            self.pending_fingerprint = fingerprint
                            continue
                        request = AnalysisRequest(repository=config['repository'], use_git=True,
                                                  semantic=config.get('semantic', True),
                                                  use_llm=config.get('use_llm', False))
                        job = self.submit(request, 'watcher')
                        self.watch['last_job'] = job['id']
                        self.last_fingerprint = fingerprint
                        self.pending_fingerprint = None
                        self.watch.pop('error', None)
            except Exception as exc:
                with self.lock:
                    self.watch['error'] = str(exc)[:400]


service = Service()


@asynccontextmanager
async def lifespan(app):
    STATE.mkdir(parents=True, exist_ok=True)
    service.watcher.start()
    yield
    service.stopping.set()
    service.executor.shutdown(wait=False, cancel_futures=True)


app = FastAPI(title='CodeImpact AI', version='1.0.0', lifespan=lifespan)


@app.middleware('http')
async def local_write_protection(request, call_next):
    # Prevent a random website from submitting local repository jobs via the browser.
    from urllib.parse import urlsplit
    origin = request.headers.get('origin')
    if request.method not in {'GET', 'HEAD', 'OPTIONS'} and origin:
        if urlsplit(origin).netloc != request.headers.get('host'):
            return PlainTextResponse('Cross-origin writes are disabled.', status_code=403)
    return await call_next(request)


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'codeimpact', 'repository_root': str(ALLOWED_ROOT)}


@app.get('/api/repository')
def repository_info(repository: str = '.'):
    try:
        root = resolve_repository(repository)
        data = snapshot(root)
        graph = build_graph(data['files'])
        return {'root': str(root), 'fingerprint': data['fingerprint'],
                'files': list(graph['nodes'].values()), 'edges': len(graph['edges']),
                'skipped': data['skipped'], 'warnings': graph['warnings']}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post('/api/analyses', status_code=202)
def create_analysis(request: AnalysisRequest):
    try:
        if not (request.description.strip() or request.diff.strip() or request.changed_files or request.use_git):
            raise ValueError('Provide a change description, diff, file, or select working-tree changes.')
        return service.submit(request)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get('/api/jobs')
def jobs():
    with service.lock:
        return list(reversed(list(service.jobs.values())))


@app.get('/api/jobs/{job_id}')
def get_job(job_id: str):
    with service.lock:
        if job_id not in service.jobs:
            raise HTTPException(404, 'Job not found (jobs are reset on service restart).')
        return dict(service.jobs[job_id])


@app.get('/api/reports')
def reports():
    result = []
    for path in sorted((STATE / 'reports').glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:100]:
        data = json.loads(path.read_text(encoding='utf-8'))
        result.append({k: data.get(k) for k in ('id', 'created_at', 'summary', 'risk', 'repository', 'trigger')})
    return result


def read_report(report_id):
    if not re_full_id(report_id):
        raise HTTPException(404, 'Report not found.')
    path = STATE / 'reports' / (report_id + '.json')
    if not path.exists():
        raise HTTPException(404, 'Report not found.')
    return json.loads(path.read_text(encoding='utf-8'))


def re_full_id(value):
    import re
    return re.fullmatch(r'[a-f0-9]{32}', value)


@app.get('/api/reports/{report_id}')
def report_json(report_id: str):
    return read_report(report_id)


@app.get('/api/reports/{report_id}/markdown', response_class=PlainTextResponse)
def report_markdown(report_id: str):
    return PlainTextResponse(markdown_report(read_report(report_id)),
                             headers={'Content-Disposition': f'attachment; filename="codeimpact-{report_id}.md"'})


@app.get('/api/watch')
def watch_status():
    with service.lock:
        return dict(service.watch)


@app.post('/api/watch')
def configure_watch(request: WatchRequest):
    try:
        root = resolve_repository(request.repository)
        if request.enabled:
            from .repository import resolve_ref
            resolve_ref(root, 'HEAD')
        fingerprint = snapshot(root)['fingerprint'] if request.enabled else None
        with service.lock:
            service.watch = {**request.model_dump(), 'last_job': None}
            service.last_fingerprint = fingerprint
            service.pending_fingerprint = None
        return watch_status()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


if (FRONTEND / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=str(FRONTEND / 'assets')), name='assets')


@app.get('/')
def index():
    if not (FRONTEND / 'index.html').exists():
        return PlainTextResponse('Build the React frontend: cd codeimpact/frontend && npm ci && npm run build', status_code=503)
    return FileResponse(FRONTEND / 'index.html')
