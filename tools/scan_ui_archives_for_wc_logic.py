from pathlib import Path
import struct


ARCHIVES = [
    Path(r"C:\Program Files\EA Games\FIFA 14\Game\data1.big"),
    Path(r"C:\Program Files\EA Games\FIFA 14\Game\patch.big"),
]


# Zoek alleen in BESTANDSNAMEN.
# We willen mogelijke algemene FIFA World Cup
# frontend NAV/layout-bestanden vinden.
NEEDLES = (
    "worldcup",
    "world_cup",
    "fifawc",
    "fifa_world",
    "world",
    "wc",
)


def read_big(path: Path):
    print("=" * 78)
    print(path.name)

    data = path.read_bytes()

    if data[:4] != b"BIG4":
        raise RuntimeError(
            f"{path.name}: verwacht BIG4, kreeg {data[:4]!r}"
        )

    count = struct.unpack_from(">I", data, 8)[0]
    pos = 16

    print(f"[INFO] records: {count}")
    print("=" * 78)

    hits = []

    for index in range(count):
        # BIG4 directory entry:
        # 4 bytes offset
        # 4 bytes size
        # null-terminated filename
        if pos + 8 > len(data):
            raise RuntimeError(
                f"{path.name}: directory eindigt onverwacht "
                f"bij record {index}"
            )

        offset, size = struct.unpack_from(
            ">II",
            data,
            pos,
        )
        pos += 8

        end = data.find(b"\x00", pos)

        if end == -1:
            raise RuntimeError(
                f"{path.name}: geen filename terminator "
                f"bij record {index}"
            )

        name = data[pos:end].decode(
            "utf-8",
            errors="replace",
        )
        pos = end + 1

        lower = name.lower()

        # Alleen frontend navigation/layout.
        if not lower.startswith("data/ui/nav/"):
            continue

        hits.append(
            (
                index,
                offset,
                size,
                name,
            )
        )

    print(
        f"[INFO] matching NAV/layout records: {len(hits)}"
    )
    print()

    for index, offset, size, name in hits:
        print(
            f"{index:6d}  "
            f"0x{offset:08X}  "
            f"{size:8d}  "
            f"{name}"
        )

    print()
    print(
        f"[DONE] {path.name}: {len(hits)} matching records"
    )
    print()


def main():
    for archive in ARCHIVES:
        if not archive.exists():
            print(f"[SKIP] niet gevonden: {archive}")
            continue

        read_big(archive)


if __name__ == "__main__":
    main()