from pathlib import Path
import struct

APT = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\enterwc_inner\00_0"
)

CONST = Path(
    r"D:\Afbeeldingen\FUT14-Revival"
    r"\extracted\enterwc_inner\02_1"
)

apt = APT.read_bytes()
const = CONST.read_bytes()

constants = {}

pos = 0x20
index = 0

while pos + 8 <= len(const):
    type_id, value = struct.unpack_from(
        "<II",
        const,
        pos,
    )

    if type_id != 1:
        break

    end = const.find(b"\x00", value)

    if end != -1:
        constants[index] = const[
            value:end
        ].decode(
            "ascii",
            errors="replace",
        )

    index += 1
    pos += 8


START = 0x4A0
END = 0x548

print(
    f"[INFO] region "
    f"0x{START:X}..0x{END:X}"
)
print()

i = START

while i < END:
    op = apt[i]

    if op in (0xAF, 0xB2) and i + 1 < END:
        idx = apt[i + 1]
        text = constants.get(
            idx,
            "<unknown>",
        )

        print(
            f"0x{i:04X}: "
            f"{op:02X} {idx:02X}  "
            f"const 0x{idx:02X} = "
            f"{text}"
        )

        i += 2
        continue

    i += 1