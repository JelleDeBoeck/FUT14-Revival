from pathlib import Path

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")

data = DLL.read_bytes()

targets = {
    "0x0ED84B11": (0x0ED84B11).to_bytes(4, "little"),
    "0x0ED84B12": (0x0ED84B12).to_bytes(4, "little"),
}

print(f"DLL: {DLL}")
print(f"Size: {len(data):,} bytes")
print()

for name, needle in targets.items():
    print("=" * 60)
    print(name)
    print("=" * 60)

    hits = []
    start = 0

    while True:
        pos = data.find(needle, start)

        if pos == -1:
            break

        hits.append(pos)
        start = pos + 1

    print(f"Hits: {len(hits)}")

    for pos in hits:
        print(f"  file offset: 0x{pos:08X}")

    print()