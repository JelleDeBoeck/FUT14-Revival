from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\helperfunctions_inner\02_1"
)

TARGETS = (
    "WorldCup",
    "WorldCupMode",
    "gFutHelpers",
)

data = SRC.read_bytes()

if not data.startswith(b"Apt constant file"):
    raise RuntimeError(
        f"Onverwachte constant file: {data[:32]!r}"
    )

TABLE_START = 0x20


def read_cstr(offset):
    if offset >= len(data):
        return None

    end = data.find(
        b"\x00",
        offset,
    )

    if end == -1:
        return None

    return data[offset:end].decode(
        "ascii",
        errors="replace",
    )


print(f"[INFO] size: {len(data)} / 0x{len(data):X}")
print(f"[INFO] table start: 0x{TABLE_START:X}")
print()

hits = []

index = 0

while True:
    pos = TABLE_START + index * 8

    if pos + 8 > len(data):
        break

    type_id, value = struct.unpack_from(
        "<II",
        data,
        pos,
    )

    if type_id == 1:
        text = read_cstr(value)

        if text and any(
            target.lower() in text.lower()
            for target in TARGETS
        ):
            hits.append(
                (
                    index,
                    value,
                    text,
                )
            )

    index += 1


print(f"[HITS] {len(hits)}")
print()

for index, offset, text in hits:
    print(
        f"index={index:5d} "
        f"/ 0x{index:04X}  "
        f"off=0x{offset:05X}  "
        f"{text!r}"
    )

    print("  context:")

    start = max(
        0,
        index - 8,
    )

    end = index + 8

    for i in range(start, end + 1):
        pos = TABLE_START + i * 8

        if pos + 8 > len(data):
            break

        type_id, value = struct.unpack_from(
            "<II",
            data,
            pos,
        )

        marker = ">>" if i == index else "  "

        if type_id == 1:
            value_text = read_cstr(value)

            print(
                f"{marker} "
                f"0x{i:04X} "
                f"type=1 "
                f"off=0x{value:05X} "
                f"{value_text!r}"
            )

        else:
            print(
                f"{marker} "
                f"0x{i:04X} "
                f"type={type_id} "
                f"value=0x{value:08X}"
            )

    print()


print("[DONE] Niets gewijzigd.")