from __future__ import annotations

import argparse
import shutil
import struct
import zlib
from pathlib import Path


PATCH_BIG = Path(r"C:\Program Files\EA Games\FIFA 14\Game\patch.big")

GAMEHUB_PATH = (
    "data/ui/external/ion_fut/screens/gamehub/gamehub.big"
)

# Offset inside extracted GameHub.big entry "0".
APT_PATCH_OFFSET = 0x285A

ORIGINAL = bytes.fromhex("A3 30 01")
PATCHED = bytes.fromhex("A3 58 01")


def read_big4_entry(data: bytes, wanted_name: str):
    if data[:4] != b"BIG4":
        raise RuntimeError("patch.big is geen BIG4 archive.")

    file_count = struct.unpack(">I", data[8:12])[0]

    pos = 16

    for index in range(file_count):
        entry_header_pos = pos

        offset, size = struct.unpack(">II", data[pos:pos + 8])
        pos += 8

        end = data.index(b"\x00", pos)
        name = data[pos:end].decode("latin1")
        pos = end + 1

        if name.lower() == wanted_name.lower():
            return {
                "index": index,
                "name": name,
                "offset": offset,
                "size": size,
                "header_pos": entry_header_pos,
                "data": data[offset:offset + size],
            }

    raise RuntimeError(f"Niet gevonden in patch.big: {wanted_name}")


def decode_chunkzip(blob: bytes) -> bytes:
    if not blob.startswith(b"chunkzip"):
        raise RuntimeError("GameHub.big is niet chunkzip-compressed.")

    version = struct.unpack(">I", blob[8:12])[0]
    unpacked_size = struct.unpack(">I", blob[12:16])[0]
    compressed_size = struct.unpack(">I", blob[40:44])[0]

    if version != 2:
        raise RuntimeError(f"Onverwachte chunkzip versie: {version}")

    compressed = blob[48:48 + compressed_size]

    decoded = zlib.decompress(compressed, -15)

    if len(decoded) != unpacked_size:
        raise RuntimeError(
            f"Decoded size klopt niet: {len(decoded)} != {unpacked_size}"
        )

    return decoded


def read_nested_big_entry(data: bytes, wanted_name: str):
    if data[:4] != b"BIGF":
        raise RuntimeError("Decoded GameHub.big is geen BIGF archive.")

    file_count = struct.unpack(">I", data[8:12])[0]

    pos = 16

    for index in range(file_count):
        offset, size = struct.unpack(">II", data[pos:pos + 8])
        pos += 8

        end = data.index(b"\x00", pos)
        name = data[pos:end].decode("latin1")
        pos = end + 1

        if name == wanted_name:
            return {
                "index": index,
                "name": name,
                "offset": offset,
                "size": size,
                "data": data[offset:offset + size],
            }

    raise RuntimeError(f"Nested entry {wanted_name!r} niet gevonden.")


def check():
    print("[WC TEST] Reading patch.big...")
    data = PATCH_BIG.read_bytes()

    gamehub = read_big4_entry(data, GAMEHUB_PATH)

    print()
    print("[OK] GameHub.big gevonden")
    print(f"     record index : {gamehub['index']}")
    print(f"     offset       : 0x{gamehub['offset']:X}")
    print(f"     size         : {gamehub['size']} bytes")

    decoded = decode_chunkzip(gamehub["data"])

    print()
    print("[OK] chunkzip decoded")
    print(f"     decoded size : {len(decoded)} bytes")

    entry0 = read_nested_big_entry(decoded, "0")

    print()
    print("[OK] nested entry 0 gevonden")
    print(f"     offset       : 0x{entry0['offset']:X}")
    print(f"     size         : {entry0['size']} bytes")

    apt = entry0["data"]

    start = APT_PATCH_OFFSET - 1
    end = APT_PATCH_OFFSET + 2

    actual = apt[start:end]

    print()
    print("[WC TEST] Target")
    print(f"     APT offset   : 0x{APT_PATCH_OFFSET:X}")
    print(f"     bytes        : {actual.hex(' ').upper()}")

    if actual == ORIGINAL:
        print()
        print("==============================================")
        print("PASS: originele bytes zijn exact A3 30 01")
        print("De GameHub is veilig klaar voor onze WC-test.")
        print("ER IS NOG NIETS AANGEPAST.")
        print("==============================================")
        return

    if actual == PATCHED:
        print()
        print("INFO: deze GameHub lijkt al gepatcht te zijn.")
        return

    raise RuntimeError(
        "STOP: bytes zijn anders dan verwacht. "
        "Er wordt niets aangepast."
    )


def apply_patch():
    data = bytearray(PATCH_BIG.read_bytes())
    gamehub = read_big4_entry(bytes(data), GAMEHUB_PATH)

    blob = gamehub["data"]
    decoded = bytearray(decode_chunkzip(blob))
    entry0 = read_nested_big_entry(bytes(decoded), "0")

    absolute_inside_decoded = (
        entry0["offset"] + APT_PATCH_OFFSET
    )

    before = bytes(
        decoded[
            absolute_inside_decoded - 1:
            absolute_inside_decoded + 2
        ]
    )

    if before == PATCHED:
        print("[INFO] Patch is al toegepast.")
        return

    if before != ORIGINAL:
        raise RuntimeError(
            f"STOP: verwacht A3 30 01, vond "
            f"{before.hex(' ').upper()}"
        )

    backup_dir = Path("backups") / "worldcup-gamehub-test"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup = backup_dir / "patch.big.before_wc_test"

    if not backup.exists():
        print(f"[BACKUP] {backup}")
        shutil.copy2(PATCH_BIG, backup)

    decoded[absolute_inside_decoded] = 0x58

    old_compressed_size = struct.unpack(">I", blob[40:44])[0]

    compressor = zlib.compressobj(
        level=9,
        method=zlib.DEFLATED,
        wbits=-15,
    )

    compressed = (
        compressor.compress(bytes(decoded))
        + compressor.flush()
    )

    if len(compressed) != old_compressed_size:
        raise RuntimeError(
            "STOP: recompressed GameHub heeft een andere grootte: "
            f"{len(compressed)} != {old_compressed_size}. "
            "patch.big blijft onaangeraakt."
        )

    new_blob = bytearray(blob)
    new_blob[48:48 + len(compressed)] = compressed

    # Final verification before touching patch.big.
    verify_decoded = decode_chunkzip(bytes(new_blob))
    verify_entry0 = read_nested_big_entry(verify_decoded, "0")

    verify = verify_entry0["data"][
        APT_PATCH_OFFSET - 1:
        APT_PATCH_OFFSET + 2
    ]

    if verify != PATCHED:
        raise RuntimeError(
            "Interne verification mislukt. "
            "patch.big blijft onaangeraakt."
        )

    outer_start = gamehub["offset"]
    outer_end = outer_start + gamehub["size"]

    if len(new_blob) != gamehub["size"]:
        raise RuntimeError("Outer GameHub record size veranderde.")

    data[outer_start:outer_end] = new_blob

    PATCH_BIG.write_bytes(data)

    print()
    print("==============================================")
    print("WC GAMEHUB TEST PATCH TOEGEPAST")
    print("A3 30 01 -> A3 58 01")
    print("Backup:", backup)
    print("==============================================")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Pas de WC GameHub proof-of-concept patch toe.",
    )

    args = parser.parse_args()

    if args.apply:
        apply_patch()
    else:
        check()


if __name__ == "__main__":
    main()