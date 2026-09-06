from pathlib import Path

PATCH = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\data1.big"
)

NEEDLES = (
    "mainhub",
    "main_hub",
    "fifahub",
    "fifa_hub",
    "fifahome",
    "fifa_home",
    "homescreen",
    "mainmenu",
)

data = PATCH.read_bytes()

if data[:4] != b"BIG4":
    raise RuntimeError(
        f"Onverwachte magic: {data[:4]!r}"
    )

count = int.from_bytes(data[8:12], "big")
pos = 16

hits = []

for i in range(count):
    offset = int.from_bytes(
        data[pos:pos + 4], "big"
    )
    size = int.from_bytes(
        data[pos + 4:pos + 8], "big"
    )
    pos += 8

    end = data.index(b"\x00", pos)
    name = data[pos:end].decode(
        "utf-8",
        errors="replace",
    )
    pos = end + 1

    lower = name.lower()

    if any(x in lower for x in NEEDLES):
        hits.append(
            (i, offset, size, name)
        )

print(f"[INFO] records: {count}")
print(f"[INFO] hits   : {len(hits)}")
print()

for i, offset, size, name in hits:
    print(
        f"{i:6}  "
        f"0x{offset:08X}  "
        f"{size:8}  "
        f"{name}"
    )