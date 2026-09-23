#! /usr/bin/env python3

"""Turn the two gcloud image listings into gcp.md and data/gcp.json.

Usage: gcp-processing.py <vmseries-list> <panorama-list>

Each input is one image name per line, as produced by
`gcloud compute images list --project paloaltonetworksgcp-public`.
"""

import logging
import re
import sys

import panos_output
from panos_version import ParseError, parse_gcp, sort_key

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# Image-name prefix -> (product, CPU model, licence). Order matters only in
# that the first match wins, and every prefix here is unambiguous.
VMSERIES_FAMILIES = [
    ("vmseries-flex-byol-", "vm-series", "flex", "byol"),
    ("vmseries-flex-bundle1-", "vm-series", "flex", "bundle1"),
    ("vmseries-flex-bundle2-", "vm-series", "flex", "bundle2"),
    ("vmseries-flex-bundle3-", "vm-series", "flex", "bundle3"),
    ("vmseries-byol-", "vm-series", "fixed", "byol"),
    ("vmseries-bundle1-", "vm-series", "fixed", "bundle1"),
    ("vmseries-bundle2-", "vm-series", "fixed", "bundle2"),
]

# Panorama has accumulated three naming styles over the years:
#   panorama-811            the original
#   panorama-byol-1000      the byol-infix era
#   panorama-gcp-11-2-6     the current dashed form
# The first two pack the version the same way VM-Series does; the third
# spells it out, so it is handled separately.
PANORAMA_PACKED = re.compile(r"^panorama-(?:byol-)?(\d.*)$")
PANORAMA_DASHED = re.compile(r"^panorama-gcp-(\d+)-(\d+)-(\d+)$")


def classify_vmseries(name):
    for prefix, product, cpu, licence in VMSERIES_FAMILIES:
        if name.startswith(prefix):
            return product, cpu, licence, name[len(prefix):]
    return None


def read_names(path):
    with open(path) as handle:
        return [line.strip() for line in handle if line.strip()]


def collect_vmseries(names, eol_table, skipped):
    records = []
    for name in names:
        classified = classify_vmseries(name)
        if not classified:
            skipped.append((name, "no known image family"))
            continue
        product, cpu, licence, suffix = classified
        try:
            version = parse_gcp(suffix)
        except ParseError as error:
            skipped.append((name, str(error)))
            continue
        records.append(
            panos_output.make_record(
                version, product, licence, eol_table, cpu=cpu, image_name=name
            )
        )
    return records


def collect_panorama(names, eol_table, skipped):
    records = []
    for name in names:
        dashed = PANORAMA_DASHED.match(name)
        if dashed:
            major, minor, patch = dashed.groups()
            version = parse_gcp(f"{major}{minor}{patch}")
        else:
            packed = PANORAMA_PACKED.match(name)
            if not packed:
                skipped.append((name, "unrecognised Panorama image name"))
                continue
            try:
                version = parse_gcp(packed.group(1))
            except ParseError as error:
                skipped.append((name, str(error)))
                continue
        records.append(
            panos_output.make_record(
                version, "panorama", "byol", eol_table, cpu=None, image_name=name
            )
        )
    return records


def section(records, cpu, licence):
    """The distinct versions in one section, oldest first."""
    matching = [r for r in records if r.get("cpu") == cpu and r["licence"] == licence]
    seen = {}
    for record in matching:
        seen.setdefault(record["version"], record)
    return sorted(seen.values(), key=lambda r: (r["major"], r["minor"], r["patch"], r["hotfix"] or 0))


def render_markdown(vmseries, panorama):
    out = ["\n# GCP\n"]
    out.append(
        "\nImage names pack the version with no separators: `10.2.0` is "
        "`1020`, and a hotfix is appended with an `h`, so `10.2.10-h9` is "
        "`10210h9`. Each version below is followed by the image name to use.\n"
    )
    out.append(panos_output.EOL_LEGEND)

    layout = [
        ("Flexible CPU", "flex", [
            ("BYOL", "byol"),
            ("PAYG Bundle 1", "bundle1"),
            ("PAYG Bundle 2", "bundle2"),
            ("PAYG Bundle 3", "bundle3"),
        ]),
        ("Fixed CPU", "fixed", [
            ("BYOL", "byol"),
            ("PAYG Bundle 1", "bundle1"),
            ("PAYG Bundle 2", "bundle2"),
        ]),
    ]
    for heading, cpu, licences in layout:
        out.append(f"\n## {heading}\n")
        for label, licence in licences:
            out.append(f"\n### {label}\n")
            rows = section(vmseries, cpu, licence)
            if not rows:
                out.append("\nNone published.\n")
                continue
            out.append("\n| Version | Image name |\n| --- | --- |\n")
            for record in rows:
                out.append(
                    f"| {panos_output.markdown_label(record)} "
                    f"| `{record['image_name']}` |\n"
                )

    out.append("\n## Panorama\n")
    rows = section(panorama, None, "byol")
    out.append("\n| Version | Image name |\n| --- | --- |\n")
    for record in rows:
        out.append(
            f"| {panos_output.markdown_label(record)} "
            f"| `{record['image_name']}` |\n"
        )
    return "".join(out)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: gcp-processing.py <vmseries-list> <panorama-list>")

    eol_table = panos_output.load_eol()
    skipped = []
    vmseries = collect_vmseries(read_names(sys.argv[1]), eol_table, skipped)
    panorama = collect_panorama(read_names(sys.argv[2]), eol_table, skipped)

    # Images that did not parse are logged rather than dropped in silence:
    # a new naming scheme should be visible in the run log, not just absent
    # from the listings.
    for name, reason in skipped:
        logging.warning("skipped %s: %s", name, reason)

    if not vmseries:
        sys.exit("no VM-Series images parsed - refusing to publish an empty listing")

    records = vmseries + panorama
    if panos_output.write_text_if_changed("gcp.md", render_markdown(vmseries, panorama)):
        logging.info("gcp.md updated")
    path, changed = panos_output.write_provider_json("gcp", records)
    logging.info("%s %s", path, "updated" if changed else "unchanged")
    path, changed = panos_output.write_combined()
    logging.info("%s %s", path, "updated" if changed else "unchanged")
    logging.info("%d images parsed, %d skipped", len(records), len(skipped))


if __name__ == "__main__":
    main()
