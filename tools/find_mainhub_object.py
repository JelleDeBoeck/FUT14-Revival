from pathlib import Path
import struct

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\globalframework_inner\00_0"
)

data = SRC.read_bytes()

OBJECTS = {
    1: 0x106D0,
    2: 0x0A98,
    3: 0x0D4C,
    4: 0x1484,
    5: 0x1918,
    6: 0x1C80,
    7: 0x2038,
    8: 0x22F4,
    9: 0x2364,
    10: 0x2C78,
    11: 0x4EDC,
    12: 0x56BC,
    13: 0x5750,
    14: 0x5A18,
    15: 0x5AC0,
    16: 0x620C,
    17: 0x6BF4,
    18: 0x7534,
    19: 0x7D64,
    20: 0xC014,
    21: 0xCAC0,
    22: 0xD028,
    23: 0xDF5C,
    24: 0xE7C4,
}

TARGETS = {
    0x6D4: "HandleFriendliesDP",
    0x6D5: "HandleFIWCDP",
    0x6D8: "HandleVBDP",
    0x6DA: "MainHubDataHelper::Action()",
    0x6DB: "TileSelected",
    0x6DC: "MainHubDataHelper::TileSelected()",
    0x6DD: "actionData",
    0x6E9: "DESTINATION_EASFC_RECOMMENDATION",
    0x6EA: "DESTINATION_LAUNCH_FUT",
    0x6EB: "DESTINATION_WORLDCUP_BUYNOW",
    0x6EC: "ACTION_ADVANCE",
    0x6ED: "WorldCupBuyNow",
    0x6F9: "LaunchFUT",
    0x73E: "ACTION_WORLDCUP_BUYNOW",
    0x831: "MainHubDataHelper::_GoToUltimateTeam()",
}

for obj_id, off in OBJECTS.items():
    tag, count, table_ptr = struct.unpack_from("<III", data, off)

    if tag != 0x88:
        continue

    ids = []

    if table_ptr + count * 4 <= len(data):
        ids = list(
            struct.unpack_from(
                f"<{count}I",
                data,
                table_ptr
            )
        )

    matches = []

    for value, name in TARGETS.items():
        if value in ids:
            matches.append((value, name, ids.index(value)))

    if not matches:
        continue

    print("=" * 72)
    print(
        f"OBJECT {obj_id}"
        f"  off=0x{off:X}"
        f"  count={count}"
        f"  table=0x{table_ptr:X}"
    )

    for value, name, local_index in matches:
        print(
            f"  local[{local_index:3}] "
            f"= 0x{value:03X}  {name}"
        )

print()
print("[OK] klaar")