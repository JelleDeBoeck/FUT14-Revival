from pathlib import Path
import struct
import zlib


ARCHIVE = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\data1.big"
)

TARGET = (
    "data/ui/nav/fut/futenterwcflow.nav"
)

OUT = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\futenterwcflow.nav"
)


def read_big4_entries(data: bytes):
    if data[:4] != b"BIG4":
        raise RuntimeError(
            "Archive is geen BIG4"
        )

    count = int.from_bytes(
        data[8:12],
        "big",
    )

    pos = 16
    entries = []

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

        end = data.index(
            b"\x00",
            pos,
        )

        name = (
            data[pos:end]
            .decode(
                "utf-8",
                "replace",
            )
        )

        pos = end + 1

        entries.append(
            (
                index,
                offset,
                size,
                name,
            )
        )

    return entries


def decode_chunkzip(blob: bytes) -> bytes:
    if len(blob) < 48:
        return blob

    # FIFA chunkzip header gevolgd
    # door raw-deflate payload.
    try:
        return zlib.decompress(
            blob[48:],
            -15,
        )
    except zlib.error:
        return blob


data = ARCHIVE.read_bytes()

entries = read_big4_entries(data)

target = None

for entry in entries:
    index, offset, size, name = entry

    if name.lower() == TARGET.lower():
        target = entry
        break

if target is None:
    raise RuntimeError(
        f"Niet gevonden: {TARGET}"
    )

index, offset, size, name = target

blob = data[
    offset:
    offset + size
]

decoded = decode_chunkzip(blob)

OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUT.write_bytes(decoded)

print(
    f"record : {index}"
)

print(
    f"offset : 0x{offset:08X}"
)

print(
    f"size   : {size}"
)

print(
    f"name   : {name}"
)

print(
    f"output : {OUT}"
)

print(
    f"bytes  : {len(decoded)}"
)