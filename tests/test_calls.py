import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from job_call_graph import parse_calls, resolve_calls


class CallTests(unittest.TestCase):
    def test_numeric_calls_and_source_locations(self):
        text = ('# call 9999\n'
                'print "call 8888"\n'
                '     call 9250 #시그널 클리어\n'
                'S2   CALL 5001 #비젼 리셋\n'
                '     recall 3000\n'
                '     call 1000_extra\n'
                '     call 1000')
        calls = parse_calls(text, 'main.job')
        self.assertEqual([(call.target, call.line) for call in calls],
                         [('9250', 3), ('5001', 4), ('1000', 7)])
        self.assertEqual(calls[0].comment, '시그널 클리어')
        self.assertEqual(calls[0].source, 'main.job')

    def test_resolution_prefers_same_folder_and_reports_unknowns(self):
        calls = parse_calls('call 9250\ncall 5001\ncall 1000\ncall 7000', 'cell-a/main.job')
        files = ['cell-a/main.job', 'cell-a/9250.job', 'cell-b/9250.job',
                 'cell-b/5001.JOB', 'cell-b/7000.job', 'cell-c/7000.job']
        links = resolve_calls(calls, files)
        self.assertEqual([link.status for link in links],
                         ['resolved', 'resolved', 'missing', 'ambiguous'])
        self.assertEqual(links[0].target_path, 'cell-a/9250.job')
        self.assertEqual(links[1].target_path, 'cell-b/5001.JOB')
        self.assertEqual(len(links[3].candidates), 2)

    def test_leading_zero_variants_and_exact_precedence(self):
        calls = parse_calls('call 405\ncall 0405\ncall 1\ncall 2', 'cell/main.job')
        files = ['cell/main.job', 'cell/405.job', 'cell/0405.job',
                 'cell/0001.job', 'cell/2.job', 'cell/0002.job']
        links = resolve_calls(calls, files)
        self.assertEqual([link.target_path for link in links],
                         ['cell/405.job', 'cell/0405.job', 'cell/0001.job', 'cell/2.job'])
        ambiguous = resolve_calls(parse_calls('call 405', 'cell/main.job'),
                                  ['cell/0405.job', 'cell/00405.job'])
        self.assertEqual(ambiguous[0].status, 'ambiguous')

    def test_no_signal_file_can_still_have_calls(self):
        root = Path(__file__).resolve().parent / 'fixtures' / 'calls'
        calls = parse_calls((root / 'main.job').read_text(encoding='utf-8'), str(root / 'main.job'))
        links = resolve_calls(calls, [str(path) for path in root.glob('*.job')])
        self.assertEqual([link.call.target for link in links], ['9250', '5001', '1000'])
        self.assertEqual([link.status for link in links], ['resolved', 'resolved', 'missing'])


if __name__ == '__main__':
    unittest.main()
