#! /usr/bin/env python3

import sys
from installer_resource_extractor import main
try:
    import logging
except(ImportError):
    print(
        "You need the logging framework to continue. ",
        "You can install it by running `pip3 install logging`",
    )
    sys.exit(1)
main()