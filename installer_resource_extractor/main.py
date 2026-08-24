"""
main.py, the main entry point for this CLI tool
"""

import logging
import sys
from pathlib import Path


def startup():
    # We configure logging to write to sys.stdout (the Terminal window)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
    )
    logger = logging.getLogger(__name__)

    # check for args
    if len(sys.argv) < 3:
        print(r"Usage: resourcesExtractor.command Applications/Install\ macOS\ version.app /path/to/output/folder/")
        sys.exit(1)
    elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
        print(r"Usage: resourcesExtractor.command Applications/Install\ macOS\ version.app /path/to/output/folder/")
        sys.exit(0)
    elif Path(sys.argv[1]).exists() and Path(sys.argv[2]).exists():
        logger.info("Starting extraction process...")
        # Call the main function from the resources_extractor module
        from installer_resource_extractor.tools.parse_app import parse_app
        parse_app(Path(sys.argv[1]), Path(sys.argv[2]))
    elif Path(sys.argv[1]).exists() and not Path(sys.argv[2]).exists():
        logger.error(f"Output folder {sys.argv[2]} does not exist.")
        sys.exit(1)
if __name__ == "__main__":
    startup()