from pathlib import Path
import struct

APT = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\globalframework_inner\00_0"
)

CONST = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\globalframework_inner\02_1"
)

START = 0xD4C
END   = 0x1484

apt = APT.read_bytes()
const = CONST.read_bytes()

TABLE_START = 0x20


def read_cstr(offset):
    if offset >= len(const):
        return None

    end = const.find(b"\x00", offset)

    if end == -1:
        return None

    raw = const[offset:end]

    try:
        return raw.decode("ascii")
    except UnicodeDecodeError:
        return None


# Bouw constant-index -> string mapping.
constants = {}

index = 0
pos = TABLE_START

while pos + 8 <= len(const):
    type_id, value = struct.unpack_from("<II", const, pos)

    if type_id != 1:
        break

    text = read_cstr(value)

    if text:
        constants[index] = text

    index += 1
    pos += 8


print(f"[INFO] record: 0x{START:X} .. 0x{END:X}")
print(f"[INFO] constants: {len(constants)}")
print()

hits = []

# Zoek alleen aligned DWORDs binnen record 3.
for pos in range(START, END - 3, 4):
    value = struct.unpack_from("<I", apt, pos)[0]

    if value not in constants:
        continue

    text = constants[value]

    # Alleen interessante/niet-triviale strings tonen.
    if len(text) < 2:
        continue

    hits.append((pos, value, text))


for pos, value, text in hits:
    print(
        f"0x{pos:05X}  "
        f"const=0x{value:03X}  "
        f"{text}"
    )

print()
print(f"[DONE] {len(hits)} candidate constant refs")