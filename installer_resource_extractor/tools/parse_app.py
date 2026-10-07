"""
parse_app.py: parses the installer app and extracts the base resources.
"""
import logging
import plistlib
import sys
import subprocess
from pathlib import Path
class parse_app:
    def __init__(self, app_path: Path, output_path: Path):
        self.logger = logging.getLogger(__name__)
        self.app_path = app_path
        self.output_path = output_path
        self.logger.info(f"Parsing installer app at {app_path} and extracting resources to {output_path}")
        try:
            if not ((app_path / Path("Contents/Resources/createinstallmedia")).exists() and (app_path / Path("Contents/SharedSupport/SharedSupport.dmg")).exists()):
                self.logger.error(f"{app_path} doesn't appear to be a valid macOS installer!")
                sys.exit(1)
            if not (app_path / Path("Contents/Info.plist")).exists():
                self.logger.error(f"{app_path} is missing `Info.plist`")
                sys.exit(1)

        except PermissionError:
            self.logger.error(f"Permission denied when accessing {app_path}")
            sys.exit(1)
        try:
            application_info_plist = plistlib.load((app_path / Path("Contents/Info.plist")).open("rb"))
        except (PermissionError, TypeError, plistlib.InvalidFileException):
            self.logger.error(f"Could not open {app_path / Path('Contents/Info.plist')}")
            sys.exit(1)
        else:
            if "DTPlatformVersion" not in application_info_plist:
                self.logger.error(f"{app_path} is missing `DTPlatformVersion`")
                sys.exit(1)
            if "CFBundleDisplayName" not in application_info_plist:
                self.logger.error(f"{app_path} is missing `CFBundleDisplayName`")
                sys.exit(1)
        self.extract_zip()
        
    def extract_zip(self):
        self.logger.info("Mounting SharedSupport.dmg...")
        subprocess.run(["/usr/bin/hdiutil", "attach", "-noverify", str(self.app_path / Path("Contents/SharedSupport/SharedSupport.dmg"))], check=True)
        assets_zip = Path(subprocess.run(["/usr/bin/find", "/Volumes/Shared Support/com_apple_MobileAsset_MacSoftwareUpdate", "-type", "f", "-name", "*.zip"], capture_output=True, text=True).stdout.strip())
        self.logger.info(f"Unziping macOS installer assets from {assets_zip} ...")
        subprocess.run(["/usr/bin/unzip", str(assets_zip), "-d", str(self.output_path / "Assets")], check=True)
        self.logger.info("Unmounting SharedSupport.dmg...")
        subprocess.run(["/usr/bin/hdiutil", "detach", "/Volumes/Shared Support"], check=True)

    def remove_extra(self):
        self.logger.debug("Removing extra payloads...")
        unneededPayloads = subprocess.run(["/usr/bin/find", str(self.output_path / "Assets" / "AssetData" / "payloadv2"), "-type", "f", "-name", "*.ecc"], capture_output=True, text=True).stdout.strip().splitlines()
        unneededPayloads.extend(subprocess.run(["/usr/bin/find", str(self.output_path / "Assets" / "AssetData" / "payloadv2"), "-type", "f", "-name", "*_payload"], capture_output=True, text=True).stdout.strip().splitlines())
        unneededPayloads.extend(subprocess.run(["/usr/bin/find", str(self.output_path / "Assets" / "AssetData" / "payloadv2"), "-type", "f", "-name", "*.txt"], capture_output=True, text=True).stdout.strip().splitlines())
        unneededPayloads.extend(subprocess.run(["/usr/bin/find", str(self.output_path / "Assets" / "AssetData" / "payloadv2"), "-type", "f", "-name", "*.manifest"], capture_output=True, text=True).stdout.strip().splitlines())
        for asset in unneededPayloads:
            subprocess.run(["/bin/rm", asset], check=True)