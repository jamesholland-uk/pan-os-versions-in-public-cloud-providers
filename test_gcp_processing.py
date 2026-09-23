"""Tests for the GCP image-name handling that sits outside panos_version."""

import importlib.util
import unittest

# The processor's file name has a hyphen, so it cannot be imported normally.
_spec = importlib.util.spec_from_file_location("gcp_processing", "gcp-processing.py")
gcp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gcp)


def panorama(*names):
    skipped = []
    records = gcp.collect_panorama(list(names), {}, skipped)
    return [r["version"] for r in records], skipped


class TestCollectPanorama(unittest.TestCase):
    def test_all_three_naming_styles(self):
        versions, skipped = panorama(
            "panorama-811", "panorama-byol-1000", "panorama-gcp-11-2-6"
        )
        self.assertEqual(versions, ["8.1.1", "10.0.0", "11.2.6"])
        self.assertEqual(skipped, [])

    def test_dashed_hotfix(self):
        versions, skipped = panorama("panorama-gcp-11-2-7-h18")
        self.assertEqual(versions, ["11.2.7-h18"])
        self.assertEqual(skipped, [])

    def test_implausible_dashed_name_is_skipped_not_fatal(self):
        versions, skipped = panorama("panorama-gcp-11-2-40", "panorama-gcp-11-2-6")
        self.assertEqual(versions, ["11.2.6"])
        self.assertEqual(len(skipped), 1)


if __name__ == "__main__":
    unittest.main()
