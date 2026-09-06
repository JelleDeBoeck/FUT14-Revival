from pathlib import Path

EXE = Path(r"C:\Program Files\EA Games\FIFA 14\Game\fifa14.exe")

TERMS = [
    "futgamehubviewmodel",
    "FUTGameHubViewModel",
    "GameHubViewModel",
    "gamehubviewmodel",

    "FluxViewModel",
    "fluxviewmodel",

    "LoadFUTDatabaseWC",
    "UnloadFUTDatabaseWC",
    "UnLoadFUTDatabaseWC",
    "SetWorldCupMode",
    "FirstTimeInitWC",

    "WorldCupMode",
    "WorldCup",
    "FUTWC",
    "FUT_WC",

    "GameHubWC",
    "EnterWC",
    "SupportNation",
]


data = EXE.read_bytes()

print(f"[INFO] bestand: {EXE}")
print(f"[INFO] grootte : {len(data):,} bytes")
print()


def find_all(haystack: bytes, needle: bytes):
    results = []
    start = 0

    while True:
        pos = haystack.find(needle, start)

        if pos == -1:
            break

        results.append(pos)
        start = pos + 1

    return results


for term in TERMS:
    ascii_needles = {
        term.encode("ascii", errors="ignore"),
        term.lower().encode("ascii", errors="ignore"),
        term.upper().encode("ascii", errors="ignore"),
    }

    utf16_needles = {
        term.encode("utf-16le"),
        term.lower().encode("utf-16le"),
        term.upper().encode("utf-16le"),
    }

    ascii_hits = set()
    utf16_hits = set()

    for needle in ascii_needles:
        if needle:
            ascii_hits.update(find_all(data, needle))

    for needle in utf16_needles:
        if needle:
            utf16_hits.update(find_all(data, needle))

    print("=" * 78)
    print(term)

    if ascii_hits:
        print("  ASCII:")
        for pos in sorted(ascii_hits)[:30]:
            print(f"    0x{pos:X}")

        if len(ascii_hits) > 30:
            print(f"    ... plus {len(ascii_hits) - 30} meer")
    else:
        print("  ASCII : [NOT FOUND]")

    if utf16_hits:
        print("  UTF16:")
        for pos in sorted(utf16_hits)[:30]:
            print(f"    0x{pos:X}")

        if len(utf16_hits) > 30:
            print(f"    ... plus {len(utf16_hits) - 30} meer")
    else:
        print("  UTF16 : [NOT FOUND]")

print()
print("[DONE]")