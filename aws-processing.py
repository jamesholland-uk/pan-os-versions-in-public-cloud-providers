#! /usr/bin/env python3

"""Query AWS for PAN-OS AMIs and write aws.md, aws/<licence>/<version>.md and data/aws.json."""

import logging
import os
import re
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

import panos_output
from panos_version import ParseError, parse_dotted

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# Product codes from the Palo Alto documentation:
# https://docs.paloaltonetworks.com/vm-series/11-0/vm-series-deployment/set-up-the-vm-series-firewall-on-aws/deploy-the-vm-series-firewall-on-aws/obtain-the-ami/get-amazon-machine-image-ids
PRODUCT_CODES = {
    "6njl1pau431dv1qxipg63mvah": ("vm-series", "byol"),
    "e9yfvyj3uag5uo5j2hjikv74n": ("vm-series", "bundle1"),
    "hd44w1chf26uv4p52cdynb2o": ("vm-series", "bundle2"),
    # "VM-Series - Advanced security subscriptions (PAYG)" - the AWS
    # equivalent of the bundle3 SKU already listed for Azure and GCP.
    "1rfiaqne1ae8ivks1wh0xyx4g": ("vm-series", "bundle3"),
    # Prisma AIRS (AI Runtime Security): the same PAN-OS image licensed as a
    # superset of VM-Series, still sold as its own marketplace listing.
    "b261y39exndwe1ltro1tqpeog": ("airs", "byol"),
    "eclz7j04vu9lf8ont8ta3n17o": ("panorama", "byol"),
}
NAME_FILTERS = [
    "PA-VM-AWS*",
    "Panorama-AWS*",
    # Older AIRS AMIs only; newer ones are named PA-VM-AWS-* like VM-Series,
    # and the product code is what tells them apart.
    "AI-Runtime-Security-AWS*",
    "PA-AI-Runtime-Security-AWS*",
]

# AMI names are <prefix>-<version>-<suffix>, where the suffix is either a UUID
# per listing or a marketplace product token:
#   PA-VM-AWS-11.1.10-h25-7064e142-2859-40a4-ab62-8b0996b842e9
#   PA-VM-AWS-11.1.15-prod-slv6ybyrjrxnm
#   Panorama-AWS-11.1.4-h13-f264c750-1102-41c9-a14d-b54ea51780e4
#   PA-AI-Runtime-Security-AWS-11.2.4-h1-prod-v7k5pwjb72ea2
AMI_NAME = re.compile(
    r"^(?:PA-VM-AWS|Panorama-AWS|(?:PA-)?AI-Runtime-Security-AWS)"
    r"-(\d+\.\d+\.\d+(?:-h\d+)?)(?:-|$)"
)

# Directory under aws/ for each (product, licence). Kept as-is so that links
# published over the last four years keep working.
DIRECTORIES = {
    ("vm-series", "byol"): "byol",
    ("vm-series", "bundle1"): "bundle1",
    ("vm-series", "bundle2"): "bundle2",
    ("vm-series", "bundle3"): "bundle3",
    ("airs", "byol"): "airs",
    ("panorama", "byol"): "panorama",
}
SECTIONS = [
    ("BYOL", ("vm-series", "byol")),
    ("PAYG Bundle 1", ("vm-series", "bundle1")),
    ("PAYG Bundle 2", ("vm-series", "bundle2")),
    ("PAYG Advanced Security (Bundle 3)", ("vm-series", "bundle3")),
    ("Prisma AIRS (AI Runtime Security) BYOL", ("airs", "byol")),
    ("Panorama", ("panorama", "byol")),
]


# A region the account cannot reach should cost one fast failure, not sixty
# seconds of connect timeouts and retries.
REGION_CONFIG = Config(
    retries={"max_attempts": 2, "mode": "standard"},
    connect_timeout=5,
    read_timeout=20,
)


def enable_new_regions(session):
    """Opt the account in to any region it has not enabled yet.

    AWS launches new regions as opt-in, so without this every new region is
    silently missing until someone notices. Enabling takes minutes to hours;
    a region still enabling is picked up by a later run. Needs only
    account:ListRegions and account:EnableRegion - without them this logs
    and carries on, so coverage never gets worse than the account allows.
    AWS also throttles how many regions can be enabling at once, so a
    refused region is simply retried on the next run.
    """
    client = session.client("account", region_name="us-east-1", config=REGION_CONFIG)
    try:
        pages = client.get_paginator("list_regions").paginate(
            RegionOptStatusContains=["DISABLED"]
        )
        disabled = [r["RegionName"] for page in pages for r in page["Regions"]]
    except (ClientError, BotoCoreError) as error:
        logging.warning("could not list regions to enable: %s", error)
        return
    for name in disabled:
        try:
            client.enable_region(RegionName=name)
            logging.info("enabling region %s", name)
        except (ClientError, BotoCoreError) as error:
            logging.warning("could not enable region %s yet: %s", name, error)


def all_regions(session):
    """Return (queryable, not_opted_in) region names.

    describe_regions() defaults to the account's *enabled* regions, which is
    why this project published only the 17 default-on regions for years.
    AllRegions=True lists everything AWS offers and tags each with an opt-in
    status, so the ones the account genuinely cannot query are named in the
    output instead of being invisibly absent. If the account opts in to more
    later, coverage widens with no change here.
    """
    client = session.client("ec2", region_name="us-east-1", config=REGION_CONFIG)
    queryable, not_opted_in = [], []
    for region in client.describe_regions(AllRegions=True)["Regions"]:
        target = (
            not_opted_in if region["OptInStatus"] == "not-opted-in" else queryable
        )
        target.append(region["RegionName"])
    return sorted(queryable), sorted(not_opted_in)


def collect(session, regions, skipped, unknown_codes):
    """Return {(product, licence, version_str): {region: ami_id}} and the
    regions that could not be reached."""
    found = {}
    versions = {}
    created = {}
    unreachable = []

    for region in regions:
        ec2 = session.client("ec2", region_name=region, config=REGION_CONFIG)
        try:
            images = []
            for name_filter in NAME_FILTERS:
                # "aws-marketplace" rather than an owner account ID: Marketplace
                # publishes from a different account in each opt-in region
                # (971815773857 in il-central-1, 939706979954 in af-south-1),
                # so a fixed ID finds nothing there. The product code below is
                # what identifies a Palo Alto listing.
                images += ec2.describe_images(
                    Owners=["aws-marketplace"],
                    Filters=[{"Name": "name", "Values": [name_filter]}],
                )["Images"]
        except (ClientError, BotoCoreError) as error:
            unreachable.append(region)
            logging.warning("%s unreachable: %s", region, type(error).__name__)
            continue

        for ami in images:
            product_codes = ami.get("ProductCodes")
            if not product_codes:
                continue
            code = product_codes[0]["ProductCodeId"]
            if code not in PRODUCT_CODES:
                # A marketplace listing this project does not track. Recorded
                # so that a new listing shows up in the run log rather than
                # quietly going unpublished, which is how AWS Bundle 3 was
                # missed for years.
                unknown_codes.setdefault(code, ami["Name"])
                continue
            match = AMI_NAME.match(ami["Name"])
            if not match:
                skipped.append((f"{region}/{ami['Name']}", "unrecognised AMI name"))
                continue
            try:
                version = parse_dotted(match.group(1))
            except ParseError as error:
                skipped.append((f"{region}/{ami['Name']}", str(error)))
                continue
            product, licence = PRODUCT_CODES[code]
            key = (product, licence, str(version))
            # Marketplace occasionally republishes a version. The newest AMI
            # wins, so the choice never depends on the order the API returns.
            if ami["CreationDate"] < created.get((key, region), ""):
                continue
            created[(key, region)] = ami["CreationDate"]
            versions[key] = version
            found.setdefault(key, {})[region] = ami["ImageId"]

    return found, versions, unreachable


def build_records(found, versions, eol_table):
    records = []
    for key, amis in found.items():
        product, licence, _ = key
        records.append(
            panos_output.make_record(
                versions[key],
                product,
                licence,
                eol_table,
                product_code=next(
                    code for code, value in PRODUCT_CODES.items()
                    if value == (product, licence)
                ),
                amis=dict(sorted(amis.items())),
            )
        )
    records.sort(
        key=lambda r: (
            r["product"], r["licence"],
            r["major"], r["minor"], r["patch"], r["hotfix"] or 0,
        )
    )
    return records


def render_index(records, covered, uncovered):
    out = ["\n# AWS\n"]
    out.append(
        f"\nAMI IDs are region-specific. Each version below links to its IDs "
        f"across the {len(covered)} regions this project covers.\n"
    )
    out.append(panos_output.EOL_LEGEND)
    for heading, key in SECTIONS:
        directory = DIRECTORIES[key]
        out.append(f"\n### {heading}\n\n")
        rows = [r for r in records if (r["product"], r["licence"]) == key]
        if not rows:
            out.append("None published.\n")
            continue
        for record in rows:
            out.append(
                f"- [{panos_output.markdown_label(record)}]"
                f"(aws/{directory}/{record['version']}.md) "
                f"- {len(record['amis'])} regions\n"
            )
    if uncovered:
        out.append("\n## Regions not covered\n")
        out.append(
            "\nNo AMI IDs are collected for the regions below, because the "
            "AWS account behind this project has not enabled them yet (new "
            "regions are enabled automatically, which can take a few hours) "
            "or could not reach them on this run. This is a limit of the "
            "account doing the querying, not a statement that Palo Alto "
            "Networks does not publish there.\n\n"
        )
        out.append("".join(f"- `{region}`\n" for region in uncovered))
    out.append("\n")
    return "".join(out)


def render_version_page(record):
    out = [f"\n # {record['version']}\n"]
    for region, ami in record["amis"].items():
        out.append(f"- {region}: {ami}\n")
    out.append("\n[Go back to aws.md](../../aws.md) \n")
    return "".join(out)


def sync_version_pages(records):
    """Write the per-version pages, then delete only what is genuinely gone.

    The previous version emptied every directory before fetching anything, so
    a mid-run failure could commit the deletion of the whole dataset. Nothing
    is removed here until the replacement content is already in hand.
    """
    wanted = {}
    for record in records:
        directory = DIRECTORIES[(record["product"], record["licence"])]
        wanted[os.path.join("aws", directory, f"{record['version']}.md")] = (
            render_version_page(record)
        )

    written = 0
    for path, text in wanted.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if panos_output.write_text_if_changed(path, text):
            written += 1

    removed = 0
    for directory in set(DIRECTORIES.values()):
        folder = os.path.join("aws", directory)
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and name.endswith(".md") and path not in wanted:
                os.remove(path)
                removed += 1
    return written, removed


def main():
    session = boto3.Session()
    eol_table = panos_output.load_eol()
    skipped = []

    unknown_codes = {}
    enable_new_regions(session)
    queryable, not_opted_in = all_regions(session)
    found, versions, unreachable = collect(
        session, queryable, skipped, unknown_codes
    )

    for name, reason in skipped:
        logging.warning("skipped %s: %s", name, reason)
    for code, example in unknown_codes.items():
        logging.warning("untracked product code %s, e.g. %s", code, example)

    if not found:
        sys.exit("no AMIs found - refusing to publish an empty listing")

    covered = [r for r in queryable if r not in unreachable]
    uncovered = sorted(not_opted_in + unreachable)
    records = build_records(found, versions, eol_table)

    if panos_output.write_text_if_changed(
        "aws.md", render_index(records, covered, uncovered)
    ):
        logging.info("aws.md updated")
    written, removed = sync_version_pages(records)
    logging.info("version pages: %d written, %d removed", written, removed)
    path, changed = panos_output.write_provider_json("aws", records)
    logging.info("%s %s", path, "updated" if changed else "unchanged")
    path, changed = panos_output.write_combined()
    logging.info("%s %s", path, "updated" if changed else "unchanged")
    logging.info(
        "%d versions across %d regions (%d not covered)",
        len(records), len(covered), len(uncovered),
    )


if __name__ == "__main__":
    main()
