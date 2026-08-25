"""main.py, the main entry point for this CLI tool."""

import logging
import sys
from pathlib import Path


def usage() -> None:
    print(
        "Usage: ResourceExtractor.command "
        "<Install macOS.app> <output folder>"
    )


def startup() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger(__name__)

    if len(sys.argv) < 3 or sys.argv[1] in {"--help", "-h"}:
        usage()
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    app_path = Path(sys.argv[1]).expanduser()
    output_path = Path(sys.argv[2]).expanduser()

    if not app_path.exists():
        logger.error("Installer app does not exist: %s", app_path)
        sys.exit(1)

    # The user-selected output directory is created if necessary. All final
    # archive contents are extracted directly beneath this directory.
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("Could not create output folder %s: %s", output_path, exc)
        sys.exit(1)

    logger.info("Starting extraction process...")

    from installer_resource_extractor.tools.parse_app import parse_app
    from installer_resource_extractor.tools.extract_assets import ExtractAssets

    parse_app(app_path, output_path)
    ExtractAssets(
        output_path,
        output_path / "Assets" / "AssetData" / "payloadv2",
    ).run()


if __name__ == "__main__":
    startup()
