import json
import os
import tempfile
import unittest
from datetime import date, timedelta

import panos_output
from panos_version import parse_dotted

PAST = (date.today() - timedelta(days=365)).isoformat()
RECENT_PAST = (date.today() - timedelta(days=30)).isoformat()
FUTURE = (date.today() + timedelta(days=365)).isoformat()

TABLE = {
    "11.0": {"standard": PAST, "extended": None},
    "10.1": {"standard": PAST, "extended": RECENT_PAST},
    "10.2": {"standard": RECENT_PAST, "extended": FUTURE},
    "12.1": {"standard": FUTURE, "extended": FUTURE},
    "9.9": {"standard": None, "extended": None},
}


def label(raw):
    return panos_output.markdown_label(
        panos_output.make_record(parse_dotted(raw), "vm-series", "byol", TABLE)
    )


class TestEolState(unittest.TestCase):
    def test_past_standard_with_no_extended_is_eol(self):
        is_eol, standard, extended = panos_output.eol_state(
            parse_dotted("11.0.4-h6"), TABLE
        )
        self.assertTrue(is_eol)
        self.assertEqual(standard, PAST)
        self.assertIsNone(extended)

    def test_before_standard_is_not_eol(self):
        is_eol, _, _ = panos_output.eol_state(parse_dotted("12.1.9"), TABLE)
        self.assertFalse(is_eol)

    def test_unknown_train_is_none_not_false(self):
        """An absent train must not be reported as supported.

        False and None both look falsy, so this is the case where a careless
        `if not eol` would quietly present an unknown version as current.
        """
        is_eol, standard, _ = panos_output.eol_state(parse_dotted("7.1.0"), TABLE)
        self.assertIsNone(is_eol)
        self.assertIsNone(standard)

    def test_null_standard_date_is_unknown(self):
        is_eol, _, _ = panos_output.eol_state(parse_dotted("9.9.1"), TABLE)
        self.assertIsNone(is_eol)


class TestMarkdownLabel(unittest.TestCase):
    def test_supported_version_is_bare(self):
        self.assertEqual(label("12.1.9"), "12.1.9")

    def test_unknown_train_is_bare(self):
        self.assertEqual(label("7.1.0"), "7.1.0")

    def test_past_standard_and_extended_is_plain_eol(self):
        self.assertEqual(label("10.1.14-h8"), "10.1.14-h8 (EOL)")

    def test_no_extended_support_offered_is_plain_eol(self):
        self.assertEqual(label("11.0.4-h6"), "11.0.4-h6 (EOL)")

    def test_extended_support_still_running_is_qualified(self):
        """The 10.2 case: standard support is over but extended is not.

        A bare "(EOL)" here would overstate the position for the single most
        widely deployed train in the listings.
        """
        self.assertEqual(
            label("10.2.14"), f"10.2.14 (EOL, extended support to {FUTURE})"
        )


class TestShippedEolFile(unittest.TestCase):
    def test_every_train_parses_as_a_date(self):
        for train, entry in panos_output.load_eol().items():
            for key in ("standard", "extended"):
                value = entry.get(key)
                if value is not None:
                    date.fromisoformat(value)  # raises if malformed
            self.assertIsNotNone(entry.get("standard"), f"{train} has no standard date")


class TestWriteJsonIfChanged(unittest.TestCase):
    def test_unchanged_payload_keeps_the_original_timestamp(self):
        """Four empty commits a day would bury the signal this repo exists for.

        A commit here should mean a version actually appeared or disappeared,
        so an unchanged payload must not be rewritten with a fresh timestamp.
        """
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "aws.json")
            payload = {"schema_version": 1, "generated": None, "images": [{"v": 1}]}
            self.assertTrue(panos_output.write_json_if_changed(path, dict(payload)))
            first = json.load(open(path))["generated"]

            self.assertFalse(panos_output.write_json_if_changed(path, dict(payload)))
            self.assertEqual(json.load(open(path))["generated"], first)

            moved = {"schema_version": 1, "generated": None, "images": [{"v": 2}]}
            self.assertTrue(panos_output.write_json_if_changed(path, moved))


if __name__ == "__main__":
    unittest.main()
