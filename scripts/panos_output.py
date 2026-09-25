"""Shared output handling: EOL lookup, JSON emission, combined dataset.

The Markdown pages and the JSON files are generated from the same list of
records so the two cannot drift apart.
"""

import json
import os
from datetime import date, datetime, timezone

SCHEMA_VERSION = 1
PROVIDERS = ("aws", "azure", "gcp")
DATA_DIR = "data"
EOL_FILE = os.path.join(os.path.dirname(__file__), "eol.json")


def load_eol(path=EOL_FILE):
    """Return a {train: {"standard": date, "extended": date|None}} map.

    A train that is absent, or present with a null standard date, is simply
    unknown - never assumed supported.
    """
    if not os.path.exists(path):
        return {}
    with open(path) as handle:
        return json.load(handle).get("trains", {})


def eol_state(version, eol_table):
    """Return (is_eol, standard_date, extended_date).

    Palo Alto Networks publishes two dates per train. Standard support ending
    is what makes a version unsuitable for a new deployment, so that is what
    drives the flag; the extended date is carried alongside because for a
    train like 10.2 - standard support ended 2025-08-27, extended support
    running to 2027-03-31 - a bare "EOL" would overstate the position.

    is_eol is None when no date is recorded.
    """
    entry = eol_table.get(version.train) or {}
    standard = entry.get("standard")
    if not standard:
        return None, None, entry.get("extended")
    return date.fromisoformat(standard) <= date.today(), standard, entry.get("extended")


def make_record(version, product, licence, eol_table, **provider_fields):
    """Build one image record.

    Always carries both identifiers: `version` is the canonical PAN-OS string
    a human reads, and the provider fields carry the raw value Terraform has
    to hand back to the cloud.
    """
    is_eol, eol_date, extended = eol_state(version, eol_table)
    return {
        "version": str(version),
        "major": version.major,
        "minor": version.minor,
        "patch": version.patch,
        "hotfix": version.hotfix,
        "train": version.train,
        "product": product,
        "licence": licence,
        "eol": is_eol,
        "eol_date": eol_date,
        "eol_extended_date": extended,
        **provider_fields,
    }


def markdown_label(record):
    """Version as it appears in the Markdown listings."""
    if not record["eol"]:
        return record["version"]
    extended = record["eol_extended_date"]
    if extended and date.fromisoformat(extended) > date.today():
        return f"{record['version']} (EOL, extended support to {extended})"
    return f"{record['version']} (EOL)"


EOL_LEGEND = (
    "\n> Versions marked **(EOL)** are past Palo Alto Networks' published "
    "end-of-standard-support date for that release train and should not be "
    "used for new deployments. Where extended support is still running, the "
    "date is given. Trains with no published date are left unmarked. See the "
    "[end-of-life summary](https://www.paloaltonetworks.com/services/support/"
    "end-of-life-announcements/end-of-life-summary) for the authoritative "
    "list and the conditions attached to extended support.\n"
)


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json_if_changed(path, payload, key="images"):
    """Write only when the data itself has moved.

    Part of this repo's value is that a commit means a version actually
    appeared or disappeared. Stamping a fresh timestamp on every 6-hourly run
    would bury that signal under four empty commits a day per provider, so
    the previous timestamp is kept when the payload is unchanged.
    """
    existing = None
    if os.path.exists(path):
        with open(path) as handle:
            try:
                existing = json.load(handle)
            except json.JSONDecodeError:
                pass
    if existing is not None and existing.get(key) == payload[key]:
        return False
    payload["generated"] = _timestamp()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return True


def write_provider_json(provider, records):
    path = os.path.join(DATA_DIR, f"{provider}.json")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "provider": provider,
        "generated": None,
        "images": records,
    }
    changed = write_json_if_changed(path, payload)
    return path, changed


def write_combined():
    """Merge the per-provider files into one flat list.

    Each workflow rewrites this after its own provider runs, so the combined
    file is only ever as fresh as the last run of each of the three.
    """
    images = []
    for provider in PROVIDERS:
        path = os.path.join(DATA_DIR, f"{provider}.json")
        if not os.path.exists(path):
            continue
        with open(path) as handle:
            for record in json.load(handle)["images"]:
                images.append({"provider": provider, **record})
    path = os.path.join(DATA_DIR, "versions.json")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated": None,
        "images": images,
    }
    changed = write_json_if_changed(path, payload)
    return path, changed


def write_text_if_changed(path, text):
    if os.path.exists(path):
        with open(path) as handle:
            if handle.read() == text:
                return False
    with open(path, "w") as handle:
        handle.write(text)
    return True
