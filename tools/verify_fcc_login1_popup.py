from pathlib import Path
import hashlib
import struct
import zlib


GAME = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game"
)

BIG_PATH = GAME / "cards0.big"
BH_PATH = GAME / "cards0.bh"

KNOWN_RECORD_INDEX = 3891
KNOWN_RECORD_OFFSET = 58_286_528
KNOWN_RECORD_COUNT = 3957
KNOWN_NEXT_RECORD_OFFSET = 58_288_256
KNOWN_PATH_HASH = 0x29333257A32EB487

APT_ENTRY_NAME = "0"
APT_ENTRY_OFFSET = 0x40
APT_ENTRY_SIZE = 0x5B5
APT_PATCH_OFFSET = 0xCA

RETAIL_OPCODE = 0x49
PATCHED_OPCODE = 0x11

EXPECTED_CONTEXT_PREFIX = bytes.fromhex(
    "b9 01 af 07 af 08 5a b9 01 af 04 af 09 a2 0a 52 73"
)

EXPECTED_CONTEXT_SUFFIX = bytes.fromhex(
    "12 12 9d 00 00 30 00 00 00"
)

LOADING_LITERAL = b"Loading"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, boundary: int = 16) -> int:
    return (
        value + boundary - 1
    ) & ~(boundary - 1)


def parse_bh(data: bytes):
    if (
        len(data) < 16
        or data[:4] != b"ViV4"
    ):
        raise ValueError(
            "cards0.bh is geen ViV4"
        )

    count = struct.unpack_from(
        ">I",
        data,
        8,
    )[0]

    records = []

    for index in range(count):
        pos = 16 + index * 20

        (
            offset,
            size,
            reserved,
            hi,
            lo,
        ) = struct.unpack_from(
            ">IIIII",
            data,
            pos,
        )

        records.append(
            {
                "index": index,
                "offset": offset,
                "size": size,
                "reserved": reserved,
                "path_hash": (
                    hi << 32
                ) | lo,
            }
        )

    return records


def decode_chunkzip(payload: bytes) -> bytes:
    if (
        len(payload) < 48
        or payload[:8] != b"chunkzip"
    ):
        raise ValueError(
            "record is geen chunkzip"
        )

    (
        version,
        output_size,
        chunk_size,
        count,
        alignment,
        a,
        b,
        c,
    ) = struct.unpack_from(
        ">IIIIIIII",
        payload,
        8,
    )

    if (
        version != 2
        or alignment != 16
        or a
        or b
        or c
    ):
        raise ValueError(
            "onbekende chunkzip-header"
        )

    pos = 40
    output = bytearray()

    for index in range(count):
        (
            stored_size,
            compression_type,
        ) = struct.unpack_from(
            ">II",
            payload,
            pos,
        )

        start = pos + 8
        end = start + stored_size

        if end > len(payload):
            raise ValueError(
                f"chunk {index} buiten payload"
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
            raise ValueError(
                "onbekend compressietype"
            )

        output.extend(decoded)

        pos = align(
            end + 8
        ) - 8

    if len(output) != output_size:
        raise ValueError(
            "decoded grootte klopt niet"
        )

    return bytes(output)


def parse_big_entries(data: bytes):
    if data[:4] not in (
        b"BIG4",
        b"BIGF",
    ):
        raise ValueError(
            "decoded package is geen BIG4/BIGF"
        )

    count = struct.unpack_from(
        ">I",
        data,
        8,
    )[0]

    header_size = struct.unpack_from(
        ">I",
        data,
        12,
    )[0]

    entries = []
    pos = 16

    for index in range(count):
        if pos + 8 > header_size:
            raise ValueError(
                "BIG entry table truncated"
            )

        offset, size = struct.unpack_from(
            ">II",
            data,
            pos,
        )

        pos += 8

        end = data.find(
            b"\0",
            pos,
            header_size,
        )

        if end < 0:
            raise ValueError(
                "BIG entry naam niet afgesloten"
            )

        name = data[
            pos:end
        ].decode(
            "ascii",
            errors="strict",
        )

        pos = end + 1

        if offset + size > len(data):
            raise ValueError(
                "BIG entry buiten decoded package"
            )

        entries.append(
            {
                "index": index,
                "name": name,
                "offset": offset,
                "size": size,
            }
        )

    return entries


def main():
    if not BIG_PATH.exists():
        raise SystemExit(
            f"STOP: ontbreekt: {BIG_PATH}"
        )

    if not BH_PATH.exists():
        raise SystemExit(
            f"STOP: ontbreekt: {BH_PATH}"
        )

    bh = BH_PATH.read_bytes()
    records = parse_bh(bh)

    print(
        "BH records:",
        len(records),
    )

    if len(records) != KNOWN_RECORD_COUNT:
        raise SystemExit(
            "STOP: cards0 record count "
            "wijkt af van reviewed reference"
        )

    record = records[
        KNOWN_RECORD_INDEX
    ]

    next_record = records[
        KNOWN_RECORD_INDEX + 1
    ]

    print(
        "record index:",
        record["index"],
    )
    print(
        "offset:",
        record["offset"],
    )
    print(
        "size:",
        record["size"],
    )
    print(
        "path hash:",
        f"{record['path_hash']:016X}",
    )
    print(
        "next offset:",
        next_record["offset"],
    )

    if (
        record["offset"]
        != KNOWN_RECORD_OFFSET
    ):
        raise SystemExit(
            "STOP: record offset mismatch"
        )

    if record["reserved"] != 0:
        raise SystemExit(
            "STOP: reserved field mismatch"
        )

    if (
        record["path_hash"]
        != KNOWN_PATH_HASH
    ):
        raise SystemExit(
            "STOP: path hash mismatch"
        )

    if (
        next_record["offset"]
        != KNOWN_NEXT_RECORD_OFFSET
    ):
        raise SystemExit(
            "STOP: next-record boundary mismatch"
        )

    capacity = (
        next_record["offset"]
        - record["offset"]
    )

    print(
        "slot capacity:",
        capacity,
    )

    with BIG_PATH.open("rb") as handle:
        handle.seek(
            record["offset"]
        )

        stored = handle.read(
            record["size"]
        )

    if (
        len(stored)
        != record["size"]
    ):
        raise SystemExit(
            "STOP: short read"
        )

    decoded = decode_chunkzip(
        stored
    )

    entries = parse_big_entries(
        decoded
    )

    matches = [
        entry
        for entry in entries
        if entry["name"]
        == APT_ENTRY_NAME
    ]

    if len(matches) != 1:
        raise SystemExit(
            "STOP: APT entry '0' "
            "niet uniek gevonden"
        )

    apt = matches[0]

    print(
        "APT entry offset:",
        apt["offset"],
    )
    print(
        "APT entry size:",
        apt["size"],
    )

    if (
        apt["offset"]
        != APT_ENTRY_OFFSET
        or apt["size"]
        != APT_ENTRY_SIZE
    ):
        raise SystemExit(
            "STOP: APT layout mismatch"
        )

    blob = decoded[
        apt["offset"]:
        apt["offset"] + apt["size"]
    ]

    if not blob.startswith(
        b"Apt Data"
    ):
        raise SystemExit(
            "STOP: geen Apt Data magic"
        )

    opcode = blob[
        APT_PATCH_OFFSET
    ]

    print(
        "APT+0xCA:",
        f"0x{opcode:02X}",
    )

    if opcode not in (
        RETAIL_OPCODE,
        PATCHED_OPCODE,
    ):
        raise SystemExit(
            "STOP: onverwachte opcode"
        )

    context_start = (
        APT_PATCH_OFFSET
        - len(
            EXPECTED_CONTEXT_PREFIX
        )
    )

    context_end = (
        APT_PATCH_OFFSET
        + 1
        + len(
            EXPECTED_CONTEXT_SUFFIX
        )
    )

    actual_context = blob[
        context_start:
        context_end
    ]

    expected_context = (
        EXPECTED_CONTEXT_PREFIX
        + bytes([opcode])
        + EXPECTED_CONTEXT_SUFFIX
    )

    if (
        actual_context
        != expected_context
    ):
        raise SystemExit(
            "STOP: BeginLogin instruction "
            "context mismatch"
        )

    if (
        decoded.count(
            LOADING_LITERAL
        )
        < 1
    ):
        raise SystemExit(
            "STOP: Loading literal "
            "niet gevonden"
        )

    if opcode == RETAIL_OPCODE:
        status = "retail-original"
    else:
        status = "popup-bypass-already-patched"

    print()
    print(
        "stored sha256:",
        sha256(stored),
    )

    print(
        "decoded sha256:",
        sha256(decoded),
    )

    print(
        "status:",
        status,
    )

    print()
    print(
        "VERIFICATIE OK - "
        "er is niets gewijzigd."
    )


if __name__ == "__main__":
    main()