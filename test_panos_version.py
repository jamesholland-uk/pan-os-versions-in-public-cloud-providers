"""Regression tests for PAN-OS version parsing.

Version-string handling is the one place in this project where a bug
silently publishes a version that does not exist, so the cases that were
actually wrong in production are pinned here by name.
"""

import unittest

from panos_version import ParseError, parse_azure, parse_dotted, parse_gcp, sort_key


class TestParseDotted(unittest.TestCase):
    """AWS publishes the canonical form already."""

    def test_plain(self):
        self.assertEqual(str(parse_dotted("11.2.12")), "11.2.12")

    def test_hotfix(self):
        self.assertEqual(str(parse_dotted("11.2.7-h18")), "11.2.7-h18")

    def test_two_digit_everything(self):
        self.assertEqual(str(parse_dotted("11.1.10-h25")), "11.1.10-h25")

    def test_components(self):
        version = parse_dotted("10.2.10-h9")
        self.assertEqual(
            (version.major, version.minor, version.patch, version.hotfix),
            (10, 2, 10, 9),
        )

    def test_raw_is_kept(self):
        self.assertEqual(parse_dotted("11.2.7-h18").raw, "11.2.7-h18")

    def test_rejects_rubbish(self):
        with self.assertRaises(ParseError):
            parse_dotted("PA-VM-AWS")


class TestParseGcp(unittest.TestCase):
    """GCP packs major.minor.patch together and appends hXX."""

    def test_multi_digit_hotfix_digits_are_not_repeated(self):
        """The bug that shipped: every hotfix digit was the first one.

        The old ver_format() appended ver[find("h") + 1] once per digit, so
        10210h12 and 10210h14 both rendered as 10.2.10-h11 - which is why
        gcp.md listed 10.2.10-h11 twice.
        """
        self.assertEqual(str(parse_gcp("10210h12")), "10.2.10-h12")
        self.assertEqual(str(parse_gcp("10210h14")), "10.2.10-h14")
        self.assertEqual(str(parse_gcp("11110h25")), "11.1.10-h25")

    def test_single_digit_hotfix(self):
        self.assertEqual(str(parse_gcp("10210h9")), "10.2.10-h9")

    def test_repeated_digit_hotfix_still_right(self):
        """h11 was correct before only by luck; it must stay correct."""
        self.assertEqual(str(parse_gcp("10210h11")), "10.2.10-h11")

    def test_one_digit_major(self):
        self.assertEqual(str(parse_gcp("8125h1")), "8.1.25-h1")
        self.assertEqual(str(parse_gcp("9016h5")), "9.0.16-h5")
        self.assertEqual(str(parse_gcp("9116h3")), "9.1.16-h3")
        self.assertEqual(str(parse_gcp("810")), "8.1.0")

    def test_two_digit_major(self):
        self.assertEqual(str(parse_gcp("1000")), "10.0.0")
        self.assertEqual(str(parse_gcp("10012h3")), "10.0.12-h3")
        self.assertEqual(str(parse_gcp("10110")), "10.1.10")
        self.assertEqual(str(parse_gcp("10114h6")), "10.1.14-h6")
        self.assertEqual(str(parse_gcp("11115")), "11.1.15")
        self.assertEqual(str(parse_gcp("1219")), "12.1.9")

    def test_raw_is_kept(self):
        """Terraform needs the packed form back, not the canonical one."""
        self.assertEqual(parse_gcp("10210h9").raw, "10210h9")

    def test_rejects_too_short(self):
        with self.assertRaises(ParseError):
            parse_gcp("81")

    def test_rejects_rubbish(self):
        with self.assertRaises(ParseError):
            parse_gcp("flex-byol")


class TestParseAzure(unittest.TestCase):
    """Azure packs patch and a zero-padded hotfix into the third component."""

    def test_plain_patch(self):
        self.assertEqual(str(parse_azure("11.1.15")), "11.1.15")
        self.assertEqual(str(parse_azure("11.2.5")), "11.2.5")
        self.assertEqual(str(parse_azure("12.1.4")), "12.1.4")

    def test_packed_hotfix(self):
        """Each of these is cross-checked against the AWS dotted form."""
        self.assertEqual(str(parse_azure("11.1.1025")), "11.1.10-h25")
        self.assertEqual(str(parse_azure("11.0.406")), "11.0.4-h6")
        self.assertEqual(str(parse_azure("11.2.501")), "11.2.5-h1")
        self.assertEqual(str(parse_azure("11.2.303")), "11.2.3-h3")
        self.assertEqual(str(parse_azure("10.2.1009")), "10.2.10-h9")
        self.assertEqual(str(parse_azure("11.1.1305")), "11.1.13-h5")
        self.assertEqual(str(parse_azure("10.1.1409")), "10.1.14-h9")
        self.assertEqual(str(parse_azure("11.2.713")), "11.2.7-h13")
        self.assertEqual(str(parse_azure("12.1.405")), "12.1.4-h5")

    def test_raw_is_kept(self):
        """Terraform needs 11.2.713 to deploy, not 11.2.7-h13."""
        self.assertEqual(parse_azure("11.2.713").raw, "11.2.713")

    def test_flags_implausible_split(self):
        """11.1.4013 appears in Azure's Panorama list and splits to 11.1.40-h13.

        PAN-OS 11.1 has no patch 40, so rather than publish a version that
        does not exist we refuse it and let the caller keep the raw value.
        """
        with self.assertRaises(ParseError):
            parse_azure("11.1.4013")

    def test_rejects_rubbish(self):
        with self.assertRaises(ParseError):
            parse_azure("vmseries-flex")


class TestSortKey(unittest.TestCase):
    def test_hotfixes_sort_numerically(self):
        """The bug that shipped: semver compared "h9" > "h14" lexically.

        aws.md listed 10.2.10-h9 below -h12 and -h14, presenting the oldest
        hotfix as the newest.
        """
        versions = [parse_dotted(v) for v in ("10.2.10-h12", "10.2.10-h14", "10.2.10-h9")]
        self.assertEqual(
            [str(v) for v in sorted(versions, key=sort_key)],
            ["10.2.10-h9", "10.2.10-h12", "10.2.10-h14"],
        )

    def test_hotfix_sorts_after_its_base_release(self):
        """semver put 11.1.13-h5 before 11.1.13; a hotfix is newer."""
        versions = [parse_dotted(v) for v in ("11.1.13-h5", "11.1.13")]
        self.assertEqual(
            [str(v) for v in sorted(versions, key=sort_key)],
            ["11.1.13", "11.1.13-h5"],
        )

    def test_full_ordering(self):
        raw = [
            "11.1.15", "10.2.10-h9", "12.1.9", "9.1.16", "11.1.13-h5",
            "10.2.10-h14", "11.2.5", "11.1.6-h35", "12.1.7",
        ]
        self.assertEqual(
            [str(v) for v in sorted((parse_dotted(r) for r in raw), key=sort_key)],
            [
                "9.1.16", "10.2.10-h9", "10.2.10-h14", "11.1.6-h35",
                "11.1.13-h5", "11.1.15", "11.2.5", "12.1.7", "12.1.9",
            ],
        )

    def test_sorts_across_providers(self):
        """The same release from three clouds must collate as one version."""
        versions = [
            parse_gcp("11110h25"),
            parse_azure("11.1.1025"),
            parse_dotted("11.1.10-h25"),
        ]
        self.assertEqual({str(v) for v in versions}, {"11.1.10-h25"})
        self.assertEqual(len({sort_key(v) for v in versions}), 1)


class TestTrain(unittest.TestCase):
    def test_train(self):
        self.assertEqual(parse_dotted("11.2.7-h18").train, "11.2")
        self.assertEqual(parse_gcp("8125h1").train, "8.1")


if __name__ == "__main__":
    unittest.main()
