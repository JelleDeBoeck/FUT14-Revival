from pathlib import Path
import hashlib
import struct
import zlib


GAME = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game"
)

BIG_PATH = GAME / "patch.big"
BH_PATH = GAME / "patch.bh"

RECORD_INDEX = 2146
EXPECTED_OFFSET = 111_471_040
EXPECTED_SIZE = 20_481
EXPECTED_HASH = 0x56CC043AC27ECC11

EXPECTED_STORED_SHA256 = (
    "91e6b9ab3d6a603fff2a5ed73b81c4f"
    "472933663b153748e9647cb8d48ca46b6"
)

EXPECTED_DECODED_SHA256 = (
    "35b0c792c5e49a5b906a6b37c2fd281d"
    "2b6b13719266a19c27a328b9056ab571"
)


PATCHES = (
    (
        0x2C86,
        bytes.fromhex(
            "9d 00 28 00 00 00"
        ),
        bytes.fromhex(
            "99 00 64 00 00 00"
        ),
        (
            "checkForFUTRosters -> "
            "futSquadLoadSuccess"
        ),
    ),
    (
        0x2D92,
        bytes.fromhex(
            "9d 00 0c 00 00 00"
        ),
        bytes.fromhex(
            "9d 00 00 00 00 00"
        ),
        "LiveDB -> direct continuation",
    ),
    (
        0x2FEA,
        bytes.fromhex(
            "9d 00 b0 00 00 00"
        ),
        bytes.fromhex(
            "99 00 b0 00 00 00"
        ),
        (
            "proceedEnterFUT -> "
            "enterFutCallback"
        ),
    ),
)


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
    if payload[:8] != b"chunkzip":
        raise ValueError(
            "payload is geen chunkzip"
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
        or a != 0
        or b != 0
        or c != 0
    ):
        raise ValueError(
            "onverwachte chunkzip-layout"
        )

    pos = 40
    output = bytearray()

    for _ in range(count):
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
                "chunk loopt buiten payload"
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


def encode_chunkzip(
    decoded: bytes,
) -> bytes:
    candidates = []

    settings = (
        (
            9,
            9,
            zlib.Z_DEFAULT_STRATEGY,
        ),
        (
            9,
            8,
            zlib.Z_DEFAULT_STRATEGY,
        ),
        (
            8,
            9,
            zlib.Z_DEFAULT_STRATEGY,
        ),
        (
            8,
            8,
            zlib.Z_DEFAULT_STRATEGY,
        ),
        (
            9,
            9,
            zlib.Z_FILTERED,
        ),
        (
            9,
            8,
            zlib.Z_FILTERED,
        ),
    )

    for (
        level,
        mem_level,
        strategy,
    ) in settings:
        compressor = zlib.compressobj(
            level,
            zlib.DEFLATED,
            -zlib.MAX_WBITS,
            mem_level,
            strategy,
        )

        compressed = (
            compressor.compress(
                decoded
            )
            + compressor.flush()
        )

        candidates.append(
            compressed
        )

    compressed = min(
        candidates,
        key=len,
    )

    header = (
        b"chunkzip"
        + struct.pack(
            ">IIIIIIII",
            2,
            len(decoded),
            262_144,
            1,
            16,
            0,
            0,
            0,
        )
    )

    return (
        header
        + struct.pack(
            ">II",
            len(compressed),
            1,
        )
        + compressed
    )


def find_apt(
    decoded: bytes,
):
    if decoded[:4] not in (
        b"BIG4",
        b"BIGF",
    ):
        raise ValueError(
            "decoded package is geen BIG"
        )

    count = struct.unpack_from(
        ">I",
        decoded,
        8,
    )[0]

    header_size = struct.unpack_from(
        ">I",
        decoded,
        12,
    )[0]

    pos = 16
    matches = []

    for _ in range(count):
        offset, size = (
            struct.unpack_from(
                ">II",
                decoded,
                pos,
            )
        )

        pos += 8

        end = decoded.find(
            b"\0",
            pos,
            header_size,
        )

        if end == -1:
            raise ValueError(
                "kapotte BIG entry"
            )

        name = decoded[
            pos:end
        ].decode(
            "ascii"
        )

        pos = end + 1

        if (
            decoded[
                offset:
                offset + 9
            ]
            == b"Apt Data:"
        ):
            matches.append(
                (
                    name,
                    offset,
                    size,
                )
            )

    if len(matches) != 1:
        raise ValueError(
            "APT entry niet uniek"
        )

    (
        name,
        offset,
        size,
    ) = matches[0]

    if (
        name != "0"
        or offset != 64
        or size != 28_172
    ):
        raise ValueError(
            "onverwachte APT-layout"
        )

    return offset, size


def main():
    # ---------------------------------
    # Verifieer BH/index
    # ---------------------------------

    bh = BH_PATH.read_bytes()

    if bh[:4] != b"ViV4":
        raise SystemExit(
            "STOP: patch.bh layout onbekend"
        )

    count = struct.unpack_from(
        ">I",
        bh,
        8,
    )[0]

    if RECORD_INDEX >= count:
        raise SystemExit(
            "STOP: record ontbreekt"
        )

    record_pos = (
        16
        + RECORD_INDEX * 20
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
        record_pos,
    )

    path_hash = (
        hash_hi << 32
    ) | hash_lo

    if (
        offset != EXPECTED_OFFSET
        or size != EXPECTED_SIZE
        or path_hash != EXPECTED_HASH
    ):
        raise SystemExit(
            "STOP: archive-layout wijkt af"
        )

    # ---------------------------------
    # Lees originele payload
    # ---------------------------------

    with BIG_PATH.open(
        "rb"
    ) as handle:
        handle.seek(
            offset
        )

        payload = handle.read(
            size
        )

    if len(payload) != size:
        raise SystemExit(
            "STOP: payload kon niet "
            "volledig gelezen worden"
        )

    if (
        sha256(payload)
        != EXPECTED_STORED_SHA256
    ):
        raise SystemExit(
            "STOP: originele payload "
            "SHA klopt niet"
        )

    # ---------------------------------
    # Decodeer + verifieer
    # ---------------------------------

    decoded = decode_chunkzip(
        payload
    )

    if (
        sha256(decoded)
        != EXPECTED_DECODED_SHA256
    ):
        raise SystemExit(
            "STOP: decoded payload "
            "SHA klopt niet"
        )

    apt_offset, apt_size = (
        find_apt(
            decoded
        )
    )

    apt = bytearray(
        decoded[
            apt_offset:
            apt_offset + apt_size
        ]
    )

    print(
        "Originele helperFunctions "
        "verified."
    )

    # ---------------------------------
    # Drie frontend-branches
    # ---------------------------------

    for (
        patch_offset,
        expected,
        replacement,
        description,
    ) in PATCHES:

        actual = bytes(
            apt[
                patch_offset:
                patch_offset
                + len(expected)
            ]
        )

        if actual != expected:
            raise SystemExit(
                f"STOP @ "
                f"0x{patch_offset:X}: "
                f"verwacht "
                f"{expected.hex(' ')}, "
                f"kreeg "
                f"{actual.hex(' ')}"
            )

        print(
            f"PATCH "
            f"0x{patch_offset:X}: "
            f"{description}"
        )

        apt[
            patch_offset:
            patch_offset
            + len(replacement)
        ] = replacement

    # ---------------------------------
    # Plaats APT terug
    # ---------------------------------

    patched_decoded = bytearray(
        decoded
    )

    patched_decoded[
        apt_offset:
        apt_offset + apt_size
    ] = apt

    # Grootte van decoded package
    # mag niet veranderen.
    if (
        len(patched_decoded)
        != len(decoded)
    ):
        raise SystemExit(
            "STOP: decoded package "
            "grootte veranderde"
        )

    # ---------------------------------
    # Recompress
    # ---------------------------------

    patched_payload = (
        encode_chunkzip(
            bytes(
                patched_decoded
            )
        )
    )

    # Controleer dat onze eigen
    # encoder exact terug decodeert.
    try:
        verification = (
            decode_chunkzip(
                patched_payload
            )
        )
    except Exception as exc:
        raise SystemExit(
            "STOP: recompress kon "
            f"niet geverifieerd worden: "
            f"{exc}"
        )

    if (
        verification
        != bytes(patched_decoded)
    ):
        raise SystemExit(
            "STOP: recompress "
            "verification faalde"
        )

    if len(patched_payload) > size:
        raise SystemExit(
            "STOP: patched payload "
            "past niet in originele slot"
        )

    print(
        "Patched payload size:",
        len(patched_payload),
        "/",
        size,
    )

    # ---------------------------------
    # Expliciete bevestiging
    # ---------------------------------

    answer = input(
        "Schrijf patch naar patch.big? "
        "Typ exact YES: "
    )

    if answer != "YES":
        print(
            "Geannuleerd; "
            "niets gewijzigd."
        )
        return

    # ---------------------------------
    # Schrijf BIG
    # ---------------------------------

    with BIG_PATH.open(
        "r+b"
    ) as handle:
        handle.seek(
            offset
        )

        handle.write(
            patched_payload
        )

        remaining = (
            size
            - len(patched_payload)
        )

        if remaining:
            handle.write(
                b"\0" * remaining
            )

        handle.flush()

    # ---------------------------------
    # Update grootte in BH
    # ---------------------------------

    patched_bh = bytearray(
        bh
    )

    struct.pack_into(
        ">I",
        patched_bh,
        record_pos + 4,
        len(patched_payload),
    )

    BH_PATH.write_bytes(
        patched_bh
    )

    # ---------------------------------
    # Read-back verificatie
    # ---------------------------------

    written_bh = (
        BH_PATH.read_bytes()
    )

    (
        written_offset,
        written_size,
    ) = struct.unpack_from(
        ">II",
        written_bh,
        record_pos,
    )

    if written_offset != offset:
        raise SystemExit(
            "STOP: BH offset "
            "veranderde onverwacht"
        )

    if (
        written_size
        != len(patched_payload)
    ):
        raise SystemExit(
            "STOP: BH size "
            "update faalde"
        )

    with BIG_PATH.open(
        "rb"
    ) as handle:
        handle.seek(
            written_offset
        )

        written_payload = (
            handle.read(
                written_size
            )
        )

    if (
        written_payload
        != patched_payload
    ):
        raise SystemExit(
            "STOP: BIG read-back "
            "wijkt af"
        )

    try:
        written_decoded = (
            decode_chunkzip(
                written_payload
            )
        )
    except Exception as exc:
        raise SystemExit(
            "STOP: on-disk payload "
            f"decode faalde: {exc}"
        )

    if (
        written_decoded
        != bytes(patched_decoded)
    ):
        raise SystemExit(
            "STOP: on-disk "
            "verificatie faalde"
        )

    print()
    print(
        "KLAAR: branch-offline "
        "patch toegepast."
    )
    print(
        "BH size:",
        written_size,
    )
    print(
        "On-disk verificatie: OK"
    )


if __name__ == "__main__":
    main()