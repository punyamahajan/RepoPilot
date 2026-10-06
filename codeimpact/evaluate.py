"""Reproducible impact precision/recall/F1 against hand-labelled small-repo cases."""

import argparse
import json
import os
from pathlib import Path
import time

from .engine import analyze
from .repository import chunks_for_file, snapshot
from .retrieval import lexical_search


def scores(predicted, expected):
    predicted, expected = set(predicted), set(expected)
    tp = len(predicted & expected)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(expected) if expected else 0.0
    return {'precision': precision, 'recall': recall,
            'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            'true_positives': tp, 'false_positives': sorted(predicted - expected),
            'false_negatives': sorted(expected - predicted)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--semantic', action='store_true', help='Also measure hybrid retrieval with real Ollama embeddings.')
    parser.add_argument('--output', default='.codeimpact/evaluation')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / 'data/codeimpact_demo'
    cases = json.loads((Path(__file__).parent / 'evaluation/cases.json').read_text())
    files = snapshot(root)['files']
    chunks = [chunk for path, text in files.items() for chunk in chunks_for_file(path, text)]
    rows = []
    for case in cases:
        print(f"Evaluating {case['id']}", flush=True)
        start = time.perf_counter()
        baseline = {c['file'] for c in lexical_search(case['description'] + ' ' + case['file'], chunks, 5)}
        keyword_seconds = time.perf_counter() - start
        report = analyze(root, Path(os.getenv('CODEIMPACT_STATE_DIR', '.codeimpact')) / 'eval-state', description=case['description'],
                         changed_files=[case['file']], semantic=args.semantic, use_llm=False)
        traced = {x['file'] for x in report['affected']}
        hybrid = traced | {x['file'] for x in report['semantic_candidates']}
        rows.append({'id': case['id'], 'expected': case['expected'],
                     'keyword': scores(baseline, case['expected']), 'graph': scores(traced, case['expected']),
                     'hybrid': scores(hybrid, case['expected']) if args.semantic and report['index']['status']=='ready' else None,
                     'keyword_seconds': keyword_seconds, 'analysis_seconds': report['duration_seconds'],
                     'semantic_status': report['index']['status']})
    summary = {}
    for method in ('keyword', 'graph', 'hybrid'):
        completed = [r[method] for r in rows if r[method] is not None]
        summary[method] = {k: sum(r[k] for r in completed) / len(completed) for k in ('precision','recall','f1')} if completed else None
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.json').write_text(json.dumps({'cases': rows, 'macro_average': summary}, indent=2))
    lines = ['# CodeImpact benchmark', '',
             'Ten hand-labelled scenarios over a small executable fixture repository. Ground truth lists all reachable consumers, including tests.', '',
             'Precision = TP / predicted files. Recall = TP / expected files. F1 = 2PR / (P+R). Averages are macro-averaged over identical cases.', '',
             'Keyword baseline: top 5 matching chunks. Graph: all reverse dependency consumers. Hybrid: graph union top retrieval candidates (unconfirmed candidates count as predictions).', '',
             '| Method | Precision | Recall | F1 |', '|---|---:|---:|---:|']
    for method, values in summary.items():
        if values:
            lines.append(f"| {method} | {values['precision']:.3f} | {values['recall']:.3f} | {values['f1']:.3f} |")
        else:
            lines.append(f'| {method} | Not measured | Not measured | Not measured |')
    lines += ['', 'This fixture checks dependency tracing, not generalization to large production repositories. It does not establish that LLM reasoning outperforms static analysis. AI suggestions require a separate human-labelled benchmark.', '']
    output.with_suffix('.md').write_text('\n'.join(lines))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
