from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\main_inner\02_1"
)

TARGETS = {
    "FIFA_HOME",
    "MAINHUB_FUT_DP",
    "USER_MSG_FUT_HUB",
    "USER_MSG_FUT_WC_HUB",
    "USER_MSG_FUT_FIFA_HUB",
    "ACTION_WORLDCUP_BUYNOW",
}

data = SRC.read_bytes()

# Uit de header/dump:
# constant records beginnen op 0x20
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


found = {}

index = 0
pos = TABLE_START

while pos + 8 <= len(data):
    type_id, offset = struct.unpack_from("<II", data, pos)

    # De tabel die we zagen bestaat uit type=1 string records.
    # Stop zodra de structuur niet meer plausibel is.
    if type_id != 1:
        break

    text = read_cstr(offset)

    if text in TARGETS:
        found[text] = {
            "index": index,
            "record_offset": pos,
            "string_offset": offset,
        }

    index += 1
    pos += 8


print(f"[INFO] {index} type-1 records gelezen")
print()

for target in TARGETS:
    info = found.get(target)

    if info is None:
        print(f"[MISS] {target}")
        continue

    print(f"[FOUND] {target}")
    print(f"  index         = {info['index']} / 0x{info['index']:X}")
    print(f"  record offset = 0x{info['record_offset']:X}")
    print(f"  string offset = 0x{info['string_offset']:X}")
    print()