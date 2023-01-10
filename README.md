# Base PAN-OS Images on Cloud Service Providers

This project exists to track the versions of base PAN-OS images which are present within major Cloud Service Providers. The list of versions is retrieved and parsed directly from the Cloud Service Providers via their APIs. Other cloud-specific details are also made available where applicable, including AMI IDs for AWS base images.

![Workflow Badge](https://github.com/jamesholland-uk/pan-os-csp-versions/actions/workflows/aws-actions.yml/badge.svg)
![Workflow Badge](https://github.com/jamesholland-uk/pan-os-csp-versions/actions/workflows/gcp-actions.yml/badge.svg)

## Lists

Today, this project includes lists of base PAN-OS image versions currently present on:

- [AWS](aws.md) - including listings of AMI IDs
- [GCP](gcp.md)

More to come in future...

## Acknowledgements

- The inspiration for this project came from this great idea by [@jtschichold](https://www.github.com/jtschichold) and his [IOC tracker](https://github.com/jtschichold/panwdbl-actions)
- Many thanks to [@lachlanjholmes](https://www.github.com/lachlanjholmes) for contributing the initial AWS code for base image versions, and an enhancement to list the AMI IDs as well

## Support

This project is released under an as-is, best effort, support policy. This should be seen as community supported. There is no expectation of technical support or help in using or troubleshooting the components of the project. This projects is in no way affiliated or supported by Palo Alto Networks, its support teams, or its ASC (Authorized Support Center) partners.
