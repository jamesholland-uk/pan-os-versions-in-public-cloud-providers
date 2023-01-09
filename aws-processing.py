import sys
# import yaml
import boto3
import re

"""
Product Codes from Palo's Doc site:
https://docs.paloaltonetworks.com/vm-series/11-0/vm-series-deployment/set-up-the-vm-series-firewall-on-aws/deploy-the-vm-series-firewall-on-aws/obtain-the-ami/get-amazon-machine-image-ids
"""
byol = '6njl1pau431dv1qxipg63mvah'
bundle1 = 'e9yfvyj3uag5uo5j2hjikv74n'
bundle2 = 'hd44w1chf26uv4p52cdynb2o'
marketplace_owner_id = '679593333241'

# Create a boto3 session
session = boto3.Session()

# Get a list of all regions
client = boto3.client('ec2')
regions = [region['RegionName'] for region in client.describe_regions()['Regions']]

try:
    list_of_byol = []
    list_of_bundle1 = []
    list_of_bundle2 = []
    amis_by_version_byol = {}
    amis_by_version_bundle1 = {}
    amis_by_version_bundle2 = {}

    for region in regions:
        # Create an EC2 client for the region
        ec2 = session.client('ec2', region_name=region)

        ami_images = ec2.describe_images(Filters=[{'Name': 'name', 'Values': ['PA-VM-AWS*']}])

        for ami in ami_images['Images']:
            if ami['ProductCodes'][0]['ProductCodeId'] == byol and ami['OwnerId'] == marketplace_owner_id:
                # Checks if the version of panos is a Hotfix or not.
                match = re.search(r'.*PA-VM-AWS-(\d+.\d+.\d+-h\d{1,2})-', ami['Name'])
                if match:
                    ver = match.group(1)
                    list_of_byol.append(ver)
                    if ver not in amis_by_version_byol:
                        amis_by_version_byol[ver] = {}
                    amis_by_version_byol[ver][region] = ami['ImageId']
                else:
                    ver = ami['Name'].split("-")[3]
                    list_of_byol.append(ver)
                    if ver not in amis_by_version_byol:
                        amis_by_version_byol[ver] = {}
                    amis_by_version_byol[ver][region] = ami['ImageId']

        for ami in ami_images['Images']:
            if ami['ProductCodes'][0]['ProductCodeId'] == bundle1 and ami['OwnerId'] == marketplace_owner_id:
                # Checks if the version of panos is a Hotfix or not.
                match = re.search(r'.*PA-VM-AWS-(\d+.\d+.\d+-h\d{1,2}|)-', ami['Name'])
                if match:
                    ver = match.group(1)
                    list_of_bundle1.append(ver)
                    if ver not in amis_by_version_bundle1:
                        amis_by_version_bundle1[ver] = {}
                    amis_by_version_bundle1[ver][region] = ami['ImageId']
                else:
                    ver = ami['Name'].split("-")[3]
                    list_of_bundle1.append(ver)
                    if ver not in amis_by_version_bundle1:
                        amis_by_version_bundle1[ver] = {}
                    amis_by_version_bundle1[ver][region] = ami['ImageId']

        for ami in ami_images['Images']:
            if ami['ProductCodes'][0]['ProductCodeId'] == bundle2 and ami['OwnerId'] == marketplace_owner_id:
                # Checks if the version of panos is a Hotfix or not.
                match = re.search(r'.*PA-VM-AWS-(\d+.\d+.\d+-h\d{1,2})-', ami['Name'])
                if match:
                    ver = match.group(1)
                    list_of_bundle2.append(ver)
                    if ver not in amis_by_version_bundle2:
                        amis_by_version_bundle2[ver] = {}
                    amis_by_version_bundle2[ver][region] = ami['ImageId']
                else:
                    ver = ami['Name'].split("-")[3]
                    list_of_bundle2.append(ver)
                    if ver not in amis_by_version_bundle2:
                        amis_by_version_bundle2[ver] = {}
                    amis_by_version_bundle2[ver][region] = ami['ImageId']

    list_of_byol = list(dict.fromkeys(list_of_byol))
    list_of_byol.sort()
    list_of_bundle1 = list(dict.fromkeys(list_of_bundle1))
    list_of_bundle1.sort()
    list_of_bundle2 = list(dict.fromkeys(list_of_bundle2))
    list_of_bundle2.sort()
    result = ""
    result += "\n# AWS\n"
    result += "\n### BYOL\n"
    for version in list_of_byol:
        result += "- [" + version + "](aws/byol/" + version + ".md) \n"
    result += "\n### PAYG Bundle 1\n"
    for version in list_of_bundle1:
        result += "- [" + version + "](aws/bundle1/" + version + ".md) \n"
    result += "\n### PAYG Bundle 2\n"
    for version in list_of_bundle2:
        result += "- [" + version + "](aws/bundle2/" + version + ".md) \n"
    result += "\n"
    with open('aws.md','w') as file:
        file.write(result)
    file.close()
    
    # Add the AMI IDs for each version to the markdown string
    for ver, amis in amis_by_version_byol.items():
        ver_str = ''
        ver_str += '\n # '+ ver + '\n'
        for region, ami in amis.items():
            ver_str += '- ' + region + ': ' + ami + '\n'
        ver_str += '\n[Go back to aws.md](../../aws.md) \n'
        with open('aws/byol/' + ver + '.md', 'w') as f:
            f.write(ver_str)

    # Add the AMI IDs for each version to the markdown string
    for ver, amis in amis_by_version_bundle1.items():
        ver_str = ''
        ver_str += '\n # '+ ver + '\n'
        for region, ami in amis.items():
            ver_str += '- ' + region + ': ' + ami + '\n'
        ver_str += '\n[Go back to aws.md](../../aws.md) \n'
        with open('aws/bundle1/' + ver + '.md', 'w') as f:
            f.write(ver_str)

    # Add the AMI IDs for each version to the markdown string
    for ver, amis in amis_by_version_bundle2.items():
        ver_str = ''
        ver_str += '\n # '+ ver + '\n'
        for region, ami in amis.items():
            ver_str += '- ' + region + ': ' + ami + '\n'
        ver_str += '\n[Go back to aws.md](../../aws.md) \n'
        with open('aws/bundle2/' + ver + '.md', 'w') as f:
            f.write(ver_str)

except Exception as e:
    print(f"Exception {e!r}", file=sys.stderr)
