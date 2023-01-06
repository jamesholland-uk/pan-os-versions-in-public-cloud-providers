import sys
import yaml

"""
Product Codes from Palo's Doc site:
https://docs.paloaltonetworks.com/vm-series/11-0/vm-series-deployment/set-up-the-vm-series-firewall-on-aws/deploy-the-vm-series-firewall-on-aws/obtain-the-ami/get-amazon-machine-image-ids
"""
byol = '6njl1pau431dv1qxipg63mvah'
bundle1 = 'e9yfvyj3uag5uo5j2hjikv74n'
bundle2 = 'hd44w1chf26uv4p52cdynb2o'

try:
    with open(sys.argv[1],'r') as file:
        ami_images = yaml.safe_load(file)

        list_of_byol = []
        list_of_bundle1 = []
        list_of_bundle2 = []

        for ami in ami_images['Images']:
            if ami['ProductCodes'][0]['ProductCodeId'] == byol:
                # Checks if the version of panos is a Hotfix or not.
                if range(len(ami['Name'].split("-")[4])) == range(0,2):
                    ver = ami['Name'].split("-")[3]+"-"+ami['Name'].split("-")[4]
                    list_of_byol.append(ver)
                else:
                    ver = ami['Name'].split("-")[3]
                    list_of_byol.append(ver)


        for ami in ami_images['Images']:
            if ami['ProductCodes'][0]['ProductCodeId'] == bundle1:
                # Checks if the version of panos is a Hotfix or not.
                if range(len(ami['Name'].split("-")[4])) == range(0,2):
                    ver = ami['Name'].split("-")[3]+"-"+ami['Name'].split("-")[4]
                    list_of_bundle1.append(ver)
                else:
                    ver = ami['Name'].split("-")[3]
                    list_of_bundle1.append(ver)


        for ami in ami_images['Images']:
            if ami['ProductCodes'][0]['ProductCodeId'] == bundle2:
                # Checks if the version of panos is a Hotfix or not.
                if range(len(ami['Name'].split("-")[4])) == range(0,2):
                    ver = ami['Name'].split("-")[3]+"-"+ami['Name'].split("-")[4]
                    list_of_bundle2.append(ver)
                else:
                    ver = ami['Name'].split("-")[3]
                    list_of_bundle2.append(ver)

    list_of_byol.sort()
    list_of_bundle1.sort()
    list_of_bundle2.sort()
    result = ""
    result += "\n# AWS\n"
    result += "\n### BYOL\n"
    for version in list_of_byol:
        result += "`" + version + "` "
    result += "\n### PAYG Bundle 1\n"
    for version in list_of_byol:
        result += "`" + version + "` "
    result += "\n### PAYG Bundle 2\n"
    for version in list_of_byol:
        result += "`" + version + "` "
    result += "\n"
    print(result)

except Exception as e:
    print(f"Exception translating file {e!r}", file=sys.stderr)
