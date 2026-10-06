"""CLI for local use and pull-request CI; no shell or model-generated commands."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from .engine import analyze, markdown_report
from .repository import safe_relative


def run_recommended_tests(report, root):
    root = Path(root).resolve()
    paths = sorted({t['file'] for t in report['recommended_tests']
                    if t['relationship'] == 'traced' and t['file'].endswith('.py')})
    validated = []
    for file in paths:
        path = root / safe_relative(file)
        if path.is_file() and path.resolve().is_relative_to(root) and not path.is_symlink():
            validated.append(path.relative_to(root).as_posix())
    if not validated:
        return {'status': 'not_run', 'reason': 'No supported, traced Python tests found.'}
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--', *validated],
                                cwd=root, capture_output=True, text=True, timeout=180)
        return {'status': 'passed' if result.returncode == 0 else 'failed',
                'exit_code': result.returncode, 'files': validated,
                'output': (result.stdout + result.stderr)[-15000:]}
    except subprocess.TimeoutExpired:
        return {'status': 'failed', 'reason': 'Selected tests exceeded 180 seconds.'}


def main():
    parser = argparse.ArgumentParser(description='Map repository change impact with evidence.')
    parser.add_argument('--repo', default='.')
    parser.add_argument('--description', default='')
    parser.add_argument('--diff-file')
    parser.add_argument('--file', action='append', default=[])
    parser.add_argument('--git', action='store_true')
    parser.add_argument('--base', default='HEAD')
    parser.add_argument('--head')
    parser.add_argument('--no-semantic', action='store_true')
    parser.add_argument('--no-llm', action='store_true')
    parser.add_argument('--model', default='codellama')
    parser.add_argument('--output', default='.codeimpact/latest')
    parser.add_argument('--run-tests', action='store_true', help='Execute traced Python tests. Use only for a trusted repository.')
    args = parser.parse_args()
    report = analyze(args.repo, Path(os.getenv('CODEIMPACT_STATE_DIR', '.codeimpact')), description=args.description,
                     diff=Path(args.diff_file).read_text(encoding='utf-8') if args.diff_file else '',
                     changed_files=args.file, use_git=args.git, base=args.base, head=args.head,
                     semantic=not args.no_semantic, use_llm=not args.no_llm, model=args.model,
                     progress=lambda message: print(message, flush=True))
    if args.run_tests:
        report['test_execution'] = run_recommended_tests(report, args.repo)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    output.with_suffix('.md').write_text(markdown_report(report), encoding='utf-8')
    print(f"{report['summary']} Risk: {report['risk']}. Report: {output.with_suffix('.md')}")
    return 1 if report.get('test_execution', {}).get('status') == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
