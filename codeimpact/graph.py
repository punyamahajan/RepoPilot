"""Conservative file dependency graph with source evidence and reverse reachability."""

import ast
from collections import defaultdict, deque
import posixpath
import re

from .repository import kind


def module_candidates(module, source, relative=0):
    base = posixpath.dirname(source) if relative else ''
    for _ in range(max(relative - 1, 0)):
        base = posixpath.dirname(base)
    path = posixpath.join(base, module.replace('.', '/'))
    return [path + '.py', path + '/__init__.py', path]


def build_graph(files):
    nodes, edges, warnings = {}, [], []
    known = set(files)
    seen = set()

    def edge(source, target, line, relation, evidence, confidence='static'):
        key = (source, target, line, relation)
        if source == target or key in seen or target not in known:
            return
        seen.add(key)
        edges.append({'source': source, 'target': target, 'line': line,
                      'relation': relation, 'evidence': evidence[:300], 'confidence': confidence})

    trees = {}
    for path, text in files.items():
        nodes[path] = {'id': path, 'kind': kind(path), 'symbols': [], 'apis': []}
        if not path.endswith('.py'):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            warnings.append(f'{path}: Python syntax could not be parsed at line {exc.lineno}.')
            continue
        trees[path] = tree
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nodes[path]['symbols'].append({'name': node.name, 'start': node.lineno, 'end': node.end_lineno})
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr in {'get', 'post', 'put', 'patch', 'delete', 'route'} and decorator.args:
                            if isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                                nodes[path]['apis'].append({'method': decorator.func.attr.upper(),
                                                          'path': decorator.args[0].value,
                                                          'function': node.name, 'line': node.lineno})
        aliases = {}
        for node in ast.walk(tree):
            imports = []
            if isinstance(node, ast.Import):
                for item in node.names:
                    imports.append((item.name, 0, item.asname or item.name.split('.')[0]))
            elif isinstance(node, ast.ImportFrom):
                for item in node.names:
                    imports.extend([(node.module or '', node.level, item.asname or item.name),
                                    ('.'.join(filter(None, [node.module, item.name])), node.level, item.asname or item.name)])
            for module, level, alias in imports:
                candidates = module_candidates(module, path, level)
                # Direct-script imports in RepoPilot use the script's directory.
                if not level:
                    candidates += module_candidates(module, path, 1)
                target = next((p for p in candidates if p in known), None)
                if target:
                    aliases[alias] = target
                    edge(path, target, node.lineno, 'imports', ast.get_source_segment(text, node) or module)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call = ast.unparse(node.func)
                target = aliases.get(call.split('.')[0])
                if target:
                    edge(path, target, node.lineno, 'calls imported symbol', call)

    # JS/TS module imports are syntax-pattern based, not a full compiler resolution.
    for path, text in files.items():
        if re.search(r'\.(?:[cm]?js|jsx|tsx?)$', path):
            for match in re.finditer(r'(?:from\s*|import\s*|require\s*\()\s*[\'"]([^\'"]+)[\'"]', text):
                module = match[1]
                if not module.startswith('.'):
                    continue
                stem = posixpath.normpath(posixpath.join(posixpath.dirname(path), module))
                candidates = [stem] + [stem + ext for ext in ('.js', '.jsx', '.ts', '.tsx')]
                candidates += [stem + '/index' + ext for ext in ('.js', '.jsx', '.ts', '.tsx')]
                target = next((p for p in candidates if p in known), None)
                if target:
                    edge(path, target, text[:match.start()].count('\n') + 1, 'imports', match[0], 'pattern')
        # Literal file references connect docs, workflows, templates, and deployment files.
        for number, line in enumerate(text.splitlines(), 1):
            if len(line) > 3000:
                continue
            for match in re.finditer(r'[\w./-]+\.(?:py|jsx?|tsx?|md|ya?ml|html|json|toml)\b', line):
                reference = match[0].removeprefix('./')
                target = reference if reference in known else posixpath.normpath(posixpath.join(posixpath.dirname(path), reference))
                if target in known:
                    edge(path, target, number, 'references file', line.strip(), 'pattern')
    return {'nodes': nodes, 'edges': edges, 'warnings': warnings}


def propagate(graph, changed):
    """Return every reachable consumer, keeping one shortest evidence path per file."""
    reverse = defaultdict(list)
    for edge in graph['edges']:
        reverse[edge['target']].append(edge)
    paths = {p: [] for p in changed}
    queue = deque(sorted(changed))
    while queue:
        provider = queue.popleft()
        for edge in sorted(reverse[provider], key=lambda e: (e['source'], e['line'])):
            consumer = edge['source']
            if consumer not in paths:
                paths[consumer] = paths[provider] + [edge]
                queue.append(consumer)
    return paths
