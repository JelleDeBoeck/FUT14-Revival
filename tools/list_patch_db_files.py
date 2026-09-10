from pathlib import Path

ARCHIVE = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\patch.big"
)

data = ARCHIVE.read_bytes()

if data[:4] != b"BIG4":
    raise RuntimeError("Geen BIG4 archive")

count = int.from_bytes(data[8:12], "big")
pos = 16

for _ in range(count):
    offset = int.from_bytes(data[pos:pos + 4], "big")
    size = int.from_bytes(data[pos + 4:pos + 8], "big")
    pos += 8

    end = data.index(b"\x00", pos)
    name = data[pos:end].decode("utf-8", "replace")
    pos = end + 1

    lower = name.lower()

    if "data/db/" in lower and (
        "cards" in lower or
        "meta" in lower
    ):
        print(name)