from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\globalframework_inner\00_0"
)

TARGETS = {
    0x6DC: "MainHubDataHelper::TileSelected()",
    0x6EA: "DESTINATION_LAUNCH_FUT",
    0x6EB: "DESTINATION_WORLDCUP_BUYNOW",
    0x6ED: "WorldCupBuyNow",
    0x6F9: "LaunchFUT",
    0x73E: "ACTION_WORLDCUP_BUYNOW",
    0x831: "MainHubDataHelper::_GoToUltimateTeam()",
}

data = SRC.read_bytes()

for value, name in TARGETS.items():
    needle = struct.pack("<I", value)

    hits = []
    pos = 0

    while True:
        pos = data.find(needle, pos)
        if pos < 0:
            break
        hits.append(pos)
        pos += 1

    print("=" * 78)
    print(f"{name}")
    print(f"ID 0x{value:X}  hits={len(hits)}")
    print("=" * 78)

    for hit in hits:
        start = max(0, hit - 32)
        end = min(len(data), hit + 36)

        print(f"\n[0x{hit:05X}]")

        for p in range(start, end, 4):
            chunk = data[p:p+4]

            if len(chunk) < 4:
                break

            dword = struct.unpack("<I", chunk)[0]
            mark = " <==" if p == hit else ""

            print(
                f"  0x{p:05X}: "
                f"{chunk.hex(' ').upper():11} "
                f"0x{dword:08X}{mark}"
            )

    print()