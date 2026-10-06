"""Bounded repository reads, Git changes, and line-addressable source chunks.

No analyzed code is imported or executed. Symlinks and ignored files are excluded.
"""

import ast
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.java', '.go',
              '.rs', '.c', '.h', '.cpp', '.cs', '.rb', '.php', '.md', '.txt', '.rst',
              '.yaml', '.yml', '.json', '.toml', '.html', '.css', '.sql', '.graphql', '.sh'}
EXCLUDE = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.codeimpact',
           '.pytest_cache', 'dist', 'build', 'coverage', '.next', '.idea', '.vscode'}
MAX_BYTES = 250_000
MAX_FILES = 2500


def safe_relative(value):
    value = value.replace('\\', '/')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or ':' in value or '\x00' in value:
        raise ValueError('File paths must be relative to the repository without traversal.')
    if not value or value == '.':
        raise ValueError('A file path is required.')
    return path.as_posix()


def eligible(path):
    p = PurePosixPath(path)
    name = p.name.lower()
    return (not any(part in EXCLUDE for part in p.parts)
            and not name.startswith('.env')
            and name not in {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'index.json'}
            and not name.endswith(('.pem', '.key'))
            and (p.suffix.lower() in EXTENSIONS or name == 'dockerfile'))


def git(root, *args, check=True):
    resolved = Path(root).resolve()
    git_root = next((p for p in [resolved, *resolved.parents] if (p / '.git').exists()), resolved)
    result = subprocess.run(
        ['git', '-c', f'safe.directory={git_root.as_posix()}', '-C', str(root), *args],
        capture_output=True, timeout=40, check=False,
    )
    if check and result.returncode:
        raise ValueError(result.stderr.decode('utf-8', errors='replace').strip()[:1200])
    return result.stdout.decode('utf-8', errors='replace')


def resolve_ref(root, ref):
    if not re.fullmatch(r'[A-Za-z0-9_./~^+-]{1,160}', ref) or ref.startswith('-'):
        raise ValueError('Invalid Git reference.')
    return git(root, 'rev-parse', '--verify', f'{ref}^{{commit}}').strip()


def snapshot(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Repository directory does not exist.')
    try:
        paths = sorted(set(git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\x00')) - {''})
    except (ValueError, FileNotFoundError):
        paths = []
        for directory, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDE and not (Path(directory) / d).is_symlink())
            paths.extend((Path(directory) / f).relative_to(root).as_posix() for f in files)
        paths.sort()
    files, skipped = {}, []
    for path in paths:
        if not eligible(path):
            continue
        try:
            target = root / safe_relative(path)
            if not target.is_file():
                continue
            if target.is_symlink() or not target.resolve().is_relative_to(root):
                skipped.append({'file': path, 'reason': 'symlink or outside repository'})
                continue
            if target.stat().st_size > MAX_BYTES or len(files) >= MAX_FILES:
                skipped.append({'file': path, 'reason': 'size or file-count limit'})
                continue
            text = target.read_text(encoding='utf-8-sig')
            if '\x00' in text:
                skipped.append({'file': path, 'reason': 'binary content'})
                continue
            files[path] = text
        except (UnicodeError, OSError, ValueError) as exc:
            skipped.append({'file': path, 'reason': str(exc)[:200]})
    digest = hashlib.sha256()
    for path, text in sorted(files.items()):
        digest.update((path + '\x00' + text + '\x00').encode())
    return {'files': files, 'fingerprint': digest.hexdigest(), 'skipped': skipped}


def git_changes(root, base='HEAD', head=None):
    base_sha = resolve_ref(root, base)
    revisions = [base_sha]
    if head:
        revisions.append(resolve_ref(root, head))
    diff = git(root, 'diff', '--relative', '--no-ext-diff', '--no-textconv', '--no-renames', '--unified=3', *revisions, '--', '.')
    if len(diff) > 500_000:
        raise ValueError('Git diff exceeds 500 KB; narrow the change before analysis.')
    paths = git(root, 'diff', '--relative', '--name-only', '-z', '--no-renames', *revisions, '--', '.').split('\x00')
    if not head:
        paths += git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\x00')
    paths = sorted({p for p in paths if p and eligible(p)})
    before = {}
    prefix = git(root, 'rev-parse', '--show-prefix').strip()
    # Keep the old dependency edges for deletions, renames, and removed imports.
    for path in paths:
        text = git(root, 'show', f'{base_sha}:{prefix}{path}', check=False)
        if text and len(text.encode()) <= MAX_BYTES:
            before[path] = text
    return {'diff': diff, 'files': paths, 'before': before, 'base': base_sha,
            'head': revisions[-1] if head else 'working-tree'}


def parse_diff(diff):
    paths, ranges = set(), {}
    current = None
    for line in diff.splitlines():
        if line.startswith(('--- ', '+++ ')):
            raw = line[4:].split('\t')[0].strip('"')
            if raw == '/dev/null':
                continue
            if raw.startswith(('a/', 'b/')):
                raw = raw[2:]
            current = safe_relative(raw)
            paths.add(current)
        elif line.startswith('@@') and current:
            match = re.search(r'\+(\d+)(?:,(\d+))?', line)
            if match:
                start, count = int(match[1]), int(match[2] or 1)
                ranges.setdefault(current, []).append([start, start + max(count - 1, 0)])
    return sorted(paths), ranges


def kind(path):
    p = PurePosixPath(path)
    if 'tests' in p.parts or p.name.startswith('test_') or re.search(r'\.(test|spec)\.', p.name):
        return 'test'
    if p.suffix in {'.md', '.rst', '.txt'} and not p.name.startswith('requirements'):
        return 'documentation'
    if p.suffix in {'.yaml', '.yml', '.toml', '.json'} or p.name.startswith(('Dockerfile', 'requirements')):
        return 'configuration'
    return 'source'


def chunks_for_file(path, text):
    lines = text.splitlines()
    boundaries = [(1, len(lines), '')]
    if path.endswith('.py'):
        try:
            tree = ast.parse(text)
            boundaries = []
            cursor = 1
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                    if start > cursor:
                        boundaries.append((cursor, start - 1, 'module'))
                    boundaries.append((start, node.end_lineno, node.name))
                    cursor = node.end_lineno + 1
            if cursor <= len(lines):
                boundaries.append((cursor, len(lines), 'module'))
        except SyntaxError:
            pass
    chunks = []
    for start, end, symbol in boundaries:
        # Split large units; all chunks retain true line references and stable IDs.
        for offset in range(start, end + 1, 35):
            stop = min(offset + 34, end)
            excerpt = '\n'.join(lines[offset - 1:stop])
            if not excerpt.strip():
                continue
            # Minified lines and embedded base64 are not useful repository evidence.
            excerpt = '\n'.join(line[:1000] for line in excerpt.splitlines())[:6000]
            key = f'{path}:{offset}:{stop}:{excerpt}'
            chunks.append({'id': hashlib.sha256(key.encode()).hexdigest(), 'file': path,
                           'start': offset, 'end': stop, 'symbol': symbol,
                           'kind': kind(path), 'text': excerpt})
    return chunks
