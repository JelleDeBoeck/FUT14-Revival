from pathlib import Path
import re


PATCH = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\patch.big"
)

TARGETS = (
    b"GotoWorldCup",
    b"GotoWorldCup_GotoStore",
    b"enableWorldCupMode",
    b"WorldCup",
    b"WORLD_CUP",
    b"FUT_WC",
    b"EnterWC",
)

data = PATCH.read_bytes()

for target in TARGETS:
    print()
    print("=" * 70)
    print(target.decode("ascii"))
    print("=" * 70)

    start = 0
    found = False

    while True:
        pos = data.find(target, start)

        if pos < 0:
            break

        found = True

        lo = max(0, pos - 250)
        hi = min(
            len(data),
            pos + len(target) + 250,
        )

        chunk = data[lo:hi]

        text = "".join(
            chr(byte)
            if 32 <= byte <= 126
            else "."
            for byte in chunk
        )

        print(f"\nOFFSET: 0x{pos:X}")
        print(text)

        start = pos + len(target)

    if not found:
        print("No matches")