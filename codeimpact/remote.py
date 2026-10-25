"""Clone and refresh live remote repositories (GitHub, GitLab, Bitbucket) for analysis.

Clones are shallow, kept under the CodeImpact state directory, and never execute
repository code. An optional access token is passed to Git through environment
configuration for that one command, so it is never written into .git/config.
"""

import base64
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit


HOSTS = {h.strip().lower() for h in os.getenv('CODEIMPACT_GIT_HOSTS', 'github.com,gitlab.com,bitbucket.org').split(',') if h.strip()}
DEPTH = int(os.getenv('CODEIMPACT_CLONE_DEPTH', '50'))
NAME = re.compile(r'[A-Za-z0-9_.-]{1,100}')
BRANCH = re.compile(r'[A-Za-z0-9_./-]{1,160}')


def parse_url(value):
    """Return (clone_url, owner, name, branch) for a repository web or clone URL."""
    value = (value or '').strip()
    if value.startswith('git@'):
        raise ValueError('Use the HTTPS address of the repository (https://github.com/owner/repo).')
    if not re.match(r'^https?://', value):
        value = 'https://' + value
    parts = urlsplit(value)
    host = (parts.hostname or '').lower()
    if parts.scheme != 'https' or host not in HOSTS or parts.username or parts.password or parts.port:
        raise ValueError(f"Only HTTPS repository URLs on {', '.join(sorted(HOSTS))} are supported.")
    segments = [s for s in parts.path.split('/') if s]
    if len(segments) < 2:
        raise ValueError('The URL must include the owner and repository, e.g. https://github.com/owner/repo.')
    owner, name = segments[0], segments[1].removesuffix('.git')
    if not NAME.fullmatch(owner) or not NAME.fullmatch(name) or name in {'.', '..'} or owner in {'.', '..'}:
        raise ValueError('That repository owner or name is not valid.')
    branch = None
    # https://github.com/owner/repo/tree/<branch> (GitLab uses /-/tree/<branch>).
    rest = segments[2:]
    if rest[:1] == ['-']:
        rest = rest[1:]
    if len(rest) >= 2 and rest[0] == 'tree':
        branch = '/'.join(rest[1:])
        if not BRANCH.fullmatch(branch) or '..' in branch or branch.startswith('-'):
            raise ValueError('That branch name is not valid.')
    return f'https://{host}/{owner}/{name}.git', owner, name, branch


def _git(args, cwd=None, token='', host='github.com', timeout=600):
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': 'echo'}
    if token:
        user = 'x-access-token' if host == 'github.com' else 'oauth2'
        credentials = base64.b64encode(f'{user}:{token}'.encode()).decode()
        env.update({'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'http.extraHeader',
                    'GIT_CONFIG_VALUE_0': f'Authorization: Basic {credentials}'})
    try:
        # Clones live on a bind mount in Docker, so ownership differs from the container user.
        result = subprocess.run(['git', '-c', 'safe.directory=*', *args], cwd=cwd, env=env, capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError:
        raise ValueError('Git is not installed on the CodeImpact server.') from None
    except subprocess.TimeoutExpired:
        raise ValueError('Git timed out while downloading the repository.') from None
    if result.returncode:
        message = result.stderr.decode('utf-8', errors='replace').strip()
        if token:
            message = message.replace(token, '••••')
        if 'could not read Username' in message or 'Authentication failed' in message or 'not found' in message.lower():
            message = 'Repository not found or not accessible. For a private repository, add an access token.'
        raise ValueError(message[-800:] or 'Git command failed.')
    return result.stdout.decode('utf-8', errors='replace').strip()


def sync(url, base_dir, allowed_root, branch=None, token=''):
    """Clone the repository, or fetch the latest commit if it was cloned before."""
    clone_url, owner, name, url_branch = parse_url(url)
    branch = (branch or url_branch or '').strip() or None
    if branch and (not BRANCH.fullmatch(branch) or '..' in branch or branch.startswith('-')):
        raise ValueError('That branch name is not valid.')
    host = urlsplit(clone_url).hostname
    base_dir = Path(base_dir).resolve()
    target = (base_dir / f'{host.split(".")[0]}__{owner}__{name}').resolve()
    if not target.is_relative_to(base_dir):
        raise ValueError('Invalid repository location.')
    if (target / '.git').is_dir():
        ref = branch or _git(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=target)
        _git(['fetch', '--depth', str(DEPTH), '--no-tags', 'origin', f'+{ref}:refs/remotes/origin/{ref}'],
             cwd=target, token=token, host=host)
        _git(['checkout', '-q', '-B', ref, f'refs/remotes/origin/{ref}'], cwd=target)
        _git(['reset', '-q', '--hard', f'refs/remotes/origin/{ref}'], cwd=target)
        action = 'updated'
    else:
        if target.exists():
            shutil.rmtree(target)
        base_dir.mkdir(parents=True, exist_ok=True)
        args = ['clone', '--depth', str(DEPTH), '--no-tags', '--single-branch']
        if branch:
            args += ['--branch', branch]
        _git([*args, '--', clone_url, str(target)], token=token, host=host)
        action = 'cloned'
    head = _git(['rev-parse', 'HEAD'], cwd=target)
    current = _git(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=target)
    subject = _git(['log', '-1', '--format=%s'], cwd=target)
    return {'repository': target.relative_to(Path(allowed_root).resolve()).as_posix(),
            'url': f'https://{host}/{owner}/{name}', 'branch': current, 'head': head, 'commit_subject': subject,
            'action': action}


def cloned(base_dir, allowed_root):
    """List repositories already cloned into the state directory."""
    base_dir = Path(base_dir)
    result = []
    if not base_dir.is_dir():
        return result
    for path in sorted(base_dir.iterdir()):
        if not (path / '.git').is_dir():
            continue
        try:
            url = _git(['remote', 'get-url', 'origin'], cwd=path).removesuffix('.git')
            branch = _git(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=path)
            head = _git(['rev-parse', '--short', 'HEAD'], cwd=path)
        except ValueError:
            continue
        result.append({'repository': path.resolve().relative_to(Path(allowed_root).resolve()).as_posix(),
                       'url': url, 'branch': branch, 'head': head})
    return result
