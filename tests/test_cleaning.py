
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cleaning.name_cleaner import clean_name
from cleaning.phone_cleaner import clean_phone
from cleaning.email_cleaner import clean_email
from cleaning.date_cleaner import clean_date


class TestNameCleaner(unittest.TestCase):
    def test_basic_capitalization(self):
        self.assertEqual(clean_name("john smith"), "John Smith")

    def test_collapses_whitespace(self):
        self.assertEqual(clean_name("Jane   Doe"), "Jane Doe")

    def test_strips_leading_trailing_whitespace_and_tabs(self):
        self.assertEqual(clean_name("\tFrank Ocean"), "Frank Ocean")

    def test_hyphenated_surname_preserved(self):
        self.assertEqual(clean_name("david-lee chen"), "David-Lee Chen")

    def test_apostrophe_name_preserved(self):
        self.assertEqual(clean_name("mary-jane o'brien"), "Mary-Jane O'Brien")

    def test_none_input_returns_none(self):
        self.assertIsNone(clean_name(None))

    def test_blank_input_returns_none(self):
        self.assertIsNone(clean_name("   "))


class TestPhoneCleaner(unittest.TestCase):
    def test_dashed_format(self):
        value, err = clean_phone("415-555-1234")
        self.assertEqual(value, "+14155551234")
        self.assertIsNone(err)

    def test_parenthesized_format(self):
        value, err = clean_phone("(415) 555-1234")
        self.assertEqual(value, "+14155551234")
        self.assertIsNone(err)

    def test_dotted_format(self):
        value, err = clean_phone("415.555.1234")
        self.assertEqual(value, "+14155551234")
        self.assertIsNone(err)

    def test_already_has_country_code(self):
        value, err = clean_phone("+1 415 555 1234")
        self.assertEqual(value, "+14155551234")
        self.assertIsNone(err)

    def test_too_few_digits_rejected(self):
        value, err = clean_phone("555-1234")
        self.assertIsNone(value)
        self.assertIn("digit", err)

    def test_missing_phone_rejected(self):
        value, err = clean_phone("")
        self.assertIsNone(value)
        self.assertEqual(err, "phone missing")


class TestEmailCleaner(unittest.TestCase):
    def test_lowercases_domain(self):
        value, err = clean_email("Jane.Doe@EXAMPLE.COM")
        self.assertEqual(value, "Jane.Doe@example.com")
        self.assertIsNone(err)

    def test_missing_at_symbol_rejected(self):
        value, err = clean_email("bob.miller")
        self.assertIsNone(value)
        self.assertIn("@", err)

    def test_missing_email_rejected(self):
        value, err = clean_email("")
        self.assertIsNone(value)
        self.assertEqual(err, "email missing")

    def test_invalid_structure_rejected(self):
        value, err = clean_email("sam.wilson@example")
        self.assertIsNone(value)
        self.assertIn("structural validity", err)


class TestDateCleaner(unittest.TestCase):
    def test_already_iso(self):
        value, err = clean_date("2024-01-15")
        self.assertEqual(value, "2024-01-15")
        self.assertIsNone(err)

    def test_slash_mmddyyyy_unambiguous(self):
        # day component (20) > 12, so this can only be DD/MM/YYYY
        value, err = clean_date("20/11/2024")
        self.assertEqual(value, "2024-11-20")
        self.assertIsNone(err)

    def test_ambiguous_date_flagged(self):
        value, err = clean_date("03/04/25")
        self.assertIsNone(value)
        self.assertIn("ambiguous", err)

    def test_written_month_with_comma(self):
        value, err = clean_date("May 6, 2024")
        self.assertEqual(value, "2024-05-06")
        self.assertIsNone(err)

    def test_written_month_without_comma(self):
        value, err = clean_date("March 3 2024")
        self.assertEqual(value, "2024-03-03")
        self.assertIsNone(err)

    def test_invalid_date_rejected(self):
        value, err = clean_date("2024-13-45")
        self.assertIsNone(value)
        self.assertIsNotNone(err)

    def test_missing_date_rejected(self):
        value, err = clean_date("")
        self.assertIsNone(value)
        self.assertEqual(err, "signup_date missing")


if __name__ == "__main__":
    unittest.main()
