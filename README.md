# Base PAN-OS Images on Cloud Service Providers

This project exists to track the versions of base PAN-OS images which are present within major Cloud Service Providers such as [AWS](aws.md), [Azure](azure.md) and [GCP](gcp.md). The list of versions is retrieved and parsed directly from the Cloud Service Providers via their APIs. Other cloud-specific details are also made available where applicable, for example, AMI IDs per region for AWS images, Offers and SKUs for Azure, and image names for GCP.

The initial intended use of the information provided within this project is for infrastructure-as-code (IaC) deployments, where the cloud-specific details such as AMIs, SKUs and image names can be used as values to deploy the required version of PAN-OS for VM-Series or Panorama. There is also benefit in the historical record (via the commits to this respository) of PAN-OS versions being added and/or removed from the Cloud Service Providers.

## The Lists

- [AWS](aws.md) - including listings of AMI IDs
- [Azure](azure.md) - with Offers and SKUs
- [GCP](gcp.md) - with image names

Other cloud providers may be added in future; suggestions, and contributions to the code, are welcome.

## Acknowledgements

- Inspiration for this project came from the great idea by [@jtschichold](https://www.github.com/jtschichold) with his [IOC tracker](https://github.com/jtschichold/panwdbl-actions)
- Many thanks to [@lachlanjholmes](https://www.github.com/lachlanjholmes) for contributing the initial AWS code for image versions, an enhancement to list the AMI IDs per region, and adding Panorama versions and AMI IDs per region for AWS

## Status
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-csp-versions/actions/workflows/aws-actions.yml/badge.svg)
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-csp-versions/actions/workflows/azure-actions.yml/badge.svg)
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-csp-versions/actions/workflows/gcp-actions.yml/badge.svg)
## Support
Community supported, as per the [support statement](SUPPORT.md).
