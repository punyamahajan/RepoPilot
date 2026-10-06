import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from codeimpact.engine import analyze, markdown_report
from codeimpact.evaluate import scores
from codeimpact.graph import build_graph, propagate
from codeimpact.repository import chunks_for_file, git_changes, parse_diff, safe_relative, snapshot


class CodeImpactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def init_git(self):
        for args in (['init'], ['add', '.'], ['-c', 'user.name=Test', '-c', 'user.email=test@example.test', 'commit', '-m', 'fixture']):
            subprocess.run(['git', '-C', str(self.root), *args], capture_output=True, check=True)

    def test_import_alias_and_transitive_consumers_with_cycles(self):
        files = {'core.py': 'import api\ndef cost(): return 3',
                 'api.py': 'from core import cost as fee\ndef route(): return fee()',
                 'tests/test_api.py': 'from api import route\ndef test_route(): assert route() == 3',
                 'unrelated.py': 'def foo(): return 0'}
        graph = build_graph(files)
        paths = propagate(graph, ['core.py'])
        self.assertEqual(set(paths), {'core.py', 'api.py', 'tests/test_api.py'})
        self.assertEqual(len(paths['tests/test_api.py']), 2)
        self.assertTrue(any(e['relation'] == 'calls imported symbol' for e in graph['edges']))

    def test_relative_imports_and_js_consumers(self):
        graph = build_graph({'pkg/core.py': 'def answer(): return 1',
                             'pkg/ui.py': 'from .core import answer',
                             'src/lib.ts': 'export const fee = 3;',
                             'src/view.tsx': "import {fee} from './lib';"})
        self.assertIn('pkg/ui.py', propagate(graph, ['pkg/core.py']))
        self.assertIn('src/view.tsx', propagate(graph, ['src/lib.ts']))

    def test_chunks_have_true_source_lines(self):
        text = '# heading\n\ndef one():\n    return 1\n\nclass Two:\n    pass\n'
        chunks = chunks_for_file('example.py', text)
        one = next(c for c in chunks if c['symbol'] == 'one')
        self.assertEqual((one['start'], one['end']), (3, 4))
        self.assertEqual(one['text'], 'def one():\n    return 1')

    def test_scanner_excludes_secrets_and_dependencies(self):
        self.write('src/file.py', 'x = 1')
        self.write('node_modules/file.js', 'export const x = 1')
        self.write('.env', 'EXAMPLE_SECRET=test')
        self.write('.codeimpact/generated.py', 'x = 2')
        self.assertEqual(set(snapshot(self.root)['files']), {'src/file.py'})

    def test_gitignore_is_respected(self):
        self.write('.gitignore', 'ignored.py\n')
        self.write('keep.py', 'x=1')
        self.init_git()
        self.write('ignored.py', 'x=2')
        self.assertNotIn('ignored.py', snapshot(self.root)['files'])

    def test_invalid_paths_rejected(self):
        for path in ('../outside.py', 'C:\\private.py', '/etc/passwords', 'a/../../b.py'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_relative(path)

    def test_diff_rename_and_hunk_parsing(self):
        paths, ranges = parse_diff('--- a/old.py\n+++ b/new.py\n@@ -5,2 +7,3 @@\n+value')
        self.assertEqual(paths, ['new.py', 'old.py'])
        self.assertEqual(ranges['new.py'], [[7, 9]])

    def test_deleted_provider_still_traces_dependents(self):
        self.write('core.py', 'def fee(): return 3')
        self.write('consumer.py', 'from core import fee')
        self.init_git()
        (self.root / 'core.py').unlink()
        report = analyze(self.root, self.root / '.codeimpact', use_git=True, semantic=False, use_llm=False)
        self.assertEqual(set(i['file'] for i in report['affected']), {'core.py', 'consumer.py'})
        self.assertTrue(next(i for i in report['affected'] if i['file'] == 'core.py')['deleted'])
        self.assertTrue(any(e.get('revision') == 'base' for e in report['graph']['edges']))

    def test_staged_unstaged_and_untracked_changes(self):
        self.write('one.py', 'x=1')
        self.write('two.py', 'x=2')
        self.init_git()
        self.write('one.py', 'x=3')
        subprocess.run(['git','-C',str(self.root),'add','one.py'], check=True, capture_output=True)
        self.write('two.py', 'x=4')
        self.write('three.py', 'x=5')
        self.assertEqual(git_changes(self.root)['files'], ['one.py','three.py','two.py'])

    def test_git_changes_in_subdirectory_are_relative_and_scoped(self):
        self.write('pkg/one.py', 'x=1')
        self.write('outside.py', 'x=2')
        self.init_git()
        self.write('pkg/one.py', 'x=3')
        self.write('outside.py', 'x=4')
        changes = git_changes(self.root / 'pkg')
        self.assertEqual(changes['files'], ['one.py'])
        self.assertEqual(changes['before']['one.py'], 'x=1')

    def test_no_changes_does_not_invent_impact(self):
        self.write('core.py', 'x=1')
        self.init_git()
        with self.assertRaisesRegex(ValueError, 'No changes'):
            analyze(self.root, self.root / '.codeimpact', use_git=True, semantic=False, use_llm=False)

    def test_unknown_file_not_silently_replaced_by_inferred_seed(self):
        self.write('auth.py', 'def authenticate(): return True')
        report = analyze(self.root, self.root / '.codeimpact', changed_files=['missing.py'],
                         description='Change authentication', semantic=False, use_llm=False)
        self.assertEqual(report['status'], 'insufficient_evidence')
        self.assertEqual(report['affected'], [])
        self.assertEqual(report['coverage']['unknown_changed_files'], ['missing.py'])

    @patch('codeimpact.engine.SemanticIndex', side_effect=RuntimeError('Ollama offline'))
    def test_offline_semantic_failure_retains_static_report(self, _index):
        self.write('core.py', 'def fee(): return 3')
        report = analyze(self.root, self.root / '.codeimpact', changed_files=['core.py'], use_llm=False)
        self.assertEqual(report['index']['status'], 'unavailable')
        self.assertEqual(report['affected'][0]['file'], 'core.py')
        self.assertIn('Semantic retrieval unavailable', report['warnings'][0])

    def test_api_routes_and_test_recommendations(self):
        self.write('api.py', '@app.post("/checkout")\ndef checkout(): return 3')
        self.write('tests/test_api.py', 'from api import checkout')
        report = analyze(self.root, self.root / '.codeimpact', changed_files=['api.py'], semantic=False, use_llm=False)
        self.assertEqual(report['risk'], 'High')
        self.assertEqual(report['affected'][0]['apis'][0]['path'], '/checkout')
        self.assertEqual(report['recommended_tests'][0]['file'], 'tests/test_api.py')
        self.assertIn('tests/test_api.py', markdown_report(report))

    def test_invalid_python_reports_partial_coverage(self):
        graph = build_graph({'broken.py': 'def invalid('})
        self.assertTrue(graph['warnings'])
        self.assertIn('broken.py', graph['nodes'])

    def test_precision_recall_calculation(self):
        values = scores({'a','b'}, {'b','c','d'})
        self.assertEqual(values['precision'], .5)
        self.assertAlmostEqual(values['recall'], 1/3)
        self.assertAlmostEqual(values['f1'], .4)

    def test_hand_labelled_dependency_scenarios(self):
        root = Path(__file__).resolve().parents[1]
        files = snapshot(root / 'data/codeimpact_demo')['files']
        graph = build_graph(files)
        cases = json.loads((root / 'codeimpact/evaluation/cases.json').read_text())
        for case in cases:
            with self.subTest(case=case['id']):
                self.assertEqual(set(propagate(graph, [case['file']])), set(case['expected']))


if __name__ == '__main__':
    unittest.main()
