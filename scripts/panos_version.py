"""Shared PAN-OS version handling for the AWS, Azure and GCP processors.

Each cloud encodes the same PAN-OS version differently:

    canonical    AWS AMI name    Azure image    GCP image
    11.2.7-h13   11.2.7-h13      11.2.713       11271h13
    10.2.10-h9   10.2.10-h9      10.2.1009      10210h9
    11.1.15      11.1.15         11.1.15        11115

Every parser returns a Version that keeps the provider's own identifier in
`raw` alongside the parsed numbers. The canonical form is what a human
reads; the raw form is what Terraform has to hand back to the cloud.
Dropping either one breaks one of the two audiences for this project.
"""

import re
from dataclasses import dataclass

# PAN-OS patch numbers have reached the mid-twenties (8.1.25) and hotfixes
# the mid-thirties (11.1.6-h35). Anything well beyond that means we have
# mis-split a packed identifier, and we would rather say so than publish a
# version that does not exist.
MAX_PLAUSIBLE_PATCH = 30
MAX_PLAUSIBLE_HOTFIX = 60


class ParseError(ValueError):
    """Raised when an image identifier does not look like a PAN-OS version."""


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    hotfix: int | None
    raw: str

    def __str__(self):
        base = f"{self.major}.{self.minor}.{self.patch}"
        return base if self.hotfix is None else f"{base}-h{self.hotfix}"

    @property
    def train(self):
        """The release train, e.g. "11.2" - the granularity EOL is tracked at."""
        return f"{self.major}.{self.minor}"


def sort_key(version):
    """Order PAN-OS versions correctly.

    This replaces semver.Version.parse, which read "-h9" as a SemVer
    prerelease tag and compared it lexically. That sorted h9 *after* h14,
    and sorted 11.1.13-h5 *before* 11.1.13. In PAN-OS a hotfix is newer
    than the release it patches, and hotfix numbers are numeric.
    """
    return (version.major, version.minor, version.patch, version.hotfix or 0)


def _check_plausible(major, minor, patch, hotfix, raw):
    if patch > MAX_PLAUSIBLE_PATCH:
        raise ParseError(
            f"implausible patch number {patch} from {raw!r} "
            f"(parsed as {major}.{minor}.{patch})"
        )
    if hotfix is not None and hotfix > MAX_PLAUSIBLE_HOTFIX:
        raise ParseError(f"implausible hotfix number {hotfix} from {raw!r}")


_DOTTED = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-h(\d+))?$")


def parse_dotted(raw):
    """Parse the AWS form, which is already canonical: 11.2.7-h18."""
    match = _DOTTED.match(raw)
    if not match:
        raise ParseError(f"not a dotted PAN-OS version: {raw!r}")
    major, minor, patch, hotfix = match.groups()
    hotfix = int(hotfix) if hotfix else None
    _check_plausible(int(major), int(minor), int(patch), hotfix, raw)
    return Version(int(major), int(minor), int(patch), hotfix, raw)


_GCP = re.compile(r"^(\d+)(?:h(\d{1,2}))?$")


def parse_gcp(raw):
    """Parse GCP's packed suffix: 10210h9 -> 10.2.10-h9.

    GCP runs major, minor and patch together with no separator, so the split
    has to be inferred. PAN-OS majors are 7 to 12 and minors are always a
    single digit, which makes it unambiguous: a leading "1" means a
    two-digit major, anything else is a one-digit major, the next digit is
    the minor, and the remainder is the patch.
    """
    match = _GCP.match(raw)
    if not match:
        raise ParseError(f"not a GCP PAN-OS image suffix: {raw!r}")
    digits, hotfix = match.groups()
    major_width = 2 if digits.startswith("1") else 1
    if len(digits) < major_width + 2:
        raise ParseError(f"too few digits for major.minor.patch: {raw!r}")
    major = int(digits[:major_width])
    minor = int(digits[major_width])
    patch = int(digits[major_width + 1:])
    hotfix = int(hotfix) if hotfix else None
    _check_plausible(major, minor, patch, hotfix, raw)
    return Version(major, minor, patch, hotfix, raw)


_AZURE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_azure(raw):
    """Parse Azure's packed form: 10.2.1009 -> 10.2.10-h9.

    Azure image versions must be exactly three numeric components, so PAN
    packs the patch and the hotfix into the third: the hotfix is zero-padded
    to two digits and appended to the patch. Azure then strips leading
    zeros, which is why 11.1.4-h5 publishes as 11.1.405 and not 11.1.0405.

    A third component of one or two digits is a plain patch with no hotfix
    (11.1.15); three or more digits means the packed form.

    One case cannot be recovered: a hotfix on a .0 release. 10.1.0-h3 packs
    to 003, which Azure strips to 3, the same string as the 10.1.3 release.
    The information is gone before it reaches us, so it is read as a plain
    patch. No x.y.0-hN image exists on any of the three clouds (checked
    2026-09-23); if one appears on AWS or GCP, expect Azure to be wrong.

    The rule is confirmed by cross-checking against AWS, which publishes the
    unambiguous dotted form of the same releases: Azure 11.1.1025 against
    AWS 11.1.10-h25, Azure 11.0.406 against AWS 11.0.4-h6, Azure 11.2.501
    against AWS 11.2.5-h1.
    """
    match = _AZURE.match(raw)
    if not match:
        raise ParseError(f"not an Azure PAN-OS image version: {raw!r}")
    major, minor, third = match.groups()
    if len(third) <= 2:
        patch, hotfix = int(third), None
    else:
        patch, hotfix = int(third[:-2]), int(third[-2:])
    _check_plausible(int(major), int(minor), patch, hotfix, raw)
    return Version(int(major), int(minor), patch, hotfix, raw)
