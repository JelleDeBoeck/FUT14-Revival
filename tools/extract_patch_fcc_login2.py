from pathlib import Path
import zlib


ARCHIVE = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\patch.big"
)

TARGET = (
    "data/ui/external/ion_fut/screens/"
    "fcc_login2.big"
)

OUT = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\fcc_login2.big"
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


def decode_chunkzip(blob: bytes) -> bytes:
    # FIFA 14 gebruikt voor deze resources
    # dezelfde eenvoudige chunkzip-vorm.
    if len(blob) >= 48:
        try:
            return zlib.decompress(
                blob[48:],
                -15,
            )
        except zlib.error:
            pass

    return blob


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