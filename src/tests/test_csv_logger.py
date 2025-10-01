import os
import tempfile
import unittest
from csv_logger import CSVLogger

class TestCSVLogger(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmpdir.name, 'test.csv')
        self.logger = CSVLogger(self.path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_header_created(self):
        # header should exist with expected columns
        with open(self.path, 'r') as f:
            header = f.readline().strip()
        self.assertIn('timestamp', header)
        self.assertIn('class', header)
        self.assertIn('Brake', header)
        self.assertIn('state', header)

    def test_single_key_log(self):
        self.logger.log_entry('j', '00:00:01:000')
        with open(self.path, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(len(lines), 2)
        cols = lines[1].split(',')
        self.assertEqual(cols[0], '00:00:01:000')
        # j column should be set to 'j'
        header = lines[0].split(',')
        class_index = header.index('class')
        self.assertEqual(cols[class_index], 'j')

    def test_multiple_keys_same_timestamp(self):
        # j then k at same timestamp should result in class column reflecting toggles
        self.logger.log_entry('j', '00:00:02:000')
        self.logger.log_entry('k', '00:00:02:000')
        with open(self.path, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertEqual(len(lines), 2)
        header = lines[0].split(',')
        class_index = header.index('class')
        cols = lines[1].split(',')
        # After pressing j then k, class column should equal 'k' (last press replaces)
        self.assertEqual(cols[class_index], 'k')

    def test_digits_aggregate_in_numbers(self):
        self.logger.log_entry('1', '00:00:03:000')
        self.logger.log_entry('2', '00:00:03:000')
        with open(self.path, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
        header = lines[0].split(',')
        num_index = header.index('state')
        cols = lines[1].split(',')
        # numbers column should be overwritten by the last pressed digit '2'
        self.assertEqual(cols[num_index], '2')

    def test_sorting_keeps_header(self):
        self.logger.log_entry('j', '00:00:05:000')
        self.logger.log_entry('k', '00:00:01:000')
        self.logger.sort_log_file()
        with open(self.path, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
        # header + 2 rows
        self.assertEqual(len(lines), 3)
        # after sorting, the earlier timestamp should be on line 1 of data (index 1)
        self.assertTrue(lines[1].startswith('00:00:01:000'))

if __name__ == '__main__':
    unittest.main()
