from pathlib import Path
import zlib

ARCHIVE = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\data1.big"
)

TARGET = "data/ui/game/fluxhelpers/mainhublibrary.big"

OUT = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\mainhublibrary.big"
)

data = ARCHIVE.read_bytes()

if data[:4] != b"BIG4":
    raise RuntimeError(f"Geen BIG4: {data[:4]!r}")

count = int.from_bytes(data[8:12], "big")
pos = 16

for i in range(count):
    offset = int.from_bytes(data[pos:pos+4], "big")
    size = int.from_bytes(data[pos+4:pos+8], "big")
    pos += 8

    end = data.index(b"\x00", pos)
    name = data[pos:end].decode("utf-8", errors="replace")
    pos = end + 1

    if name.lower() != TARGET.lower():
        continue

    print(f"[FOUND] record : {i}")
    print(f"        offset : 0x{offset:X}")
    print(f"        size   : {size}")

    blob = data[offset:offset+size]

    if blob.startswith(b"chunkzip"):
        print("[INFO] chunkzip -> decompress")
        blob = zlib.decompress(blob[48:], -15)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(blob)

    print(f"[OK] {OUT}")
    print(f"[INFO] decoded size: {len(blob)}")
    break
else:
    raise RuntimeError("mainhubcfg.xml niet gevonden")