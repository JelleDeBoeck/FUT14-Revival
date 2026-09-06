from pathlib import Path
import zlib

PATCH = Path(r"C:\Program Files\EA Games\FIFA 14\Game\patch.big")
TARGET = "data/ui/nav/fut/futgamehubflow.nav"
OUT = Path(r"D:\Afbeeldingen\FUT14-Revival\extracted\futgamehubflow.nav")


def read_cstr(data, pos):
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8", errors="replace"), end + 1


data = PATCH.read_bytes()

if data[:4] != b"BIG4":
    raise RuntimeError("patch.big is geen BIG4 archive")

count = int.from_bytes(data[8:12], "big")
pos = 16

found = None

for i in range(count):
    offset = int.from_bytes(data[pos:pos+4], "big")
    size = int.from_bytes(data[pos+4:pos+8], "big")
    pos += 8

    name, pos = read_cstr(data, pos)

    if name.lower() == TARGET.lower():
        found = (offset, size, name)
        break

if not found:
    raise RuntimeError(f"Niet gevonden: {TARGET}")

offset, size, name = found
blob = data[offset:offset+size]

print("[OK] gevonden:")
print("    ", name)
print(f"     offset : 0x{offset:X}")
print(f"     size   : {size}")

if blob.startswith(b"chunkzip"):
    compressed = blob[48:]

    decoded = zlib.decompress(compressed, -15)

    print("[OK] chunkzip decoded")
    print(f"     decoded size: {len(decoded)}")

    blob = decoded

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(blob)

print()
print("[OK] opgeslagen als:")
print(OUT)