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

TABLE_START = 0x20


def read_cstr(offset):
    if offset >= len(const):
        return None

    end = const.find(
        b"\x00",
        offset,
    )

    if end == -1:
        return None

    raw = const[offset:end]

    try:
        return raw.decode("ascii")
    except UnicodeDecodeError:
        return None


# constant index -> string
constants = {}

index = 0
pos = TABLE_START

while pos + 8 <= len(const):
    type_id, value = struct.unpack_from(
        "<II",
        const,
        pos,
    )

    if type_id != 1:
        break

    text = read_cstr(value)

    if text:
        constants[index] = text

    index += 1
    pos += 8


print(
    f"[INFO] APT size  : {len(apt)}"
)
print(
    f"[INFO] constants : {len(constants)}"
)
print()

interesting = {
    "SetWorldCupMode",
    "LoadFUTDatabaseWC",
    "FirstTimeInitWC",
    "InitialLoginDone",
    "GotoSupportNation",
}

hits = []

for pos in range(
    0,
    len(apt) - 3,
    4,
):
    value = struct.unpack_from(
        "<I",
        apt,
        pos,
    )[0]

    text = constants.get(value)

    if text is None:
        continue

    hits.append(
        (
            pos,
            value,
            text,
        )
    )


for pos, value, text in hits:
    marker = (
        "  <== TARGET"
        if text in interesting
        else ""
    )

    print(
        f"0x{pos:04X}  "
        f"const=0x{value:02X}  "
        f"{text}"
        f"{marker}"
    )

print()
print(
    f"[DONE] {len(hits)} "
    "candidate constant refs"
)