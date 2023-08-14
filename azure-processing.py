#! /usr/bin/env python3

import os
import re
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

# Variables
subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
location = "eastus"
publisher_name = "PaloAltoNetworks"

# Acquire a credential object
token_credential = DefaultAzureCredential()

# Acquire a compute client
compute_client = ComputeManagementClient(token_credential, subscription_id)

# Gather version numbers per offer and per sku
fixed_bnd1 = []
offer = "vmseries1" # Fixed CPU
sku = "bundle1"
images = compute_client.virtual_machine_images.list(location, publisher_name, offer, sku)
for image in images:
    fixed_bnd1.append(image.name)

fixed_bnd2 = []
offer = "vmseries1" # Fixed CPU
sku = "bundle2"
images = compute_client.virtual_machine_images.list(location, publisher_name, offer, sku)
for image in images:
    fixed_bnd2.append(image.name)

fixed_byol = []
offer = "vmseries1" # Fixed CPU
sku = "byol"
images = compute_client.virtual_machine_images.list(location, publisher_name, offer, sku)
for image in images:
    fixed_byol.append(image.name)

flex_bnd1_v9 = []
flex_bnd2_v9 = []
flex_bnd3_v9 = []
flex_byol_v9 = []

flex_bnd1 = []
offer = "vmseries-flex" # Flex
sku = "bundle1"
images = compute_client.virtual_machine_images.list(location, publisher_name, offer, sku)
for image in images:
    if image.name[0]=="9":
        flex_bnd1_v9.append(image.name)
    else:
        flex_bnd1.append(image.name)

flex_bnd2 = []
offer = "vmseries-flex" # Flex
sku = "bundle2"
images = compute_client.virtual_machine_images.list(location, publisher_name, offer, sku)
for image in images:
    if image.name[0]=="9":
        flex_bnd2_v9.append(image.name)
    else:
        flex_bnd2.append(image.name)
    
flex_bnd3 = []
offer = "vmseries-flex" # Flex
sku = "bundle3"
images = compute_client.virtual_machine_images.list(location, publisher_name, offer, sku)
for image in images:
    if image.name[0]=="9":
        flex_bnd3_v9.append(image.name)
    else:
        flex_bnd3.append(image.name)

flex_byol = []
offer = "vmseries-flex" # Flex
sku = "byol"
images = compute_client.virtual_machine_images.list(location, publisher_name, offer, sku)
for image in images:
    if image.name[0]=="9":
        flex_byol_v9.append(image.name)
    else:
        flex_byol.append(image.name)

# Output in markdown format
result = "\n# Azure\n"
result += "\n## Flexible CPU (Offer: `vmseries-flex`)\n"
result += "\n### BYOL (SKU: `byol`)\n"
for sku in flex_byol_v9:
    result += "`" + sku + "` "
for sku in flex_byol:
    result += "`" + sku + "` "
result += "\n### PAYG Bundle 1 (SKU: `bundle1`)\n"
for sku in flex_bnd1_v9:
    result += "`" + sku + "` "
for sku in flex_bnd1:
    result += "`" + sku + "` "
result += "\n### PAYG Bundle 2 (SKU: `bundle2`)\n"
for sku in flex_bnd2_v9:
    result += "`" + sku + "` "
for sku in flex_bnd2:
    result += "`" + sku + "` "
result += "\n### PAYG Bundle 3 (SKU: `bundle3`)\n"
for sku in flex_bnd3_v9:
    result += "`" + sku + "` "
for sku in flex_bnd3:
    result += "`" + sku + "` "
result += "\n## Fixed CPU (Offer: `vmseries1`)\n"
result += "\n### BYOL (SKU: `byol`)\n"
for sku in fixed_byol:
    result += "`" + sku + "` "
result += "\n### PAYG Bundle 1 (SKU: `bundle1`)\n"
for sku in fixed_bnd1:
    result += "`" + sku + "` "
result += "\n### PAYG Bundle 2 (SKU: `bundle2`)\n"
for sku in fixed_bnd2:
    result += "`" + sku + "` "
result += "\n"
print(result)