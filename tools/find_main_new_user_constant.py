from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\main_inner\02_1"
)

TARGET = "NEW_USER"
TABLE_START = 0x20

data = SRC.read_bytes()


def read_cstr(offset):
    if offset >= len(data):
        return None

    end = data.find(b"\x00", offset)

    if end == -1:
        return None

    return data[offset:end].decode(
        "ascii",
        errors="replace",
    )


index = 0
pos = TABLE_START

while pos + 8 <= len(data):
    type_id, offset = struct.unpack_from(
        "<II",
        data,
        pos,
    )

    if type_id != 1:
        break

    text = read_cstr(offset)

    if text == TARGET:
        print(f"[FOUND] {TARGET}")
        print(
            f"  index         = "
            f"{index} / 0x{index:X}"
        )
        print(
            f"  record offset = "
            f"0x{pos:X}"
        )
        print(
            f"  string offset = "
            f"0x{offset:X}"
        )
        break

    index += 1
    pos += 8
else:
    print("[MISS] NEW_USER")