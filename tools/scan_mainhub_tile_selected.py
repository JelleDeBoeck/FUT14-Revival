from pathlib import Path

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\globalframework_inner\00_0"
)

data = SRC.read_bytes()

START = 0x7D64
END   = 0xC014

targets = {
    136: "TileSelected",
    137: "MainHubDataHelper::TileSelected()",
    138: "actionData",
    150: "DESTINATION_EASFC_RECOMMENDATION",
    151: "DESTINATION_LAUNCH_FUT",
    152: "DESTINATION_WORLDCUP_BUYNOW",
    153: "ACTION_ADVANCE",
    154: "WorldCupBuyNow",
    166: "LaunchFUT",
    235: "ACTION_WORLDCUP_BUYNOW",
}

# Tot nu toe zien we deze prefixes bij local refs.
PREFIXES = {
    0xAF: "AF",
    0xA2: "A2",
    0xAE: "AE",
    0xB2: "B2",
}

for local_idx, name in targets.items():

    # Eerst alleen indices die in één byte passen.
    if local_idx > 0xFF:
        continue

    found = []

    for pos in range(START, END - 1):
        prefix = data[pos]
        operand = data[pos + 1]

        if prefix in PREFIXES and operand == local_idx:
            found.append((pos, prefix))

    print("=" * 72)
    print(
        f"local[{local_idx}] = {name} "
        f"(0x{local_idx:02X})"
    )

    if not found:
        print("  geen 2-byte refs gevonden")
        continue

    for pos, prefix in found:
        lo = max(START, pos - 24)
        hi = min(END, pos + 26)

        chunk = data[lo:hi]

        print(
            f"\n  hit @ 0x{pos:05X} "
            f"opcode={PREFIXES[prefix]}"
        )

        for row in range(0, len(chunk), 16):
            addr = lo + row
            part = chunk[row:row+16]
            print(
                f"    {addr:05X}: "
                + " ".join(f"{b:02X}" for b in part)
            )

print("\n[DONE]")