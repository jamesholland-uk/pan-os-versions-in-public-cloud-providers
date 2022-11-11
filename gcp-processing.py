#! /usr/bin/env python3

import sys
import re


def ver_format(ver):

    # This function formats a PAN-OS version number, that arrives as a continuous string, into dotted notation

    if re.search("\d{5}", ver):
        # example 10.1.11
        newver = ver[0] + ver[1] + "." + ver[2] + "." + ver[3] + ver[4]
    elif re.search("1\d{3}", ver):
        # example 10.1.1
        newver = ver[0] + ver[1] + "." + ver[2] + "." + ver[3]
    elif re.search("\d{4}", ver):
        # example 8.1.11
        newver = ver[0] + "." + ver[1] + "." + ver[2] + ver[3]
    elif re.search("\d{3}", ver):
        # example 8.1.1
        newver = ver[0] + "." + ver[1] + "." + ver[2]
    else:
        newver = ver

    if re.search("\d{3,5}h\d{1,2}", ver):
        # example 10.1.11h1
        # example 10.1.11h11

        newver += "-h"

        hotfix_digits = len(ver) - 1 - ver.find("h")

        while hotfix_digits > 0:
            newver += ver[ver.find("h") + 1]
            hotfix_digits -= 1

    return newver


try:
    with open(sys.argv[1], "r") as f:

        # Empty places for the results
        # v9 collected differently, for Flex only, so we can output the v9 first then the v10 (lazy hack in order to not order them after collecting them into an array)
        result = ""
        fixed_bnd1 = []
        fixed_bnd2 = []
        fixed_byol = []
        flex_bnd1_v9 = []
        flex_bnd2_v9 = []
        flex_byol_v9 = []
        flex_bnd1 = []
        flex_bnd2 = []
        flex_byol = []

        for line in f:

            # Fixed PAYG Bundle 1
            if re.search("vmseries-bundle1-\d{3,5}", line):
                ver = line.split("-")[2].rstrip()
                fixed_bnd1.append(ver_format(ver))

            # Fixed PAYG Bundle 2
            elif re.search("vmseries-bundle2-\d{3,5}", line):
                ver = line.split("-")[2].rstrip()
                fixed_bnd2.append(ver_format(ver))

            # Fixed BYOL
            elif re.search("vmseries-byol-\d{3,5}", line):
                ver = line.split("-")[2].rstrip()
                fixed_byol.append(ver_format(ver))

            # Flex PAYG Bundle 1 v9
            elif re.search("vmseries-flex-bundle1-9\d{2,5}", line):
                ver = line.split("-")[3].rstrip()
                flex_bnd1_v9.append(ver_format(ver))

            # Flex PAYG Bundle 1 v10 onwards
            elif re.search("vmseries-flex-bundle1-\d{3,5}", line):
                ver = line.split("-")[3].rstrip()
                flex_bnd1.append(ver_format(ver))

            # Flex PAYG Bundle 2 v9
            elif re.search("vmseries-flex-bundle2-9\d{2,5}", line):
                ver = line.split("-")[3].rstrip()
                flex_bnd2_v9.append(ver_format(ver))

            # Flex PAYG Bundle 2 v10 onwards
            elif re.search("vmseries-flex-bundle2-\d{3,5}", line):
                ver = line.split("-")[3].rstrip()
                flex_bnd2.append(ver_format(ver))

            # Flex BYOL v9
            elif re.search("vmseries-flex-byol-9\d{2,5}", line):
                ver = line.split("-")[3].rstrip()
                flex_byol_v9.append(ver_format(ver))

            # Flex BYOL v10 onwards
            elif re.search("vmseries-flex-byol-\d{3,5}", line):
                ver = line.split("-")[3].rstrip()
                flex_byol.append(ver_format(ver))

        # Output in markdown format
        result += "\n# GCP\n"
        result += "\n## Flexible CPU\n"
        result += "\n### BYOL\n"
        for sku in flex_byol_v9:
            result += "`" + sku + "` "
        for sku in flex_byol:
            result += "`" + sku + "` "
        result += "\n### PAYG Bundle 1\n"
        for sku in flex_bnd1_v9:
            result += "`" + sku + "` "
        for sku in flex_bnd1:
            result += "`" + sku + "` "
        result += "\n### PAYG Bundle 2\n"
        for sku in flex_bnd2_v9:
            result += "`" + sku + "` "
        for sku in flex_bnd2:
            result += "`" + sku + "` "
        result += "\n## Fixed CPU\n"
        result += "\n### BYOL\n"
        for sku in fixed_byol:
            result += "`" + sku + "` "
        result += "\n### PAYG Bundle 1\n"
        for sku in fixed_bnd1:
            result += "`" + sku + "` "
        result += "\n### PAYG Bundle 2\n"
        for sku in fixed_bnd2:
            result += "`" + sku + "` "
        result += "\n"
        print(result)

except Exception as e:
    print(f"Exception translating file {e!r}", file=sys.stderr)
