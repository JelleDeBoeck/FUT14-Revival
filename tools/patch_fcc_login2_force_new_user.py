from pathlib import Path
import shutil
import struct
import zlib
import os
from datetime import datetime

GAME = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game"
)

BIG_PATH = GAME / "patch.big"

TARGET_NAME = (
    "data/ui/external/ion_fut/screens/"
    "fcc_login2.big"
)

BACKUP_DIR = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\backups\fcc-login2-force-new-user"
)

INNER_NAME = "0"

# fcc_login2.apt - LoginFinalizedSuccessContinue()
#
# APT+0x0920:
#   ... AF 4A 4C
#       NEW_USER
#
# APT+0x0926:
#   9D 00 05 00 00 00
#       BranchIfTrue -> NewUserFlow
#
# APT+0x092C:
#   17
#   AE 21 AF 4C
#   12
#       KNOWN_USER_WITHOUT_STARTER_PACK
#       Not
#
# APT+0x0932:
#   9D 00 08 00 00 00
#       BranchIfTrue -> AllCustomThingsCreated
#
# Proof-test:
# neutraliseer alleen deze tweede branch.
# Daardoor valt execution door naar:
#   CallFuncPop 77 = NewUserFlow
APT_OFFSET = 0x0932

EXPECTED = bytes.fromhex(
    "9D 00 08 00 00 00"
)

PATCHED = bytes.fromhex(
    "9D 00 00 00 00 00"
)


def align(value, boundary=16):
    return (
        value + boundary - 1
    ) & ~(boundary - 1)


def decode_chunkzip(payload):
    if not payload.startswith(b"chunkzip"):
        return payload, False

    if len(payload) < 48:
        raise RuntimeError(
            "chunkzip payload te klein"
        )

    (
        version,
        output_size,
        chunk_size,
        count,
        alignment,
        flag_a,
        flag_b,
        flag_c,
    ) = struct.unpack_from(
        ">IIIIIIII",
        payload,
        8,
    )

    if version != 2:
        raise RuntimeError(
            f"onbekende chunkzip versie: {version}"
        )

    pos = 40
    output = bytearray()

    for index in range(count):
        if pos + 8 > len(payload):
            raise RuntimeError(
                f"chunk {index}: header buiten payload"
            )

        stored_size, compression_type = (
            struct.unpack_from(
                ">II",
                payload,
                pos,
            )
        )

        start = pos + 8
        end = start + stored_size

        if end > len(payload):
            raise RuntimeError(
                f"chunk {index}: data buiten payload"
            )

        stored = payload[start:end]

        if compression_type == 0:
            decoded = stored

        elif compression_type == 1:
            decoded = zlib.decompress(
                stored,
                -zlib.MAX_WBITS,
            )

        else:
            raise RuntimeError(
                "onbekend chunkzip "
                f"compression type: {compression_type}"
            )

        output.extend(decoded)

        pos = align(
            end + 8,
            alignment,
        ) - 8

    if len(output) != output_size:
        raise RuntimeError(
            "chunkzip decoded size klopt niet: "
            f"{len(output)} != {output_size}"
        )

    return bytes(output), True


def encode_chunkzip(decoded):
    compressor = zlib.compressobj(
        9,
        zlib.DEFLATED,
        -zlib.MAX_WBITS,
    )

    compressed = (
        compressor.compress(decoded)
        + compressor.flush()
    )

    return (
        b"chunkzip"
        + struct.pack(
            ">IIIIIIIIII",
            2,
            len(decoded),
            262_144,
            1,
            16,
            0,
            0,
            0,
            len(compressed),
            1,
        )
        + compressed
    )


def parse_big(data, expected_magic=None):
    magic = data[:4]

    if expected_magic is not None:
        if magic != expected_magic:
            raise RuntimeError(
                f"verwacht {expected_magic!r}, "
                f"kreeg {magic!r}"
            )
    elif magic not in (b"BIG4", b"BIGF"):
        raise RuntimeError(
            f"geen BIG archive: {magic!r}"
        )

    count = struct.unpack_from(
        ">I",
        data,
        8,
    )[0]

    pos = 16
    records = []

    for index in range(count):
        entry_pos = pos

        offset, size = struct.unpack_from(
            ">II",
            data,
            pos,
        )

        pos += 8

        end = data.find(
            b"\x00",
            pos,
        )

        if end == -1:
            raise RuntimeError(
                f"record {index}: "
                "filename terminator ontbreekt"
            )

        name = data[pos:end].decode(
            "utf-8",
            errors="replace",
        )

        pos = end + 1

        records.append(
            {
                "index": index,
                "entry_pos": entry_pos,
                "offset": offset,
                "size": size,
                "name": name,
            }
        )

    return records


def get_capacity(data, records, record):
    later_offsets = [
        r["offset"]
        for r in records
        if r["offset"] > record["offset"]
    ]

    if later_offsets:
        next_offset = min(later_offsets)
    else:
        next_offset = len(data)

    return next_offset - record["offset"]


def main():
    print("=" * 70)
    print("FIFA 14 EnterWC - force first-time branch TEST")
    print("=" * 70)

    archive = BIG_PATH.read_bytes()
    records = parse_big(
        archive,
        expected_magic=b"BIG4",
    )

    matches = [
        r for r in records
        if r["name"].lower()
        == TARGET_NAME.lower()
    ]

    if len(matches) != 1:
        raise SystemExit(
            "STOP: outer target niet uniek. "
            f"matches={len(matches)}"
        )

    outer = matches[0]

    outer_capacity = get_capacity(
        archive,
        records,
        outer,
    )

    print(
        f"[OUTER] record   : {outer['index']}"
    )
    print(
        f"[OUTER] offset   : 0x{outer['offset']:08X}"
    )
    print(
        f"[OUTER] size     : {outer['size']}"
    )
    print(
        f"[OUTER] capacity : {outer_capacity}"
    )

    outer_payload = archive[
        outer["offset"]:
        outer["offset"] + outer["size"]
    ]

    inner_big, was_chunkzip = (
        decode_chunkzip(outer_payload)
    )

    if not was_chunkzip:
        raise SystemExit(
            "STOP: EnterWC outer payload "
            "was geen chunkzip"
        )

    if inner_big[:4] != b"BIGF":
        raise SystemExit(
            "STOP: decoded EnterWC is geen BIGF"
        )

    inner_records = parse_big(
        inner_big,
        expected_magic=b"BIGF",
    )

    inner_matches = [
        r for r in inner_records
        if r["name"] == INNER_NAME
    ]

    if len(inner_matches) != 1:
        raise SystemExit(
            "STOP: inner APT record '0' "
            f"niet uniek ({len(inner_matches)})"
        )

    inner = inner_matches[0]

    print(
        f"[INNER] record   : {inner['index']}"
    )
    print(
        f"[INNER] offset   : 0x{inner['offset']:X}"
    )
    print(
        f"[INNER] size     : {inner['size']}"
    )

    apt_start = inner["offset"]
    apt_end = apt_start + inner["size"]

    apt = bytearray(
        inner_big[apt_start:apt_end]
    )

    if APT_OFFSET + len(EXPECTED) > len(apt):
        raise SystemExit(
            "STOP: APT patch-offset buiten record"
        )

    current = bytes(
        apt[
            APT_OFFSET:
            APT_OFFSET + len(EXPECTED)
        ]
    )

    print(
        f"[CHECK] APT+0x{APT_OFFSET:X}: "
        f"{current.hex(' ').upper()}"
    )

    if current == PATCHED:
        print()
        print(
            "[INFO] Deze proof-patch staat "
            "er al in."
        )
        print(
            "[INFO] Niets gewijzigd."
        )
        return

    if current != EXPECTED:
        raise SystemExit(
            "STOP: verwachte branchbytes "
            "staan niet op APT+0x0503"
        )

    apt[
        APT_OFFSET:
        APT_OFFSET + len(PATCHED)
    ] = PATCHED

    # Zelfde grootte: inner BIGF directory
    # hoeft niet aangepast te worden.
    patched_inner_big = bytearray(
        inner_big
    )

    patched_inner_big[
        apt_start:apt_end
    ] = apt

    patched_inner_big = bytes(
        patched_inner_big
    )

    # Harde inner read-back vóór compressie.
    verify_inner_records = parse_big(
        patched_inner_big,
        expected_magic=b"BIGF",
    )

    verify_inner = [
        r for r in verify_inner_records
        if r["name"] == INNER_NAME
    ][0]

    verify_apt = patched_inner_big[
        verify_inner["offset"]:
        verify_inner["offset"]
        + verify_inner["size"]
    ]

    if (
        verify_apt[
            APT_OFFSET:
            APT_OFFSET + len(PATCHED)
        ]
        != PATCHED
    ):
        raise SystemExit(
            "STOP: inner read-back faalde"
        )

    patched_outer_payload = (
        encode_chunkzip(
            patched_inner_big
        )
    )

    print(
        f"[INFO] nieuwe stored size: "
        f"{len(patched_outer_payload)}"
    )

    if len(patched_outer_payload) > outer_capacity:
        raise SystemExit(
            "STOP: nieuwe EnterWC payload "
            "past niet in fysieke BIG4-slot"
        )

    print()
    print("[PLAN]")
    print(
        "  EnterWC InitialLoginDone:"
    )
    print(
        "  BranchIfTrue +0x28 "
        "-> BranchIfTrue +0x00"
    )
    print(
        "  Hierdoor valt de test altijd "
        "door naar het NEW_USER-pad."
    )
    print(
        "  Geen backend-state wordt gewijzigd."
    )
    print()

    answer = input(
        "Patch schrijven? Typ exact YES: "
    )

    if answer != "YES":
        print(
            "Geannuleerd; niets gewijzigd."
        )
        return

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    backup = (
        BACKUP_DIR
        / f"patch.big.{stamp}.bak"
    )

    print(
        f"[BACKUP] {backup}"
    )

    shutil.copy2(
        BIG_PATH,
        backup,
    )

    with BIG_PATH.open("r+b") as handle:
        handle.seek(
            outer["offset"]
        )

        handle.write(
            patched_outer_payload
        )

        remaining = (
            outer_capacity
            - len(patched_outer_payload)
        )

        if remaining:
            handle.write(
                b"\x00" * remaining
            )

        # Alleen OUTER stored-size verandert.
        # Inner APT bleef exact even groot.
        handle.seek(
            outer["entry_pos"] + 4
        )

        handle.write(
            struct.pack(
                ">I",
                len(patched_outer_payload),
            )
        )

        handle.flush()
        os.fsync(
            handle.fileno()
        )

    # Definitieve on-disk read-back.
    disk = BIG_PATH.read_bytes()
    disk_records = parse_big(
        disk,
        expected_magic=b"BIG4",
    )

    disk_outer = [
        r for r in disk_records
        if r["name"].lower()
        == TARGET_NAME.lower()
    ]

    if len(disk_outer) != 1:
        raise SystemExit(
            "STOP: outer read-back lookup faalde"
        )

    disk_outer = disk_outer[0]

    disk_payload = disk[
        disk_outer["offset"]:
        disk_outer["offset"]
        + disk_outer["size"]
    ]

    disk_inner, _ = decode_chunkzip(
        disk_payload
    )

    disk_inner_records = parse_big(
        disk_inner,
        expected_magic=b"BIGF",
    )

    disk_apt_record = [
        r for r in disk_inner_records
        if r["name"] == INNER_NAME
    ]

    if len(disk_apt_record) != 1:
        raise SystemExit(
            "STOP: inner read-back lookup faalde"
        )

    disk_apt_record = disk_apt_record[0]

    disk_apt = disk_inner[
        disk_apt_record["offset"]:
        disk_apt_record["offset"]
        + disk_apt_record["size"]
    ]

    final = disk_apt[
        APT_OFFSET:
        APT_OFFSET + len(PATCHED)
    ]

    if final != PATCHED:
        raise SystemExit(
            "STOP: definitieve read-back faalde"
        )

    print()
    print("=" * 70)
    print("KLAAR")
    print("=" * 70)
    print(
        "EnterWC proof-patch staat op disk."
    )
    print(
        f"APT+0x{APT_OFFSET:X}: "
        f"{final.hex(' ').upper()}"
    )
    print(
        "On-disk read-back: OK"
    )
    print(
        f"Backup: {backup}"
    )


if __name__ == "__main__":
    main()