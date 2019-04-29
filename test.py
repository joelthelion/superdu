#!/usr/bin/env python3
""" Test non-regression to make refactoring easier """

import unittest
import pickle
import superdu


class TestSuperdu(unittest.TestCase):
    def test_non_regression(self):
        with open("test/processed.pck", "rb") as f:
            reference = pickle.load(f)
        tuples = superdu.read_file("test/du_output.txt")
        processed = superdu.process_du_output(tuples, 1024*100)
        self.assertEqual(processed, reference)


if __name__ == '__main__':
    unittest.main()
