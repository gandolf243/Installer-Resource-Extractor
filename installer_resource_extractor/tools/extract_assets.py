import lzma
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


class extractAssets:
    def __init__(self, output_path: Path, payload_dir: Path):
        self.output_path = output_path
        self.payload_dir = payload_dir

        # PBZX constants
        self.PBZX_Magic = b"pbzx"
        self.block_size = 0x800000       # 8 MiB

    def read_u64_be(data, offset):
        return struct.unpack_from(">Q", data, offset)[0]


    def find_xz(data, start):
        """
        Find the next XZ stream beginning at or after start.
        """
        pos = data.find(b"\xfd7zXZ\x00", start)

        if pos == -1:
            return None

        return pos


def decompress_xz_stream(data, start):
    """
    Decompress one XZ stream beginning at 'start'.

    Returns:
        decompressed data
        number of bytes consumed from the XZ stream
    """

    decompressor = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)

    try:
        output = decompressor.decompress(data[start:])

    except lzma.LZMAError as e:
        raise RuntimeError(
            f"XZ decompression failed at offset {start}: {e}"
        )

    if not decompressor.eof:
        raise RuntimeError(
            f"XZ stream at offset {start} did not reach EOF"
        )

    consumed = len(data[start:]) - len(decompressor.unused_data)

    return output, consumed


    def reconstruct_pbzx(payload, output_file):
        """
        Reconstruct the YAA1 Apple Archive contained inside a PBZX payload.

        The original payload is only read; it is never modified.
        """

        data = payload.read_bytes()

        if data[:4] != self.PBZX_magic:
            raise RuntimeError(
                f"{payload.name}: not a PBZX file "
                f"(magic={data[:4]!r})"
            )

        if len(data) < 28:
            raise RuntimeError(f"{payload.name}: file is too small")

        # PBZX header:
        #
        # 00: "pbzx"
        # 04: flags / version
        # 0c: first logical block size
        # 14: first compressed-size field
        #
        # The first XZ stream starts at offset 28.

        pos = 28
        record = 0
        logical_total = 0

        with output_file.open("wb") as out:

            while pos < len(data):

                # We expect an XZ stream at the current record position.
                if data[pos:pos + 6] == b"\xfd7zXZ\x00":

                    decoded, consumed = decompress_xz_stream(data, pos)

                    out.write(decoded)

                    logical_total += len(decoded)

                    xz_end = pos + consumed

                    # PBZX records have a 16-byte metadata area between
                    # the end of the XZ stream and the next XZ stream.
                    next_xz = find_xz(data, xz_end)

                    if next_xz is None:
                        # No further XZ stream. The remaining bytes may
                        # contain a raw PBZX record.
                        pos = xz_end

                        print(
                            f"  {record}: XZ "
                            f"uncomp={len(decoded):,} "
                            f"stored={consumed:,} "
                            f"offset={pos - consumed:,}"
                        )

                        record += 1
                        break

                    metadata_gap = next_xz - xz_end

                    if metadata_gap >= 16:
                        pos = next_xz

                    else:
                        raise RuntimeError(
                            f"Unexpected PBZX metadata gap: "
                            f"{metadata_gap} bytes"
                        )

                    print(
                        f"  {record}: XZ "
                        f"uncomp={len(decoded):,} "
                        f"stored={consumed:,} "
                        f"offset={pos - metadata_gap - consumed:,}"
                    )

                    record += 1
                    continue

                # ----------------------------------------------------
                # RAW block
                #
                # Once the XZ records end, PBZX can contain raw blocks.
                # The remaining record sizes are described by the
                # 16-byte record metadata immediately before them.
                # ----------------------------------------------------

                remaining = len(data) - pos

                if remaining <= 0:
                    break

                # At this point we need to locate the next PBZX raw
                # record boundary. The raw data consists of 8 MiB
                # logical blocks, with a final shorter block.
                #
                # The reconstructed data from our installer demonstrated
                # that these blocks occur consecutively.
                block_size = min(self.block_size, remaining)

                chunk = data[pos:pos + block_size]

                if not chunk:
                    break

                out.write(chunk)
                logical_total += len(chunk)

                print(
                    f"  {record}: RAW "
                    f"uncomp={len(chunk):,} "
                    f"stored={len(chunk):,} "
                    f"offset={pos:,}"
                )

                pos += len(chunk)
                record += 1

        print()
        print("PBZX reconstruction complete")
        print(f"records: {record}")
        print(f"logical bytes: {logical_total:,}")
        print(f"output: {output_file}")
        print()

        return output_file


    # ------------------------------------------------------------
    # Apple Archive extraction
    # ------------------------------------------------------------

    def extract_apple_archive(archive, destination):
        destination.mkdir(parents=True, exist_ok=True)

        command = [
            "aa",
            "extract",
            "-i", str(archive),
            "-d", str(destination),
        ]

        print("Running:")
        print(" ".join(command))
        print()

        try:
            subprocess.run(command, check=True)

        except FileNotFoundError:
            raise RuntimeError(
                "'aa' was not found in PATH. "
                "Run 'which aa' to verify that Apple's aa tool is available."
            )

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"aa extraction failed with exit code {e.returncode}"
            )


    # ------------------------------------------------------------
    # Process one payload
    # ------------------------------------------------------------

    def process_payload(payload):
        name = payload.name

        print()
        print("=" * 72)
        print(f"PROCESSING: {name}")
        print("=" * 72)

        work = WORK_DIR / name
        output = OUTPUT_DIR / name

        work.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)

        reconstructed = work / f"{name}.reconstructed"

        print()
        print("Step 1/2: reconstructing PBZX")
        print(f"Input : {payload}")
        print(f"Output: {reconstructed}")
        print()

        reconstruct_pbzx(payload, reconstructed)

        print()
        print("Step 2/2: extracting Apple Archive")
        print(f"Input : {reconstructed}")
        print(f"Output: {output}")
        print()

        self.extract_apple_archive(reconstructed, output)

        print()
        print(f"Finished: {name}")
        print(f"Extracted to: {output}")

        return True


    # ------------------------------------------------------------
    # Main
    # ------------------------------------------------------------

    def main():

        OUTPUT_DIR.mkdir(exist_ok=True)
        WORK_DIR.mkdir(exist_ok=True)

        payloads = sorted(
            p for p in BASE_DIR.glob("payload.*")
            if p.is_file()
            and ".reconstructed" not in p.name
        )

        if not payloads:
            print("No payload.* files found.")
            return 1

        print(f"Found {len(payloads)} payload file(s):")

        for payload in payloads:
            print(f"  {payload.name}")

        print()
        print(f"Working files : {WORK_DIR}")
        print(f"Final output  : {OUTPUT_DIR}")
        print()

        failures = []

        for payload in payloads:
            try:
                process_payload(payload)

            except Exception as e:
                print()
                print(f"ERROR processing {payload.name}:")
                print(f"  {e}")
                print()

                failures.append(payload.name)

        print()
        print("=" * 72)
        print("ALL PAYLOADS PROCESSED")
        print("=" * 72)

        if failures:
            print()
            print("Failed payloads:")

            for name in failures:
                print(f"  {name}")

            return 1

        print()
        print("No failures.")

        return 0