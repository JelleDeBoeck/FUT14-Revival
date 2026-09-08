from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\supportnation_inner\21_1"
)

data = SRC.read_bytes()

TABLE_START = 0x20


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

    print(f"[{index:3}] {text!r}")

    index += 1
    pos += 8