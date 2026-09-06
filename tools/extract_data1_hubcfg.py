from pathlib import Path
import zlib

ARCHIVE = Path(r"C:\Program Files\EA Games\FIFA 14\Game\data1.big")
TARGET = "data/ui/layout/fut/futfluxhubcfg.xml"
OUT = Path(r"D:\Afbeeldingen\FUT14-Revival\extracted\data1_futfluxhubcfg.xml")


def read_cstr(data, pos):
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8", errors="replace"), end + 1


data = ARCHIVE.read_bytes()

if data[:4] != b"BIG4":
    raise RuntimeError("data1.big is geen BIG4 archive")

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
    blob = zlib.decompress(blob[48:], -15)
    print("[OK] chunkzip decoded")
    print(f"     decoded size: {len(blob)}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(blob)

print()
print("[OK] opgeslagen:")
print(OUT)