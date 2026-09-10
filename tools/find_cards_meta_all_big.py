from pathlib import Path

GAME = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game"
)

for archive in GAME.rglob("*.big"):
    try:
        data = archive.read_bytes()

        if data[:4] != b"BIG4":
            continue

        count = int.from_bytes(data[8:12], "big")
        pos = 16

        for _ in range(count):
            offset = int.from_bytes(data[pos:pos + 4], "big")
            size = int.from_bytes(data[pos + 4:pos + 8], "big")
            pos += 8

            end = data.index(b"\x00", pos)
            name = data[pos:end].decode(
                "utf-8",
                "replace",
            )
            pos = end + 1

            lower = name.lower()

            if (
                "cards_ng" in lower
                or (
                    "cards" in lower
                    and "meta" in lower
                )
            ):
                print()
                print("ARCHIVE:", archive)
                print("FILE   :", name)
                print("OFFSET :", hex(offset))
                print("SIZE   :", size)

    except Exception:
        pass