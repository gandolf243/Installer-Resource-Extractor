"""PBZX -> Apple Archive payload extraction."""

from __future__ import annotations

import lzma
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


class ExtractAssets:
    """
    Extract every plain PBZX payload in a payloadv2 directory.

    The source payloads are never modified. Each payload is reconstructed into
    a temporary working file and then extracted with Apple's ``aa`` utility.

    ECC payloads (payload.*.ecc) are intentionally ignored. The normal
    payload.* files are the source archives used by the extractor.
    """

    PBZX_MAGIC = b"pbzx"
    XZ_MAGIC = b"\xfd7zXZ\x00"
    YAA1_MAGIC = b"YAA1"

    HEADER_SIZE = 16
    FIRST_HEADER_OFFSET = 12

    # Only match payload.000, payload.001, ..., payload.026, etc.
    PAYLOAD_RE = re.compile(r"^payload\.\d+$")

    def __init__(self, output_path: Path, payload_dir: Path):
        self.output_path = Path(output_path)
        self.payload_dir = Path(payload_dir)
        self.logger = logging.getLogger(__name__)

        # Apple Archive paths are rooted directly here.
        self.extracted_dir = self.output_path

    @staticmethod
    def read_u64_be(data: bytes, offset: int) -> int:
        return int.from_bytes(data[offset:offset + 8], "big")

    def reconstruct_pbzx(self, payload: Path, reconstructed: Path) -> None:
        """
        Reconstruct one PBZX payload into its YAA1 Apple Archive.

        PBZX records contain:

            uint64 logical/uncompressed size
            uint64 stored size
            record data

        Normally compressed records have a smaller stored size than their
        logical size. However, payload.026 demonstrates that an XZ record can
        have stored_size == logical_size, so compression type is determined
        from the record's magic rather than from the two sizes.
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

                # IMPORTANT:
                #
                # Do NOT use:
                #
                #     stored_size == logical_size
                #
                # to decide whether a block is raw.
                #
                # payload.026 contains an XZ stream whose stored size happens
                # to equal the logical PBZX block size.
                if block.startswith(self.XZ_MAGIC):
                    kind = "XZ"

                    try:
                        decoder = lzma.LZMADecompressor(
                            format=lzma.FORMAT_XZ
                        )
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

                    # Some PBZX/XZ records may contain trailing padding.
                    # We do not reject it merely because the XZ decoder did
                    # not consume every byte.
                    #
                    # The PBZX record boundary already tells us exactly how
                    # many bytes belong to this record.
                    if decoder.unused_data:
                        self.logger.debug(
                            "%s: record %d contains %d trailing bytes "
                            "after XZ stream",
                            payload.name,
                            record,
                            len(decoder.unused_data),
                        )

                else:
                    kind = "RAW"
                    decoded = block

                if len(decoded) != logical_size:
                    raise ValueError(
                        f"{payload.name}: record {record} decoded to "
                        f"{len(decoded):,} bytes, expected "
                        f"{logical_size:,}"
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
            raise ValueError(
                f"{payload.name}: reconstructed archive is empty"
            )

        with reconstructed.open("rb") as f:
            magic = f.read(4)

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

    def extract_apple_archive(
        self,
        archive: Path,
        destination: Path,
    ) -> None:
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

        self.logger.info(
            "Extracting Apple Archive: %s",
            archive.name,
        )
        subprocess.run([
            aa,
            "extract",
            "-i",
            str(archive),
            "-d",
            str(archive.parent),
        ])

        archive.unlink()

        #  just to check
        if archive.exists():
            subprocess.run([
                    "/bin/rm",
                    archive,
            ])

        subprocess.run([
            "/bin/cp",
            "-R",
            f"{archive.parent}/.",
            str(destination),
        ], check=True)
    def process_payload(self, payload: Path) -> None:
        """
        Run the complete PBZX -> YAA1 -> filesystem pipeline.
        """
        name = payload.name

        # Apple Archive paths such as:
        #
        #   System/Library/...
        #
        # are rooted directly in the selected output directory.
        destination = self.extracted_dir

        self.logger.debug("=" * 72)
        self.logger.debug("Processing %s", name)
        self.logger.debug("=" * 72)

        # Keep the large reconstructed YAA1 archive out of the user-visible
        # output tree. It is temporary and removed automatically.
        with tempfile.TemporaryDirectory(
            prefix=f"{name}.",
            dir=self.output_path,
        ) as temp_dir:
            reconstructed = Path(temp_dir) / f"{name}.reconstructed"

            self.reconstruct_pbzx(
                payload,
                reconstructed,
            )

            self.extract_apple_archive(
                reconstructed,
                destination,
            )

    def run(self) -> None:
        """
        Process all unmodified plain payload files in payloadv2.

        payload.*.ecc files are intentionally excluded.
        """
        if not self.payload_dir.is_dir():
            raise FileNotFoundError(
                f"Payload directory not found: {self.payload_dir}"
            )

        payloads = sorted(
            p
            for p in self.payload_dir.iterdir()
            if p.is_file()
            and self.PAYLOAD_RE.fullmatch(p.name)
        )

        if not payloads:
            raise FileNotFoundError(
                f"No plain payload.* files found in {self.payload_dir}"
            )

        self.logger.debug(
            "Found %d payload files.",
            len(payloads),
        )

        self.output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        failures: list[str] = []

        for payload in payloads:
            try:
                self.process_payload(payload)

            except Exception:
                self.logger.exception(
                    "Failed to process %s",
                    payload.name,
                )
                failures.append(payload.name)

        if failures:
            raise RuntimeError(
                "The following payloads failed: "
                + ", ".join(failures)
            )

        # Assets are intermediate installer data and are not part of the
        # extracted result.
        assets_dir = self.output_path / "Assets"

        if assets_dir.exists():
            shutil.rmtree(
                assets_dir,
                ignore_errors=True,
            )

        self.logger.info(
            "All %d payloads processed successfully.",
            len(payloads),
        )


# Backwards-compatible name used by an older commit of this project.
extractAssets = ExtractAssets