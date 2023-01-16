# Base PAN-OS Images on Cloud Service Providers

This project exists to track the versions of base PAN-OS images which are present within major Cloud Service Providers such as [AWS](aws.md), [Azure](azure.md) and [GCP](gcp.md). The list of versions is retrieved and parsed directly from the Cloud Service Providers via their APIs. Other cloud-specific details are also made available where applicable, for example, AMI IDs per region for AWS images.

## The Lists

- [AWS](aws.md) - including listings of AMI IDs
- [Azure](azure.md)
- [GCP](gcp.md)

Other cloud providers may be added in future; suggestions, and contributions to the code, are welcome.

## Acknowledgements

- Inspiration for this project came from the great idea by [@jtschichold](https://www.github.com/jtschichold) with his [IOC tracker](https://github.com/jtschichold/panwdbl-actions)
- Many thanks to [@lachlanjholmes](https://www.github.com/lachlanjholmes) for contributing the initial AWS code for image versions, and an enhancement to list the AMI IDs per region as well

## Status
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-csp-versions/actions/workflows/aws-actions.yml/badge.svg)
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-csp-versions/actions/workflows/azure-actions.yml/badge.svg)
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-csp-versions/actions/workflows/gcp-actions.yml/badge.svg)
## Support
Community supported, as per the [support statement](SUPPORT.md).
