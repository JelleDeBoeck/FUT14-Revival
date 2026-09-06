from pathlib import Path
import hashlib
import struct
import zlib


GAME = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game"
)

BIG_PATH = GAME / "data1.big"
BH_PATH = GAME / "data1.bh"

PATH_HASH = 0x4B5CD1DA3749E8E0


IDENTITIES = {
    "retail-original": {
        "size": 601,
        "stored": (
            "233b178542769cec15c32f73348d5c98"
            "f96df6e4cb9f72512231ce54f2f6fa7b"
        ),
        "decoded": (
            "a39c8e57e826cd22c6c17d16f20e6cf9"
            "1ad53e57dd85e1b9ec8f3c8e25a791e3"
        ),
        "target": b'"targets":["futLogIn2"]',
    },

    "advance-to-icebreaker": {
        "size": 598,
        "stored": (
            "95e3f1d31e695e8aded5b3df4c3a8109"
            "db27f227be1a050f0c232be9935d0a97"
        ),
        "decoded": (
            "4d71d20cb7292886a3835fafa261e83bc"
            "caed11b11888cfe3b2a2e03ff8a26f1"
        ),
        "target": b'"targets":["iceBreaker"]',
    },

    "advance-to-create-club": {
        "size": 596,
        "stored": (
            "9c2c1bcb440ce153c65c44a7ca982e2c"
            "b43e26028a51865bd2cc15b4541c959d"
        ),
        "decoded": (
            "24e7847e0278556e696c386bc1f5812be"
            "95c40c17a1fd8fd68b14201bf987885"
        ),
        "target": b'"targets":["createClub"]',
    },
}


STATE_MARKER = b'"name":"futLogIn1"'
NEXT_STATE_MARKER = b'"name":"futLogIn2"'
TRANSITIONS_MARKER = b'"transitions"'
ADVANCE_MARKER = b'"event":"advance"'


def sha256(data: bytes) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


def align(
    value: int,
    boundary: int = 16,
) -> int:
    return (
        value + boundary - 1
    ) & ~(boundary - 1)


def decode_chunkzip(
    payload: bytes,
) -> bytes:
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
        if pos + 8 > len(payload):
            raise ValueError(
                f"truncated chunk {index}"
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
                f"chunk {index} buiten payload"
            )

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
                "onbekend compressietype "
                f"{compression_type}"
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


def parse_bh_records(
    bh: bytes,
):
    if (
        len(bh) < 16
        or bh[:4] != b"ViV4"
    ):
        raise ValueError(
            "data1.bh is geen ViV4-index"
        )

    count = struct.unpack_from(
        ">I",
        bh,
        8,
    )[0]

    table_end = (
        16 + count * 20
    )

    if table_end > len(bh):
        raise ValueError(
            "BH record table is truncated"
        )

    rows = []

    for index in range(count):
        pos = (
            16 + index * 20
        )

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


def find_advance_target(
    decoded: bytes,
):
    state_start = decoded.find(
        STATE_MARKER
    )

    if state_start < 0:
        raise ValueError(
            "futLogIn1 niet gevonden"
        )

    if (
        decoded.find(
            STATE_MARKER,
            state_start + 1,
        )
        >= 0
    ):
        raise ValueError(
            "futLogIn1 niet uniek"
        )

    transitions_start = (
        decoded.find(
            TRANSITIONS_MARKER,
            state_start,
        )
    )

    next_state = decoded.find(
        NEXT_STATE_MARKER,
        transitions_start,
    )

    if (
        transitions_start < 0
        or next_state < 0
    ):
        raise ValueError(
            "futLogIn1 transitions "
            "niet begrensd"
        )

    advance_at = decoded.find(
        ADVANCE_MARKER,
        transitions_start,
        next_state,
    )

    if advance_at < 0:
        raise ValueError(
            "futLogIn1 advance "
            "niet gevonden"
        )

    next_event = decoded.find(
        b'"event":',
        advance_at
        + len(ADVANCE_MARKER),
        next_state,
    )

    if next_event >= 0:
        transition_end = next_event
    else:
        transition_end = next_state

    found = []

    for (
        name,
        identity,
    ) in IDENTITIES.items():

        marker = identity[
            "target"
        ]

        pos = decoded.find(
            marker,
            advance_at,
            transition_end,
        )

        if pos >= 0:
            found.append(
                (
                    name,
                    marker,
                )
            )

    if len(found) != 1:
        raise ValueError(
            "advance target is "
            "geen bekende reference-state"
        )

    return found[0]


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

    rows = parse_bh_records(
        bh
    )

    print(
        "BH records:",
        len(rows),
    )

    candidates = [
        row
        for row in rows
        if row["hash"] == PATH_HASH
    ]

    print(
        "Path-hash candidates:",
        len(candidates),
    )

    if not candidates:
        raise SystemExit(
            "STOP: futLogInFlow "
            "path-hash niet gevonden"
        )

    usable = []

    with BIG_PATH.open(
        "rb"
    ) as handle:

        for row in candidates:
            try:
                handle.seek(
                    row["offset"]
                )

                payload = handle.read(
                    row["size"]
                )

                if (
                    len(payload)
                    != row["size"]
                ):
                    raise ValueError(
                        "short read"
                    )

                decoded = (
                    decode_chunkzip(
                        payload
                    )
                )

                (
                    route_name,
                    route_marker,
                ) = find_advance_target(
                    decoded
                )

                usable.append(
                    (
                        row,
                        payload,
                        decoded,
                        route_name,
                        route_marker,
                    )
                )

            except Exception as exc:
                print(
                    "Candidate rejected:",
                    row["index"],
                    exc,
                )

    if len(usable) != 1:
        raise SystemExit(
            "STOP: geen unieke "
            "compatibele NAV-entry"
        )

    (
        row,
        payload,
        decoded,
        route_name,
        route_marker,
    ) = usable[0]

    stored_sha = sha256(
        payload
    )

    decoded_sha = sha256(
        decoded
    )

    exact_identity = None

    for (
        name,
        identity,
    ) in IDENTITIES.items():

        if (
            row["size"]
            == identity["size"]
            and stored_sha
            == identity["stored"]
            and decoded_sha
            == identity["decoded"]
        ):
            exact_identity = name
            break

    print()
    print(
        "record index:",
        row["index"],
    )

    print(
        "offset:",
        row["offset"],
    )

    print(
        "size:",
        row["size"],
    )

    print(
        "path hash:",
        f"{row['hash']:016X}",
    )

    print(
        "stored sha256:",
        stored_sha,
    )

    print(
        "decoded sha256:",
        decoded_sha,
    )

    print(
        "route target:",
        route_marker.decode(
            "ascii"
        ),
    )

    print(
        "route status:",
        route_name,
    )

    print(
        "EXACT REFERENCE IDENTITY:",
        exact_identity,
    )

    if exact_identity is None:
        raise SystemExit(
            "\nSTOP: structuur lijkt herkenbaar, "
            "maar bytes zijn geen exact "
            "reviewed reference identity."
        )

    print()
    print(
        "VERIFICATIE OK - "
        "er is niets gewijzigd."
    )


if __name__ == "__main__":
    main()