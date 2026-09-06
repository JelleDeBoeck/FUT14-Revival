from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\helperfunctions.big"
)

OUT_DIR = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\helperfunctions_inner"
)

data = SRC.read_bytes()

if data[:4] not in (b"BIG4", b"BIGF"):
    raise RuntimeError(
        f"geen BIG archive: {data[:4]!r}"
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

print(f"[INFO] magic       : {data[:4]!r}")
print(f"[INFO] entries     : {count}")
print(f"[INFO] header size : 0x{header_size:X}")
print()

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

pos = 16

for i in range(count):
    offset, size = struct.unpack_from(
        ">II",
        data,
        pos,
    )

    pos += 8

    end = data.find(
        b"\x00",
        pos,
        header_size,
    )

    if end == -1:
        raise RuntimeError(
            f"geen filename terminator bij entry {i}"
        )

    name = data[pos:end].decode(
        "ascii",
        errors="replace",
    )

    pos = end + 1

    blob = data[
        offset:
        offset + size
    ]

    out = OUT_DIR / f"{i:02d}_{name}"

    out.write_bytes(blob)

    print(
        f"[{i:02d}] "
        f"name={name!r} "
        f"offset=0x{offset:X} "
        f"size={size} / 0x{size:X}"
    )

    print(
        f"     magic={blob[:24]!r}"
    )

    print(
        f"     -> {out}"
    )

    print()