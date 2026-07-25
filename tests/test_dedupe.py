
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dedupe.dedupe import dedupe_key, pick_best, remove_duplicates, remove_exact_duplicates


class TestDedupeKey(unittest.TestCase):
    def test_key_is_lowercased_email(self):
        record = {"email": "John.Smith@Example.com"}
        self.assertEqual(dedupe_key(record), "john.smith@example.com")


class TestPickBest(unittest.TestCase):
    def test_prefers_more_recent_date(self):
        older = {"signup_date": "2024-01-01", "full_name": "A"}
        newer = {"signup_date": "2024-02-01", "full_name": "A"}
        self.assertEqual(pick_best(older, newer), newer)

    def test_prefers_more_complete_record_on_date_tie(self):
        incomplete = {"signup_date": "2024-01-01", "full_name": "A", "phone": ""}
        complete = {"signup_date": "2024-01-01", "full_name": "A", "phone": "+14155551234"}
        self.assertEqual(pick_best(incomplete, complete), complete)


class TestRemoveDuplicates(unittest.TestCase):
    def test_removes_case_variant_duplicate(self):
        records = [
            {"full_name": "John Smith", "email": "john.smith@example.com", "phone": "+14155551234", "signup_date": "2024-01-15"},
            {"full_name": "John Smith", "email": "John.Smith@Example.com", "phone": "+14155551234", "signup_date": "2024-02-20"},
        ]
        result = remove_duplicates(records)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(len(result.unique_records), 1)
        # Keep-rule: more recent date wins.
        self.assertEqual(result.unique_records[0]["signup_date"], "2024-02-20")

    def test_no_duplicates_returns_all(self):
        records = [
            {"full_name": "A", "email": "a@example.com", "phone": "+14155551111", "signup_date": "2024-01-01"},
            {"full_name": "B", "email": "b@example.com", "phone": "+14155552222", "signup_date": "2024-01-02"},
        ]
        result = remove_duplicates(records)
        self.assertEqual(result.duplicates_removed, 0)
        self.assertEqual(len(result.unique_records), 2)


class TestRemoveExactDuplicates(unittest.TestCase):
    def test_removes_fully_identical_rows(self):
        rows = [
            {"full_name": "A", "email": "a@example.com", "_source_line": 2},
            {"full_name": "A", "email": "a@example.com", "_source_line": 3},
        ]
        unique_rows, count = remove_exact_duplicates(rows)
        self.assertEqual(count, 1)
        self.assertEqual(len(unique_rows), 1)

    def test_keeps_rows_that_differ_in_any_field(self):
        rows = [
            {"full_name": "A", "email": "a@example.com", "_source_line": 2},
            {"full_name": "A", "email": "different@example.com", "_source_line": 3},
        ]
        unique_rows, count = remove_exact_duplicates(rows)
        self.assertEqual(count, 0)
        self.assertEqual(len(unique_rows), 2)


if __name__ == "__main__":
    unittest.main()
