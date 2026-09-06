from pathlib import Path
import struct

APT = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted"
    r"\helperfunctions_inner\00_0"
)

CONST = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted"
    r"\helperfunctions_inner\02_1"
)

TARGET = b"gFutHelpersGetWorldCupMode"

apt = APT.read_bytes()
const = CONST.read_bytes()

print(f"[INFO] APT   : {len(apt)} / 0x{len(apt):X}")
print(f"[INFO] CONST : {len(const)} / 0x{len(const):X}")
print()


# -------------------------------------------------
# 1. Vind de string fysiek in de constant file
# -------------------------------------------------

positions = []

start = 0

while True:
    pos = const.find(TARGET, start)

    if pos == -1:
        break

    positions.append(pos)
    start = pos + 1


if not positions:
    raise SystemExit(
        f"[STOP] {TARGET.decode()} niet gevonden"
    )


print("[STRING HITS]")

for pos in positions:
    print(
        f"  CONST+0x{pos:X} "
        f"({pos})"
    )

print()


# -------------------------------------------------
# 2. Zoek DWORD pointers naar die string-offsets
#
# APT constant files gebruiken tabellen met offsets.
# We tonen zowel little- als big-endian matches,
# zodat we hier niets gokken.
# -------------------------------------------------

for string_pos in positions:
    print(
        f"[POINTERS -> CONST+0x{string_pos:X}]"
    )

    le = struct.pack(
        "<I",
        string_pos,
    )

    be = struct.pack(
        ">I",
        string_pos,
    )

    found = False

    for encoding, needle in (
        ("LE", le),
        ("BE", be),
    ):
        search = 0

        while True:
            hit = const.find(
                needle,
                search,
            )

            if hit == -1:
                break

            found = True

            print(
                f"  {encoding} pointer "
                f"@ CONST+0x{hit:X}"
            )

            search = hit + 1

    if not found:
        print(
            "  geen directe DWORD pointer gevonden"
        )

    print()


# -------------------------------------------------
# 3. Toon context rond fysieke string
# -------------------------------------------------

print("[STRING CONTEXT]")

for pos in positions:
    lo = max(
        0,
        pos - 160,
    )

    hi = min(
        len(const),
        pos + len(TARGET) + 160,
    )

    raw = const[lo:hi]

    printable = "".join(
        chr(b)
        if 0x20 <= b < 0x7F
        else "."
        for b in raw
    )

    print(
        f"\nCONST 0x{lo:X}..0x{hi:X}"
    )

    print(printable)


# -------------------------------------------------
# 4. Voorlopig géén APT patch/xref-gok.
#
# Eerst bepalen we uit de pointer-table welk
# constant-index bij TARGET hoort.
# -------------------------------------------------

print()
print(
    "[DONE] Niets gewijzigd."
)