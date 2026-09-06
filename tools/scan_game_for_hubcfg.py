from pathlib import Path

ROOT = Path(r"C:\Program Files\EA Games\FIFA 14\Game")

NEEDLES = [
    b"futfluxhubcfg",
    b"futfluxhubcfg.xml",
    b"futfluxhubwccfg",
    b"futfluxhubwccfg.xml",
]

EXTENSIONS = {
    ".exe",
    ".dll",
    ".big",
    ".xml",
    ".nav",
    ".ini",
    ".cfg",
}


def find_all_case_insensitive(data: bytes, needle: bytes):
    data_lower = data.lower()
    needle_lower = needle.lower()

    hits = []
    pos = 0

    while True:
        pos = data_lower.find(needle_lower, pos)

        if pos == -1:
            break

        hits.append(pos)
        pos += 1

    return hits


print(f"[INFO] root: {ROOT}")
print()

total_hits = 0

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue

    if path.suffix.lower() not in EXTENSIONS:
        continue

    try:
        data = path.read_bytes()
    except Exception as exc:
        print(f"[SKIP] {path}: {exc}")
        continue

    file_hits = []

    for needle in NEEDLES:
        hits = find_all_case_insensitive(data, needle)

        for offset in hits:
            file_hits.append(
                (needle.decode("ascii"), offset)
            )

    if not file_hits:
        continue

    print("=" * 80)
    print(path)

    for needle, offset in file_hits:
        print(
            f"  {needle:<24} "
            f"offset=0x{offset:X}"
        )

        total_hits += 1

    print()

print("=" * 80)
print(f"[DONE] totaal aantal hits: {total_hits}")