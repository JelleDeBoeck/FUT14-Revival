from pathlib import Path
import zlib

ROOT = Path(r"C:\Program Files\EA Games\FIFA 14\Game")

ARCHIVES = [
    ROOT / "data1.big",
    ROOT / "patch.big",
]

NEEDLES = [
    b"FUT_WORLD_CUP_0",
    b"WorldCupDefault",
    b"GOTO_WORLD_CUP",
    b"FLUX_PANEL_DP",
]


def read_cstr(data, pos):
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8", errors="replace"), end + 1


def try_decode(blob: bytes) -> bytes:
    if blob.startswith(b"chunkzip") and len(blob) > 48:
        try:
            return zlib.decompress(blob[48:], -15)
        except Exception:
            pass
    return blob


for archive in ARCHIVES:
    print()
    print("=" * 80)
    print(archive.name)
    print("=" * 80)

    data = archive.read_bytes()

    if data[:4] != b"BIG4":
        print("[SKIP] geen BIG4")
        continue

    count = int.from_bytes(data[8:12], "big")
    pos = 16

    hits = []

    for i in range(count):
        offset = int.from_bytes(data[pos:pos+4], "big")
        size = int.from_bytes(data[pos+4:pos+8], "big")
        pos += 8

        name, pos = read_cstr(data, pos)

        blob = data[offset:offset+size]
        decoded = try_decode(blob)

        found = []

        for needle in NEEDLES:
            if needle.lower() in decoded.lower():
                found.append(needle.decode())

        if found:
            hits.append((name, offset, size, found))

    for name, offset, size, found in hits:
        print()
        print(name)
        print(f"  offset : 0x{offset:X}")
        print(f"  size   : {size}")
        print(f"  hits   : {', '.join(found)}")

    print()
    print(f"[DONE] {len(hits)} bestanden met hits")