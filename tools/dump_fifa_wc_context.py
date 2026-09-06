from pathlib import Path

EXE = Path(r"C:\Program Files\EA Games\FIFA 14\Game\fifa14.exe")

TERMS = [
    "FluxViewModel",
    "LoadFUTDatabaseWC",
    "UnLoadFUTDatabaseWC",
    "WorldCup",
    "FUTWC",
]

RADIUS = 0x500
MIN_STRING_LEN = 4


def find_all_case_insensitive(data: bytes, text: str):
    needle = text.lower().encode("ascii")
    lower_data = data.lower()

    hits = []
    pos = 0

    while True:
        pos = lower_data.find(needle, pos)

        if pos == -1:
            break

        hits.append(pos)
        pos += 1

    return hits


def extract_ascii_strings(data: bytes, start: int, end: int):
    results = []

    i = start

    while i < end:
        if 0x20 <= data[i] <= 0x7E:
            s = i

            while i < end and 0x20 <= data[i] <= 0x7E:
                i += 1

            if i - s >= MIN_STRING_LEN:
                text = data[s:i].decode("ascii", errors="replace")
                results.append((s, text))
        else:
            i += 1

    return results


data = EXE.read_bytes()

print(f"[INFO] bestand : {EXE}")
print(f"[INFO] grootte : {len(data):,} bytes")
print()

seen_regions = set()

for term in TERMS:
    hits = find_all_case_insensitive(data, term)

    print("=" * 90)
    print(term)
    print("=" * 90)

    if not hits:
        print("[NOT FOUND]")
        print()
        continue

    for hit in hits:
        print()
        print(f"[HIT] 0x{hit:X}")

        start = max(0, hit - RADIUS)
        end = min(len(data), hit + RADIUS)

        region_key = (start, end)

        if region_key in seen_regions:
            print("  [context al hierboven getoond]")
            continue

        seen_regions.add(region_key)

        strings = extract_ascii_strings(data, start, end)

        print(f"[CONTEXT] 0x{start:X} - 0x{end:X}")
        print()

        for pos, text in strings:
            marker = " <==" if pos <= hit < pos + len(text) else ""

            print(
                f"0x{pos:08X}  "
                f"{text[:160]}"
                f"{marker}"
            )

        print()

print("[DONE]")