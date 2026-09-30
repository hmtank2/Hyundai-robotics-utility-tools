import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = Path(__file__).resolve().parent / 'fixtures' / 'sample.job'
EXE = ROOT / 'dist' / 'JOB_Signal_Explorer.exe'


class FrozenTests(unittest.TestCase):
    @unittest.skipUnless(EXE.is_file(), 'Build the EXE first with packaging/JOB_Signal_Explorer.spec')
    def test_self_test(self):
        env = dict(os.environ)
        for key in ('PYTHONPATH', 'PYTHONHOME', 'TCL_LIBRARY', 'TK_LIBRARY'):
            env.pop(key, None)
        env['PATH'] = str(Path(os.environ.get('SYSTEMROOT', 'C:/Windows')) / 'System32')
        with tempfile.TemporaryDirectory() as folder:
            env['TEMP'] = env['TMP'] = folder
            report = Path(folder) / 'self_test.json'
            result = subprocess.run(
                [str(EXE), '--self-test', str(SAMPLE), str(report)],
                env=env, cwd=folder, timeout=50, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(report.read_text(encoding='utf-8')),
                {'ok': True, 'occurrences': 18, 'signals': 18, 'graph_connections': 18,
                 'calls': 0, 'resolved_calls': 0},
            )
            self.assertTrue(report.with_suffix('.xlsx').is_file())

    @unittest.skipUnless(EXE.is_file(), 'Build the EXE first with packaging/JOB_Signal_Explorer.spec')
    def test_call_graph_self_test(self):
        sample = SAMPLE.parent / 'calls' / 'main.job'
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'calls.json'
            result = subprocess.run(
                [str(EXE), '--self-test', str(sample), str(report)],
                cwd=folder, timeout=50, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(report.read_text(encoding='utf-8')),
                {'ok': True, 'occurrences': 0, 'signals': 1, 'graph_connections': 3,
                 'calls': 4, 'resolved_calls': 3},
            )


if __name__ == '__main__':
    unittest.main()
