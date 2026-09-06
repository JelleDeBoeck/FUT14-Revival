from pathlib import Path
import hashlib
import os
import struct
import tempfile
import zlib


GAME = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game"
)

BIG_PATH = GAME / "data1.big"
BH_PATH = GAME / "data1.bh"

PATH_HASH = 0x4B5CD1DA3749E8E0

EXPECTED_ORIGINAL_SIZE = 601

EXPECTED_ORIGINAL_STORED = (
    "233b178542769cec15c32f73348d5c98"
    "f96df6e4cb9f72512231ce54f2f6fa7b"
)

EXPECTED_ORIGINAL_DECODED = (
    "a39c8e57e826cd22c6c17d16f20e6cf9"
    "1ad53e57dd85e1b9ec8f3c8e25a791e3"
)

EXPECTED_PATCHED_SIZE = 598

EXPECTED_PATCHED_STORED = (
    "95e3f1d31e695e8aded5b3df4c3a8109"
    "db27f227be1a050f0c232be9935d0a97"
)

EXPECTED_PATCHED_DECODED = (
    "4d71d20cb7292886a3835fafa261e83b"
    "ccaed11b11888cfe3b2a2e03ff8a26f1"
)

OLD_TARGET = b'"targets":["futLogIn2"]'
NEW_TARGET = b'"targets":["iceBreaker"]'

STATE_MARKER = b'"name":"futLogIn1"'
NEXT_STATE_MARKER = b'"name":"futLogIn2"'
TRANSITIONS_MARKER = b'"transitions"'
ADVANCE_MARKER = b'"event":"advance"'


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

        os.replace(
            temp_name,
            path,
        )

    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass

        raise


def decode_chunkzip(payload):
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
        flag_a,
        flag_b,
        flag_c,
    ) = struct.unpack_from(
        ">IIIIIIII",
        payload,
        8,
    )

    if (
        version != 2
        or alignment != 16
        or flag_a
        or flag_b
        or flag_c
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

        stored = payload[
            start:end
        ]

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

        output.extend(
            decoded
        )

        pos = align(
            end + 8
        ) - 8

    if len(output) != output_size:
        raise ValueError(
            "decoded grootte klopt niet"
        )

    return bytes(output)


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


def parse_bh(bh):
    if (
        len(bh) < 16
        or bh[:4] != b"ViV4"
    ):
        raise ValueError(
            "data1.bh is geen ViV4"
        )

    count = struct.unpack_from(
        ">I",
        bh,
        8,
    )[0]

    rows = []

    for index in range(count):
        pos = 16 + index * 20

        (
            offset,
            size,
            reserved,
            hash_hi,
            hash_lo,
        ) = struct.unpack_from(
            ">IIIII",
            bh,
            pos,
        )

        rows.append(
            {
                "index": index,
                "pos": pos,
                "offset": offset,
                "size": size,
                "hash": (
                    hash_hi << 32
                ) | hash_lo,
            }
        )

    return rows


def find_record(
    bh,
):
    rows = parse_bh(
        bh
    )

    candidates = [
        row
        for row in rows
        if row["hash"] == PATH_HASH
    ]

    if len(candidates) != 1:
        raise SystemExit(
            "STOP: NAV path-hash "
            "niet uniek gevonden"
        )

    record = candidates[0]

    later_offsets = [
        row["offset"]
        for row in rows
        if row["offset"]
        > record["offset"]
    ]

    big_size = BIG_PATH.stat().st_size

    if later_offsets:
        next_offset = min(
            later_offsets
        )
    else:
        next_offset = big_size

    record["capacity"] = (
        next_offset
        - record["offset"]
    )

    return record


def find_target(decoded):
    state_start = decoded.find(
        STATE_MARKER
    )

    if state_start < 0:
        raise SystemExit(
            "STOP: futLogIn1 "
            "niet gevonden"
        )

    transitions_start = decoded.find(
        TRANSITIONS_MARKER,
        state_start,
    )

    next_state = decoded.find(
        NEXT_STATE_MARKER,
        transitions_start,
    )

    advance_at = decoded.find(
        ADVANCE_MARKER,
        transitions_start,
        next_state,
    )

    if (
        transitions_start < 0
        or next_state < 0
        or advance_at < 0
    ):
        raise SystemExit(
            "STOP: advance transition "
            "niet gevonden"
        )

    target_pos = decoded.find(
        OLD_TARGET,
        advance_at,
        next_state,
    )

    if target_pos < 0:
        raise SystemExit(
            "STOP: huidige target "
            "is niet futLogIn2"
        )

    return target_pos


def main():
    bh = BH_PATH.read_bytes()

    record = find_record(
        bh
    )

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
        "slot capacity:",
        record["capacity"],
    )

    if (
        record["size"]
        != EXPECTED_ORIGINAL_SIZE
    ):
        raise SystemExit(
            "STOP: record size "
            "is niet retail-original"
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
        != EXPECTED_ORIGINAL_STORED
    ):
        raise SystemExit(
            "STOP: stored SHA "
            "is niet retail-original"
        )

    decoded = decode_chunkzip(
        payload
    )

    if (
        sha256(decoded)
        != EXPECTED_ORIGINAL_DECODED
    ):
        raise SystemExit(
            "STOP: decoded SHA "
            "is niet retail-original"
        )

    print(
        "Retail-original verified."
    )

    target_pos = find_target(
        decoded
    )

    patched_decoded = (
        decoded[:target_pos]
        + NEW_TARGET
        + decoded[
            target_pos
            + len(OLD_TARGET):
        ]
    )

    if (
        sha256(patched_decoded)
        != EXPECTED_PATCHED_DECODED
    ):
        raise SystemExit(
            "STOP: transformed NAV "
            "matches niet met "
            "reviewed Icebreaker identity"
        )

    patched_payload = (
        encode_chunkzip(
            patched_decoded
        )
    )

    print(
        "Patched payload size:",
        len(patched_payload),
    )

    if (
        len(patched_payload)
        != EXPECTED_PATCHED_SIZE
    ):
        raise SystemExit(
            "STOP: patched size "
            "klopt niet"
        )

    if (
        sha256(patched_payload)
        != EXPECTED_PATCHED_STORED
    ):
        raise SystemExit(
            "STOP: patched stored SHA "
            "klopt niet"
        )

    if (
        len(patched_payload)
        > record["capacity"]
    ):
        raise SystemExit(
            "STOP: patched payload "
            "past niet in fysieke slot"
        )

    print(
        "Icebreaker target verified."
    )

    answer = input(
        "Schrijf NAV patch? "
        "Typ exact YES: "
    )

    if answer != "YES":
        print(
            "Geannuleerd; niets gewijzigd."
        )
        return

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
                record["capacity"]
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

    # ----------------------------
    # Read-back verificatie
    # ----------------------------

    verify_bh = BH_PATH.read_bytes()

    verify_size = struct.unpack_from(
        ">I",
        verify_bh,
        record["pos"] + 4,
    )[0]

    if (
        verify_size
        != EXPECTED_PATCHED_SIZE
    ):
        raise SystemExit(
            "STOP: BH size "
            "read-back faalde"
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

    verify_decoded = (
        decode_chunkzip(
            verify_payload
        )
    )

    if (
        sha256(verify_payload)
        != EXPECTED_PATCHED_STORED
    ):
        raise SystemExit(
            "STOP: on-disk stored SHA "
            "faalde"
        )

    if (
        sha256(verify_decoded)
        != EXPECTED_PATCHED_DECODED
    ):
        raise SystemExit(
            "STOP: on-disk decoded SHA "
            "faalde"
        )

    print()
    print(
        "KLAAR: FUT NAV route gepatched."
    )

    print(
        "Nieuwe route: "
        "futLogIn1 / advance -> iceBreaker"
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