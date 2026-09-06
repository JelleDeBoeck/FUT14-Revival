from pathlib import Path


SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\fcc_login2.big"
)

OUT_DIR = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\fcc_login2_inner"
)


def read_entries(data: bytes):
    if data[:4] != b"BIGF":
        raise RuntimeError(
            f"Geen BIGF archive: {data[:4]!r}"
        )

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


data = SRC.read_bytes()

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

print(f"source : {SRC}")
print(f"size   : {len(data)}")
print(f"magic  : {data[:4]!r}")
print()

for index, offset, size, name in read_entries(data):
    print(
        f"[{index}] "
        f"name={name!r} "
        f"offset=0x{offset:X} "
        f"size={size}"
    )

    if size == 0:
        print("    EMPTY")
        continue

    blob = data[
        offset:
        offset + size
    ]

    safe_name = name.replace(
        "/",
        "_",
    ).replace(
        "\\",
        "_",
    )

    out = OUT_DIR / (
        f"{index:02d}_{safe_name}"
    )

    out.write_bytes(blob)

    print(
        f"    first32={blob[:32].hex(' ')}"
    )
    print(
        f"    ascii32={blob[:32]!r}"
    )
    print(
        f"    output={out}"
    )

print()
print("KLAAR")