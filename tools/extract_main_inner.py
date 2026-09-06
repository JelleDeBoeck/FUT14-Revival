from pathlib import Path
import struct

SRC = Path(r"D:\Afbeeldingen\FUT14-Revival\extracted\main.big")
OUT_DIR = Path(r"D:\Afbeeldingen\FUT14-Revival\extracted\main_inner")


def read_cstr(data: bytes, pos: int):
    end = data.index(b"\x00", pos)
    name = data[pos:end].decode("utf-8", errors="replace")
    return name, end + 1


data = SRC.read_bytes()

print(f"[INFO] bestand: {SRC}")
print(f"[INFO] grootte : {len(data)} bytes")
print(f"[INFO] magic   : {data[:4]!r}")

if data[:4] not in (b"BIG4", b"BIGF"):
    raise RuntimeError(f"Onbekende BIG magic: {data[:4]!r}")

count = int.from_bytes(data[8:12], "big")

print(f"[INFO] records : {count}")
print()

pos = 16
entries = []

for index in range(count):
    offset = int.from_bytes(data[pos:pos+4], "big")
    size = int.from_bytes(data[pos+4:pos+8], "big")
    pos += 8

    name, pos = read_cstr(data, pos)

    entries.append((index, offset, size, name))

OUT_DIR.mkdir(parents=True, exist_ok=True)

for index, offset, size, name in entries:
    blob = data[offset:offset+size]

    safe_name = name.replace("/", "_").replace("\\", "_")
    if not safe_name:
        safe_name = f"record_{index}"

    out = OUT_DIR / f"{index:02d}_{safe_name}"

    out.write_bytes(blob)

    print(f"[{index}]")
    print(f"  name   : {name!r}")
    print(f"  offset : 0x{offset:X}")
    print(f"  size   : {size}")
    print(f"  magic  : {blob[:16]!r}")
    print(f"  out    : {out}")
    print()

print("[OK] klaar")
print(f"[OK] output map: {OUT_DIR}")