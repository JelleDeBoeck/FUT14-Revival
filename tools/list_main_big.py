from pathlib import Path

BIG = Path(r"D:\Afbeeldingen\FUT14-Revival\extracted\main.big")

data = BIG.read_bytes()

print("Magic:", data[:4])
print("Size :", len(data))

if data[:4] not in (b"BIG4", b"BIGF"):
    raise RuntimeError(f"Onbekend BIG-formaat: {data[:4]!r}")

count = int.from_bytes(data[8:12], "big")
print("Files:", count)
print()

pos = 16

for i in range(count):
    offset = int.from_bytes(data[pos:pos+4], "big")
    size = int.from_bytes(data[pos+4:pos+8], "big")
    pos += 8

    end = data.index(b"\x00", pos)
    name = data[pos:end].decode("utf-8", errors="replace")
    pos = end + 1

    print(f"{i:4}  off=0x{offset:08X}  size={size:8}  {name}")