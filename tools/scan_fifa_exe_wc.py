from pathlib import Path

EXE = Path(r"C:\Program Files\EA Games\FIFA 14\Game\fifa14.exe")

NEEDLES = [
    b"futgamehubviewmodel",
    b"FluxViewModel",
    b"FLUX_PANEL_DP",
    b"MAINHUB_FUT_DP",
    b"USER_MSG_FUT_HUB",
    b"USER_MSG_FUT_WC_HUB",
    b"GOTO_WORLD_CUP",
    b"WorldCupDefault",
    b"FUT_WORLD_CUP_0",
    b"enableWorldCupMode",
    b"SetWorldCupMode",
    b"LoadFUTDatabaseWC",
]

data = EXE.read_bytes()

print(f"[INFO] {EXE}")
print(f"[INFO] size: {len(data):,} bytes")
print()

for needle in NEEDLES:
    print("=" * 70)
    print(needle.decode("ascii"))

    found = []
    start = 0

    while True:
        pos = data.lower().find(needle.lower(), start)

        if pos == -1:
            break

        found.append(pos)
        start = pos + 1

    if not found:
        print("  [NOT FOUND]")
        continue

    for pos in found[:20]:
        print(f"  offset: 0x{pos:X}")

    if len(found) > 20:
        print(f"  ... plus {len(found) - 20} meer")

    print(f"  total: {len(found)}")

print()
print("[DONE]")