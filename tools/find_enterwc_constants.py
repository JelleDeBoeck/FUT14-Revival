from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\enterwc_inner\02_1"
)

TARGETS = {
    "SetWorldCupMode",
    "LoadFUTDatabaseWC",
    "FirstTimeInitWC",
    "InitialLoginDone",
    "GotoSupportNation",
}

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


found = {}

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

    if text in TARGETS:
        found[text] = {
            "index": index,
            "record_offset": pos,
            "string_offset": offset,
        }

    index += 1
    pos += 8


print(
    f"[INFO] {index} type-1 records gelezen"
)
print()

for target in TARGETS:
    info = found.get(target)

    if info is None:
        print(f"[MISS] {target}")
        continue

    print(f"[FOUND] {target}")
    print(
        f"  index         = "
        f"{info['index']} / 0x{info['index']:X}"
    )
    print(
        f"  record offset = "
        f"0x{info['record_offset']:X}"
    )
    print(
        f"  string offset = "
        f"0x{info['string_offset']:X}"
    )
    print()