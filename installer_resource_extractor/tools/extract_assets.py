"""PBZX -> Apple Archive payload extraction."""

from __future__ import annotations

import lzma
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path


class ExtractAssets:
    """
    Extract every PBZX payload in a payloadv2 directory.

    The source payloads are never modified. Each payload is reconstructed into
    a temporary working file and then extracted with Apple's ``aa`` utility.
    """

    PBZX_MAGIC = b"pbzx"
    XZ_MAGIC = b"\xfd7zXZ\x00"
    YAA1_MAGIC = b"YAA1"
    HEADER_SIZE = 16
    FIRST_HEADER_OFFSET = 12

    def __init__(self, output_path: Path, payload_dir: Path):
        self.output_path = Path(output_path)
        self.payload_dir = Path(payload_dir)
        self.logger = logging.getLogger(__name__)

        self.extracted_dir = self.output_path

    @staticmethod
    def read_u64_be(data: bytes, offset: int) -> int:
        return int.from_bytes(data[offset:offset + 8], "big")

    def reconstruct_pbzx(self, payload: Path, reconstructed: Path) -> None:
        """
        Reconstruct one PBZX payload into its YAA1 Apple Archive.
        """
        self.logger.info("Reconstructing %s", payload.name)

        data = payload.read_bytes()
        if data[:4] != self.PBZX_MAGIC:
            raise ValueError(f"{payload.name}: not a PBZX file")

        if len(data) < self.FIRST_HEADER_OFFSET + self.HEADER_SIZE:
            raise ValueError(f"{payload.name}: PBZX file is too small")

        pos = self.FIRST_HEADER_OFFSET
        record = 0
        logical_total = 0

        reconstructed.parent.mkdir(parents=True, exist_ok=True)

        with reconstructed.open("wb") as out:
            while pos < len(data):
                if pos + self.HEADER_SIZE > len(data):
                    raise ValueError(
                        f"{payload.name}: truncated record header at {pos}"
                    )

                logical_size = self.read_u64_be(data, pos)
                stored_size = self.read_u64_be(data, pos + 8)
                data_start = pos + self.HEADER_SIZE
                data_end = data_start + stored_size

                if data_end > len(data):
                    raise ValueError(
                        f"{payload.name}: record {record} extends past EOF "
                        f"(offset={data_start}, stored={stored_size}, "
                        f"file={len(data)})"
                    )

                block = data[data_start:data_end]

                if stored_size == logical_size:
                    # Raw PBZX block.
                    decoded = block
                    kind = "RAW"
                else:
                    if not block.startswith(self.XZ_MAGIC):
                        raise ValueError(
                            f"{payload.name}: record {record} declares a "
                            f"compressed block but does not begin with XZ "
                            f"magic at offset {data_start}"
                        )

                    try:
                        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
                        decoded = decoder.decompress(block)
                    except lzma.LZMAError as exc:
                        raise ValueError(
                            f"{payload.name}: XZ decompression failed in "
                            f"record {record} at offset {data_start}: {exc}"
                        ) from exc

                    if not decoder.eof:
                        raise ValueError(
                            f"{payload.name}: XZ stream in record {record} "
                            "did not reach EOF"
                        )

                    if decoder.unused_data:
                        raise ValueError(
                            f"{payload.name}: XZ record {record} contains "
                            f"{len(decoder.unused_data)} unexpected trailing bytes"
                        )

                    kind = "XZ"

                if len(decoded) != logical_size:
                    raise ValueError(
                        f"{payload.name}: record {record} decoded to "
                        f"{len(decoded):,} bytes, expected {logical_size:,}"
                    )

                out.write(decoded)
                logical_total += len(decoded)

                self.logger.info(
                    "  %d: %s uncomp=%s stored=%s offset=%s",
                    record,
                    kind,
                    f"{logical_size:,}",
                    f"{stored_size:,}",
                    f"{data_start:,}",
                )

                pos = data_end
                record += 1

        if reconstructed.stat().st_size < 4:
            raise ValueError(f"{payload.name}: reconstructed archive is empty")

        magic = reconstructed.read_bytes()[:4]
        if magic != self.YAA1_MAGIC:
            raise ValueError(
                f"{payload.name}: reconstruction finished, but output does "
                f"not begin with YAA1 (got {magic!r})"
            )

        self.logger.info(
            "Reconstruction complete: %d records, %s bytes -> %s",
            record,
            f"{logical_total:,}",
            reconstructed,
        )

    def extract_apple_archive(self, archive: Path, destination: Path) -> None:
        """
        Extract a reconstructed YAA1 archive using Apple's aa.
        """
        destination.mkdir(parents=True, exist_ok=True)

        aa = shutil.which("aa")
        if aa is None:
            raise RuntimeError(
                "Apple's 'aa' utility was not found in PATH. "
                "Run 'which aa' to verify it is available."
            )

        command = [aa, "extract", "-i", str(archive), "-d", str(destination)]
        self.logger.info("Extracting Apple Archive: %s", archive.name)
        subprocess.run(command, check=True)

    def process_payload(self, payload: Path) -> None:
        """
        Run the complete PBZX -> YAA1 -> filesystem pipeline.
        """
        name = payload.name
        # Extract directly into the selected output directory. Apple Archive
        # paths such as System/Library/dyld/... are therefore rooted there,
        # rather than underneath output/payload.001/.
        destination = self.extracted_dir

        self.logger.info("=" * 72)
        self.logger.info("Processing %s", name)
        self.logger.info("=" * 72)

        # Keep the large reconstructed YAA1 archive out of the user-visible
        # output tree. It is temporary and is removed after aa finishes.
        with tempfile.TemporaryDirectory(prefix=f"{name}.", dir=self.output_path) as temp_dir:
            reconstructed = Path(temp_dir) / f"{name}.reconstructed"
            self.reconstruct_pbzx(payload, reconstructed)
            self.extract_apple_archive(reconstructed, destination)

    def run(self) -> None:
        """
        Process all unmodified payload files in payloadv2.
        """
        if not self.payload_dir.is_dir():
            raise FileNotFoundError(f"Payload directory not found: {self.payload_dir}")

        payloads = sorted(
            p for p in self.payload_dir.iterdir()
            if p.is_file()
            and p.name.startswith("payload.")
        )

        if not payloads:
            raise FileNotFoundError(
                f"No payload.* files found in {self.payload_dir}"
            )

        self.output_path.mkdir(parents=True, exist_ok=True)
        failures: list[str] = []
        for payload in payloads:
            try:
                self.process_payload(payload)
            except Exception:
                self.logger.exception("Failed to process %s", payload.name)
                failures.append(payload.name)

        if failures:
            raise RuntimeError(
                "The following payloads failed: " + ", ".join(failures)
            )
        # cleanup the Assets dir
        subprocess.run(["/bin/rm", "-rf", str(self.output_path / "Assets")])
        self.logger.info("All %d payloads processed successfully.", len(payloads))


# Backwards-compatible name used by an older commit of this project.
extractAssets = ExtractAssets
