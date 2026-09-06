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
    "data/ui/layout/fut/futfluxhubcfg.xml"
)

OLD = b'DESTINATION="GOTO_STORE"'
NEW = b'DESTINATION="GOTO_WORLD_CUP"'

BACKUP_DIR = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\backups\wc-store-route"
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
                f"compression type: "
                f"{compression_type}"
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
            2,              # version
            len(decoded),   # output size
            262_144,        # chunk size
            1,              # chunk count
            16,             # alignment
            0,
            0,
            0,
            len(compressed),
            1,              # compressed
        )
        + compressed
    )


def parse_big(data):
    if data[:4] != b"BIG4":
        raise RuntimeError(
            f"verwacht BIG4, kreeg {data[:4]!r}"
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


def main():
    print("=" * 70)
    print("FIFA 14 WC Store-route test patch")
    print("=" * 70)

    archive = BIG_PATH.read_bytes()
    records = parse_big(archive)

    matches = [
        record
        for record in records
        if record["name"].lower()
        == TARGET_NAME.lower()
    ]

    if len(matches) != 1:
        raise SystemExit(
            "STOP: target record niet uniek. "
            f"matches={len(matches)}"
        )

    record = matches[0]

    print(
        f"[INFO] record : {record['index']}"
    )
    print(
        f"[INFO] offset : "
        f"0x{record['offset']:08X}"
    )
    print(
        f"[INFO] size   : {record['size']}"
    )
    print(
        f"[INFO] name   : {record['name']}"
    )

    later_offsets = [
        r["offset"]
        for r in records
        if r["offset"] > record["offset"]
    ]

    if later_offsets:
        next_offset = min(later_offsets)
    else:
        next_offset = len(archive)

    capacity = (
        next_offset - record["offset"]
    )

    print(
        f"[INFO] slot capacity: {capacity}"
    )

    start = record["offset"]
    end = start + record["size"]

    payload = archive[start:end]

    decoded, was_chunkzip = (
        decode_chunkzip(payload)
    )

    print(
        "[INFO] format :",
        "chunkzip" if was_chunkzip else "raw",
    )

    print(
        f"[INFO] decoded: {len(decoded)} bytes"
    )

    old_count = decoded.count(OLD)
    new_count = decoded.count(NEW)

    print(
        f"[INFO] GOTO_STORE exact count     : "
        f"{old_count}"
    )

    print(
        f"[INFO] GOTO_WORLD_CUP exact count : "
        f"{new_count}"
    )

    if old_count == 0:
        if new_count >= 2:
            print()
            print(
                "[INFO] Lijkt al gepatcht."
            )
            print(
                "Niets gewijzigd."
            )
            return

        raise SystemExit(
            "STOP: exacte GOTO_STORE "
            "destination niet gevonden"
        )

    if old_count != 1:
        raise SystemExit(
            "STOP: GOTO_STORE kwam niet "
            f"exact 1x voor ({old_count}x)"
        )

    patched_decoded = decoded.replace(
        OLD,
        NEW,
        1,
    )

    if (
        patched_decoded.count(OLD) != 0
        or patched_decoded.count(NEW)
        != new_count + 1
    ):
        raise SystemExit(
            "STOP: decoded verificatie faalde"
        )

    if was_chunkzip:
        patched_payload = encode_chunkzip(
            patched_decoded
        )
    else:
        patched_payload = patched_decoded

    print(
        f"[INFO] nieuwe stored size: "
        f"{len(patched_payload)}"
    )

    if len(patched_payload) > capacity:
        raise SystemExit(
            "STOP: nieuwe payload past niet "
            "in fysieke BIG4-slot"
        )

    print()
    print(
        "[PLAN] Store tile:"
    )
    print(
        '       GOTO_STORE -> GOTO_WORLD_CUP'
    )
    print(
        "[PLAN] Geen andere XML-route "
        "wordt gewijzigd."
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

    # Eerst payload schrijven.
    with BIG_PATH.open("r+b") as handle:
        handle.seek(
            record["offset"]
        )

        handle.write(
            patched_payload
        )

        remaining = (
            capacity
            - len(patched_payload)
        )

        if remaining:
            handle.write(
                b"\x00" * remaining
            )

        # BIG4 directory size aanpassen.
        handle.seek(
            record["entry_pos"] + 4
        )

        handle.write(
            struct.pack(
                ">I",
                len(patched_payload),
            )
        )

        handle.flush()
        os.fsync(
            handle.fileno()
        )

    # -----------------------------
    # Read-back verificatie
    # -----------------------------

    verify_archive = BIG_PATH.read_bytes()
    verify_records = parse_big(
        verify_archive
    )

    verify = [
        r
        for r in verify_records
        if r["name"].lower()
        == TARGET_NAME.lower()
    ]

    if len(verify) != 1:
        raise SystemExit(
            "STOP: read-back record lookup "
            "faalde"
        )

    verify_record = verify[0]

    verify_payload = verify_archive[
        verify_record["offset"]:
        verify_record["offset"]
        + verify_record["size"]
    ]

    verify_decoded, _ = (
        decode_chunkzip(
            verify_payload
        )
    )

    if verify_decoded.count(OLD) != 0:
        raise SystemExit(
            "STOP: read-back bevat "
            "nog GOTO_STORE"
        )

    if (
        verify_decoded.count(NEW)
        != new_count + 1
    ):
        raise SystemExit(
            "STOP: read-back WC count "
            "klopt niet"
        )

    print()
    print("=" * 70)
    print("KLAAR")
    print("=" * 70)
    print(
        "Store tile route is nu:"
    )
    print(
        "GOTO_STORE -> GOTO_WORLD_CUP"
    )
    print(
        "On-disk read-back: OK"
    )
    print(
        f"Backup: {backup}"
    )


if __name__ == "__main__":
    main()