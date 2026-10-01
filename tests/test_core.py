import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from job_core import collect_files, read_job, split_line
from job_signal_extractor import (
    collect_files as extractor_collect_files,
    read_job as extractor_read_job,
    split_line as extractor_split_line,
)


class CoreTests(unittest.TestCase):
    def test_existing_extractor_imports_remain_available(self):
        self.assertIs(collect_files, extractor_collect_files)
        self.assertIs(read_job, extractor_read_job)
        self.assertIs(split_line, extractor_split_line)

    def test_utf16_and_job_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job = root / '0001.JOB'
            job.write_bytes('call 9250 #초기화\nwait di40'.encode('utf-16'))
            self.assertEqual(read_job(job), ('call 9250 #초기화\nwait di40', 'utf-16'))
            self.assertEqual(collect_files([str(root), str(job)]), [job.resolve()])

    def test_quoted_hash_is_not_comment(self):
        code, comment = split_line('print "di3 # 문자"; do40=1 #실제 주석')
        self.assertNotIn('di3', code)
        self.assertIn('do40=1', code)
        self.assertEqual(comment, '실제 주석')


if __name__ == '__main__':
    unittest.main()
