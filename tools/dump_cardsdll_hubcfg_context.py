from pathlib import Path

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")

TARGETS = [
    b"futfluxhubwccfg.xml",
    b"futfluxhubcfg.xml",
]

RADIUS = 0x1000
MIN_STRING_LEN = 4


def find_all(data: bytes, needle: bytes):
    hits = []
    start = 0

    while True:
        pos = data.lower().find(needle.lower(), start)

        if pos == -1:
            break

        hits.append(pos)
        start = pos + 1

    return hits


def extract_ascii_strings(data: bytes, start: int, end: int):
    results = []
    pos = start

    while pos < end:
        if 0x20 <= data[pos] <= 0x7E:
            string_start = pos

            while pos < end and 0x20 <= data[pos] <= 0x7E:
                pos += 1

            if pos - string_start >= MIN_STRING_LEN:
                text = data[string_start:pos].decode(
                    "ascii",
                    errors="replace",
                )

                results.append((string_start, text))
        else:
            pos += 1

    return results


data = DLL.read_bytes()

print(f"[INFO] bestand : {DLL}")
print(f"[INFO] grootte : {len(data):,} bytes")
print()


for target in TARGETS:
    hits = find_all(data, target)

    print("=" * 90)
    print(target.decode("ascii"))
    print("=" * 90)

    if not hits:
        print("[NOT FOUND]")
        print()
        continue

    for hit in hits:
        start = max(0, hit - RADIUS)
        end = min(len(data), hit + len(target) + RADIUS)

        print()
        print(f"[HIT]     0x{hit:X}")
        print(f"[CONTEXT] 0x{start:X} - 0x{end:X}")
        print()

        strings = extract_ascii_strings(data, start, end)

        for offset, text in strings:
            marker = ""

            if offset <= hit < offset + len(text):
                marker = "  <== TARGET"

            print(
                f"0x{offset:08X}  "
                f"{text[:200]}"
                f"{marker}"
            )

        print()

print("[DONE]")