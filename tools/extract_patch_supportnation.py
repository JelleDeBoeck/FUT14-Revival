from pathlib import Path
import zlib
import struct


ARCHIVE = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\patch.big"
)

TARGET = (
    "data/ui/external/ion_fut/screens/"
    "worldcup/supportnation.big"
)

OUT = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\supportnation.big"
)


def read_entries(data: bytes):
    if data[:4] != b"BIG4":
        raise RuntimeError("Geen BIG4 archive")

    count = int.from_bytes(
        data[8:12],
        "big",
    )

    pos = 16

    for index in range(count):
        offset = int.from_bytes(
            data[pos:pos + 4],
            "big",
        )
        size = int.from_bytes(
            data[pos + 4:pos + 8],
            "big",
        )
        pos += 8

        end = data.index(b"\x00", pos)

        name = data[pos:end].decode(
            "utf-8",
            "replace",
        )

        pos = end + 1

        yield index, offset, size, name


def align(value, boundary=16):
    return (
        value + boundary - 1
    ) & ~(boundary - 1)


def decode_chunkzip(payload: bytes) -> bytes:
    if not payload.startswith(b"chunkzip"):
        return payload

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

        stored_size, compression_type = struct.unpack_from(
            ">II",
            payload,
            pos,
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
                f"onbekend compression type: {compression_type}"
            )

        output.extend(decoded)

        pos = align(
            end + 8,
            alignment,
        ) - 8

    if len(output) != output_size:
        raise RuntimeError(
            f"decoded size klopt niet: "
            f"{len(output)} != {output_size}"
        )

    return bytes(output)


data = ARCHIVE.read_bytes()

for index, offset, size, name in read_entries(data):
    if name.lower() != TARGET.lower():
        continue

    stored = data[
        offset:
        offset + size
    ]

    decoded = decode_chunkzip(stored)

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_bytes(decoded)

    print(f"record : {index}")
    print(f"offset : 0x{offset:08X}")
    print(f"stored : {size}")
    print(f"decoded: {len(decoded)}")
    print(f"magic  : {decoded[:4]!r}")
    print(f"output : {OUT}")
    break
else:
    raise RuntimeError(
        f"Niet gevonden: {TARGET}"
    )