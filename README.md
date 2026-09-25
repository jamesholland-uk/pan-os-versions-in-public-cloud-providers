# Base PAN-OS Images on Cloud Service Providers

PAN-OS VM-Series, Panorama and Prisma AIRS image IDs across AWS, Azure and GCP, as Markdown and JSON.

This project exists to track the versions of base PAN-OS images which are present within major Cloud Service Providers such as [AWS](aws.md), [Azure](azure.md) and [GCP](gcp.md). The list of versions is retrieved and parsed directly from the Cloud Service Providers via their APIs. Other cloud-specific details are also made available where applicable, for example, AMI IDs per region for AWS images, Offers and SKUs for Azure, and image names for GCP.

The initial intended use of the information provided within this project is for infrastructure-as-code (IaC) deployments, where the cloud-specific details such as AMIs, SKUs and image names can be used as values to deploy the required version of PAN-OS for VM-Series or Panorama. There is also benefit in the historical record (via the commits to this respository) of PAN-OS versions being added and/or removed from the Cloud Service Providers.

## The Lists

Browse and search: **[jamesholland.me.uk/pan-os-image-catalog](https://jamesholland.me.uk/pan-os-image-catalog/)**. It reads `data/versions.json` directly, so it is never more than 6 hours stale.

For reading:

- [AWS](aws.md) - including listings of AMI IDs
- [Azure](azure.md) - with Offers and SKUs
- [GCP](gcp.md) - with image names

For automation, the same data as JSON:

| File | Contents |
| --- | --- |
| [`data/versions.json`](data/versions.json) | Every image across all three providers, each record tagged with `provider` |
| [`data/aws.json`](data/aws.json) | AWS only - `product_code` and an `amis` map of region to AMI ID |
| [`data/azure.json`](data/azure.json) | Azure only - `offer`, `sku` and the `image_version` to deploy |
| [`data/gcp.json`](data/gcp.json) | GCP only - the `image_name` to deploy |

Each record carries both forms of the version: `version` is the canonical PAN-OS string a human reads (`11.2.7-h13`), and the provider fields carry the raw identifier the cloud actually expects (Azure `11.2.713`, GCP `vmseries-flex-byol-11271h13`, AWS an AMI ID per region). Use the canonical form to decide, the raw form to deploy.

Two real records from `data/versions.json`, one AWS and one Azure (the AWS `amis` map is cut to two regions; the real one lists every region the image is in):

```json
[
  {
    "provider": "aws",
    "version": "11.2.7-h18",
    "major": 11, "minor": 2, "patch": 7, "hotfix": 18,
    "train": "11.2",
    "product": "vm-series",
    "licence": "byol",
    "eol": false,
    "eol_date": "2027-05-02",
    "eol_extended_date": "2027-08-31",
    "product_code": "6njl1pau431dv1qxipg63mvah",
    "amis": { "eu-west-1": "ami-01d2bf894ea94ad4a", "us-east-1": "ami-08c1e7c452f866f48" }
  },
  {
    "provider": "azure",
    "version": "11.2.7-h13",
    "major": 11, "minor": 2, "patch": 7, "hotfix": 13,
    "train": "11.2",
    "product": "vm-series",
    "licence": "byol",
    "eol": false,
    "eol_date": "2027-05-02",
    "eol_extended_date": "2027-08-31",
    "cpu": "flex",
    "offer": "vmseries-flex",
    "sku": "byol",
    "image_version": "11.2.713"
  }
]
```

`eol` is `true` past the end of standard support for that release train, `false` before it, and `null` when no date is recorded in [`eol.json`](eol.json). `eol_date` is that standard-support date, and `eol_extended_date` is the end of extended support where Palo Alto Networks offers it, otherwise `null`. An unknown date is never reported as supported, so filter on `eol != true` rather than `eol == false`.

## Using the JSON from Terraform

Pick the newest non-EOL BYOL VM-Series image available in a given region:

```hcl
data "http" "panos_aws" {
  url = "https://raw.githubusercontent.com/jamesholland-uk/pan-os-image-catalog/main/data/aws.json"
}

locals {
  region = "eu-west-1"

  candidates = [
    for image in jsondecode(data.http.panos_aws.response_body).images : image
    if image.product == "vm-series"
    && image.licence == "byol"
    && image.eol != true
    && contains(keys(image.amis), local.region)
  ]

  # Zero-pad each component so a plain string sort orders the versions
  # correctly, then take the last one.
  by_version = {
    for image in local.candidates :
    format("%03d%03d%03d%03d", image.major, image.minor, image.patch, coalesce(image.hotfix, 0)) => image
  }
  latest = local.by_version[element(sort(keys(local.by_version)), length(local.by_version) - 1)]
}

resource "aws_instance" "vmseries" {
  ami           = local.latest.amis[local.region]
  instance_type = "m5.xlarge"
  # ...
}
```

The same shape works for Azure (`image_version` into `source_image_reference`) and GCP (`image_name` into `boot_disk`).

## Coverage and caveats

- **AWS regions.** AMI IDs are collected from every region the AWS account behind this project has enabled. The AWS workflow opts the account in to new regions as AWS launches them, which takes a few hours to complete; any region not covered yet is listed at the bottom of [aws.md](aws.md) so the gap is visible rather than silent. An AMI missing for a region here does not mean Palo Alto Networks has not published there.
- **End-of-life dates.** Held in [`eol.json`](eol.json), maintained by hand from Palo Alto Networks' [end-of-life summary](https://www.paloaltonetworks.com/services/support/end-of-life-announcements/end-of-life-summary). Trains with no date recorded are left unmarked.
- **Prisma AIRS (AI Runtime Security)** is listed as its own product (`"product": "airs"`) on all three clouds. Since the March 2026 release it's the same PAN-OS image as VM-Series, with the licence deciding which mode it runs in, but each cloud still publishes it as a separate listing (an AWS product code, the Azure `airs-flex` offer, GCP `ai-runtime-security-byol-*` images), so it has its own identifiers to deploy with.
- **Azure can't show a hotfix on a `.0` release.** Azure packs the hotfix into the third number of the image version and strips leading zeros, so a hypothetical `10.1.0-h3` would be published as `10.1.3`, the same as the real 10.1.3 release, and would be listed as that. No such image exists on any of the three clouds today.
- **New listings are flagged, not guessed.** An AWS marketplace listing from Palo Alto Networks that isn't in `aws-processing.py`'s product-code table is logged as a warning on every run, so a new one gets noticed instead of quietly going unpublished.
- **Public clouds only.** Images for private clouds and hypervisors (ESXi, KVM, Hyper-V and so on) are only available from the authenticated customer download area on the Palo Alto Networks support site, so they are out of scope.
- **This is not an official Palo Alto Networks source.** It reads the public cloud APIs and publishes what they return.

Other cloud providers may be added in future; suggestions, and contributions to the code, are welcome.

## Running it yourself

```bash
pip install -r requirements.txt

python aws-processing.py                                    # needs AWS credentials
AZURE_SUBSCRIPTION_ID=... python azure-processing.py        # az login, or a service principal
gcloud compute images list --project paloaltonetworksgcp-public --no-standard-images \
  --format="value(NAME)" --filter="name~'vmseries'" > gcp-list.txt
gcloud compute images list --project paloaltonetworksgcp-public --no-standard-images \
  --format="value(NAME)" --filter="name~'panorama'" > gcp-rama-list.txt
gcloud compute images list --project paloaltonetworksgcp-public --no-standard-images \
  --format="value(NAME)" --filter="name~'ai-runtime-security'" > gcp-airs-list.txt
python gcp-processing.py gcp-list.txt gcp-rama-list.txt gcp-airs-list.txt

python -m unittest discover -p "test_*.py"                  # parsing and EOL tests
```

Each script writes its own Markdown page and JSON file, and refuses to publish an empty listing if the API returns nothing. The three clouds each encode PAN-OS versions differently; `panos_version.py` holds the parsers and is the only place that logic lives.

## Acknowledgements

- Inspiration for this project came from the great idea by [@jtschichold](https://www.github.com/jtschichold) with his [IOC tracker](https://github.com/jtschichold/panwdbl-actions)
- Many thanks to [@lachlanjholmes](https://www.github.com/lachlanjholmes) for contributing the initial AWS code for image versions, an enhancement to list the AMI IDs per region, and adding Panorama versions and AMI IDs per region for AWS

## Status
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-image-catalog/actions/workflows/aws-actions.yml/badge.svg)
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-image-catalog/actions/workflows/azure-actions.yml/badge.svg)
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-image-catalog/actions/workflows/gcp-actions.yml/badge.svg)
## Support
Community supported, as per the [support statement](SUPPORT.md).
