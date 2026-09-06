from pathlib import Path
import hashlib
import os
import struct
import tempfile
import zlib


GAME = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game"
)

BIG_PATH = GAME / "cards0.big"
BH_PATH = GAME / "cards0.bh"

RECORD_INDEX = 3891
EXPECTED_OFFSET = 58_286_528
EXPECTED_PATH_HASH = 0x29333257A32EB487
EXPECTED_NEXT_OFFSET = 58_288_256

EXPECTED_RETAIL_SIZE = 1723
EXPECTED_RETAIL_STORED_SHA = (
    "e80eea2d577fe83a4a90a005dada7136"
    "5090b140f82df1d701723b57537b70a1"
)
EXPECTED_RETAIL_DECODED_SHA = (
    "3c92c6362d1675408d3ce43030afa2d0"
    "5a1ecc12419f06d881afa67c7ff57c4c"
)

APT_ENTRY_OFFSET = 64
APT_ENTRY_SIZE = 1461
APT_PATCH_OFFSET = 0xCA

RETAIL_OPCODE = 0x49
PATCHED_OPCODE = 0x11

EXPECTED_CONTEXT_PREFIX = bytes.fromhex(
    "b9 01 af 07 af 08 5a b9 01 af 04 af 09 a2 0a 52 73"
)

EXPECTED_CONTEXT_SUFFIX = bytes.fromhex(
    "12 12 9d 00 00 30 00 00 00"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def align(value, boundary=16):
    return (
        value + boundary - 1
    ) & ~(boundary - 1)


def atomic_write(path, data):
    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temp_name, path)

    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def parse_bh(data):
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
                "pos": pos,
                "offset": offset,
                "size": size,
                "reserved": reserved,
                "path_hash": (
                    hi << 32
                ) | lo,
            }
        )

    return records


def decode_chunkzip(payload):
    if (
        len(payload) < 48
        or payload[:8] != b"chunkzip"
    ):
        raise ValueError(
            "geen chunkzip"
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
        if pos + 8 > len(payload):
            raise ValueError(
                "truncated chunk"
            )

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
                "chunk buiten payload"
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


def encode_chunkzip(decoded):
    candidates = []

    for level in range(1, 10):
        compressor = zlib.compressobj(
            level,
            zlib.DEFLATED,
            -zlib.MAX_WBITS,
        )

        compressed = (
            compressor.compress(decoded)
            + compressor.flush()
        )

        payload = (
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

        candidates.append(payload)

    return min(
        candidates,
        key=len,
    )


def verify_context(blob, opcode):
    start = (
        APT_PATCH_OFFSET
        - len(EXPECTED_CONTEXT_PREFIX)
    )

    end = (
        APT_PATCH_OFFSET
        + 1
        + len(EXPECTED_CONTEXT_SUFFIX)
    )

    expected = (
        EXPECTED_CONTEXT_PREFIX
        + bytes([opcode])
        + EXPECTED_CONTEXT_SUFFIX
    )

    if blob[start:end] != expected:
        raise SystemExit(
            "STOP: instruction context mismatch"
        )


def main():
    bh = BH_PATH.read_bytes()
    records = parse_bh(bh)

    if len(records) <= RECORD_INDEX + 1:
        raise SystemExit(
            "STOP: BH record table te klein"
        )

    record = records[RECORD_INDEX]
    next_record = records[
        RECORD_INDEX + 1
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

    if (
        record["offset"] != EXPECTED_OFFSET
        or record["path_hash"]
        != EXPECTED_PATH_HASH
        or record["reserved"] != 0
    ):
        raise SystemExit(
            "STOP: record identity mismatch"
        )

    if (
        next_record["offset"]
        != EXPECTED_NEXT_OFFSET
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

    if (
        record["size"]
        != EXPECTED_RETAIL_SIZE
    ):
        raise SystemExit(
            "STOP: record is niet "
            "retail-original size"
        )

    with BIG_PATH.open("rb") as handle:
        handle.seek(
            record["offset"]
        )
        payload = handle.read(
            record["size"]
        )

    if (
        sha256(payload)
        != EXPECTED_RETAIL_STORED_SHA
    ):
        raise SystemExit(
            "STOP: retail stored SHA mismatch"
        )

    decoded = decode_chunkzip(
        payload
    )

    if (
        sha256(decoded)
        != EXPECTED_RETAIL_DECODED_SHA
    ):
        raise SystemExit(
            "STOP: retail decoded SHA mismatch"
        )

    if (
        APT_ENTRY_OFFSET
        + APT_ENTRY_SIZE
        > len(decoded)
    ):
        raise SystemExit(
            "STOP: APT entry buiten package"
        )

    apt = decoded[
        APT_ENTRY_OFFSET:
        APT_ENTRY_OFFSET
        + APT_ENTRY_SIZE
    ]

    if not apt.startswith(
        b"Apt Data"
    ):
        raise SystemExit(
            "STOP: Apt Data magic ontbreekt"
        )

    opcode = apt[
        APT_PATCH_OFFSET
    ]

    print(
        "APT+0xCA:",
        f"0x{opcode:02X}",
    )

    if opcode != RETAIL_OPCODE:
        raise SystemExit(
            "STOP: opcode is niet retail 0x49"
        )

    verify_context(
        apt,
        RETAIL_OPCODE,
    )

    print(
        "Retail instruction verified."
    )

    absolute_patch = (
        APT_ENTRY_OFFSET
        + APT_PATCH_OFFSET
    )

    patched_decoded = bytearray(
        decoded
    )

    patched_decoded[
        absolute_patch
    ] = PATCHED_OPCODE

    patched_decoded = bytes(
        patched_decoded
    )

    patched_apt = patched_decoded[
        APT_ENTRY_OFFSET:
        APT_ENTRY_OFFSET
        + APT_ENTRY_SIZE
    ]

    verify_context(
        patched_apt,
        PATCHED_OPCODE,
    )

    # Exactly one decoded byte must differ.
    differences = [
        i
        for i, (old, new)
        in enumerate(
            zip(
                decoded,
                patched_decoded,
            )
        )
        if old != new
    ]

    if differences != [
        absolute_patch
    ]:
        raise SystemExit(
            "STOP: meer dan één decoded byte gewijzigd"
        )

    patched_payload = encode_chunkzip(
        patched_decoded
    )

    print(
        "Patched payload size:",
        len(patched_payload),
        "/",
        capacity,
    )

    print(
        "Patched decoded sha256:",
        sha256(patched_decoded),
    )

    print(
        "Patched stored sha256:",
        sha256(patched_payload),
    )

    if len(patched_payload) > capacity:
        raise SystemExit(
            "STOP: patched payload "
            "past niet in slot"
        )

    print(
        "Popup-bypass transformation verified."
    )

    answer = input(
        "Schrijf FCC login1 patch? "
        "Typ exact YES: "
    )

    if answer != "YES":
        print(
            "Geannuleerd; niets gewijzigd."
        )
        return

    # Write BIG first. BH remains valid until
    # the size field is atomically replaced below.
    with BIG_PATH.open(
        "r+b"
    ) as handle:

        handle.seek(
            record["offset"]
        )

        handle.write(
            patched_payload
        )

        handle.write(
            b"\0"
            * (
                capacity
                - len(patched_payload)
            )
        )

        handle.flush()
        os.fsync(
            handle.fileno()
        )

    patched_bh = bytearray(
        bh
    )

    struct.pack_into(
        ">I",
        patched_bh,
        record["pos"] + 4,
        len(patched_payload),
    )

    atomic_write(
        BH_PATH,
        bytes(patched_bh),
    )

    # Read-back verification.
    verify_bh = BH_PATH.read_bytes()

    verify_size = struct.unpack_from(
        ">I",
        verify_bh,
        record["pos"] + 4,
    )[0]

    if verify_size != len(
        patched_payload
    ):
        raise SystemExit(
            "STOP: BH read-back size mismatch"
        )

    with BIG_PATH.open(
        "rb"
    ) as handle:

        handle.seek(
            record["offset"]
        )

        verify_payload = handle.read(
            verify_size
        )

    if (
        verify_payload
        != patched_payload
    ):
        raise SystemExit(
            "STOP: BIG read-back mismatch"
        )

    verify_decoded = decode_chunkzip(
        verify_payload
    )

    if (
        verify_decoded
        != patched_decoded
    ):
        raise SystemExit(
            "STOP: decoded read-back mismatch"
        )

    verify_apt = verify_decoded[
        APT_ENTRY_OFFSET:
        APT_ENTRY_OFFSET
        + APT_ENTRY_SIZE
    ]

    if (
        verify_apt[APT_PATCH_OFFSET]
        != PATCHED_OPCODE
    ):
        raise SystemExit(
            "STOP: patched opcode read-back mismatch"
        )

    verify_context(
        verify_apt,
        PATCHED_OPCODE,
    )

    print()
    print(
        "KLAAR: FCC login1 popup patch toegepast."
    )
    print(
        "APT+0xCA: 0x49 -> 0x11"
    )
    print(
        "BH size:",
        verify_size,
    )
    print(
        "On-disk verificatie: OK"
    )


if __name__ == "__main__":
    main()