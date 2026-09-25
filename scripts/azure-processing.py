#! /usr/bin/env python3

"""Query the Azure marketplace image versions and write azure/README.md and data/azure.json."""

import logging
import os
import sys

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

import panos_output
from panos_version import ParseError, parse_azure

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
# The SDK logs every HTTP request and response header at INFO.
logging.getLogger("azure").setLevel(logging.WARNING)

PUBLISHER = "PaloAltoNetworks"
LOCATION = "eastus"

# (offer, sku, product, CPU model, licence)
CATALOGUE = [
    ("vmseries-flex", "byol", "vm-series", "flex", "byol"),
    ("vmseries-flex", "bundle1", "vm-series", "flex", "bundle1"),
    ("vmseries-flex", "bundle2", "vm-series", "flex", "bundle2"),
    ("vmseries-flex", "bundle3", "vm-series", "flex", "bundle3"),
    ("vmseries1", "byol", "vm-series", "fixed", "byol"),
    ("vmseries1", "bundle1", "vm-series", "fixed", "bundle1"),
    ("vmseries1", "bundle2", "vm-series", "fixed", "bundle2"),
    # Prisma AIRS (AI Runtime Security): the same PAN-OS image licensed as a
    # superset of VM-Series, still sold as its own offer.
    ("airs-flex", "airs-byol", "airs", "flex", "byol"),
    ("panorama", "byol", "panorama", None, "byol"),
]


def collect(compute_client, eol_table, skipped):
    records = []
    for offer, sku, product, cpu, licence in CATALOGUE:
        images = compute_client.virtual_machine_images.list(
            LOCATION, PUBLISHER, offer, sku
        )
        for image in images:
            try:
                version = parse_azure(image.name)
            except ParseError as error:
                skipped.append((f"{offer}/{sku}/{image.name}", str(error)))
                continue
            records.append(
                panos_output.make_record(
                    version,
                    product,
                    licence,
                    eol_table,
                    cpu=cpu,
                    offer=offer,
                    sku=sku,
                    image_version=image.name,
                )
            )
    return records


def section(records, offer, sku):
    matching = [r for r in records if r["offer"] == offer and r["sku"] == sku]
    seen = {}
    for record in matching:
        seen.setdefault(record["version"], record)
    return sorted(
        seen.values(),
        key=lambda r: (r["major"], r["minor"], r["patch"], r["hotfix"] or 0),
    )


def render_markdown(records, unparsed):
    out = ["\n# Azure\n"]
    out.append(
        "\nAzure packs the hotfix into the third component of the image "
        "version, zero-padded to two digits, and then strips leading zeros: "
        "`11.2.7-h13` is published as `11.2.713` and `11.0.4-h6` as "
        "`11.0.406`. Deploy using the **image version** column, not the "
        "PAN-OS version.\n"
    )
    out.append(panos_output.EOL_LEGEND)

    layout = [
        ("Flexible CPU (Offer: `vmseries-flex`)", "vmseries-flex", [
            ("BYOL (SKU: `byol`)", "byol"),
            ("PAYG Bundle 1 (SKU: `bundle1`)", "bundle1"),
            ("PAYG Bundle 2 (SKU: `bundle2`)", "bundle2"),
            ("PAYG Bundle 3 (SKU: `bundle3`)", "bundle3"),
        ]),
        ("Fixed CPU (Offer: `vmseries1`)", "vmseries1", [
            ("BYOL (SKU: `byol`)", "byol"),
            ("PAYG Bundle 1 (SKU: `bundle1`)", "bundle1"),
            ("PAYG Bundle 2 (SKU: `bundle2`)", "bundle2"),
        ]),
        ("Prisma AIRS / AI Runtime Security (Offer: `airs-flex`)", "airs-flex", [
            ("BYOL (SKU: `airs-byol`)", "airs-byol"),
        ]),
        ("Panorama (Offer: `panorama`)", "panorama", [
            ("BYOL (SKU: `byol`)", "byol"),
        ]),
    ]
    for heading, offer, skus in layout:
        out.append(f"\n## {heading}\n")
        for label, sku in skus:
            out.append(f"\n### {label}\n")
            rows = section(records, offer, sku)
            if not rows:
                out.append("\nNone published.\n")
                continue
            out.append("\n| PAN-OS version | Image version |\n| --- | --- |\n")
            for record in rows:
                out.append(
                    f"| {panos_output.markdown_label(record)} "
                    f"| `{record['image_version']}` |\n"
                )

    if unparsed:
        out.append("\n## Unrecognised image versions\n")
        out.append(
            "\nPublished by Azure but not in a form this project can map to a "
            "PAN-OS version. Listed so they are visible rather than silently "
            "dropped.\n\n"
        )
        for name, reason in unparsed:
            out.append(f"- `{name}` - {reason}\n")
    return "".join(out)


def main():
    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    if not subscription_id:
        sys.exit("AZURE_SUBSCRIPTION_ID is not set")

    compute_client = ComputeManagementClient(
        DefaultAzureCredential(), subscription_id
    )

    eol_table = panos_output.load_eol()
    skipped = []
    records = collect(compute_client, eol_table, skipped)

    for name, reason in skipped:
        logging.warning("skipped %s: %s", name, reason)

    if not records:
        sys.exit("no images parsed - refusing to publish an empty listing")

    if panos_output.write_text_if_changed(
        "azure/README.md", render_markdown(records, skipped)
    ):
        logging.info("azure/README.md updated")
    path, changed = panos_output.write_provider_json("azure", records)
    logging.info("%s %s", path, "updated" if changed else "unchanged")
    path, changed = panos_output.write_combined()
    logging.info("%s %s", path, "updated" if changed else "unchanged")
    logging.info("%d images parsed, %d skipped", len(records), len(skipped))


if __name__ == "__main__":
    main()
