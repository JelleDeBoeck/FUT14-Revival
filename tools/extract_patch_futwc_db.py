from pathlib import Path
import zlib


ARCHIVE = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\patch.big"
)

TARGETS = [
    "data/db/futwc_ng_db.db",
    "data/db/futwc_ng_db-meta.xml",
]

OUT_DIR = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\futwc_db"
)


def read_entries(data: bytes):
    if data[:4] != b"BIG4":
        raise RuntimeError("Geen BIG4 archive")

    count = int.from_bytes(
        data[8:12],
        "big",
    )

    pos = 16

    for index in range(count):
        offset = int.from_bytes(
            data[pos:pos + 4],
            "big",
        )

        size = int.from_bytes(
            data[pos + 4:pos + 8],
            "big",
        )

        pos += 8

        end = data.index(b"\x00", pos)

        name = data[pos:end].decode(
            "utf-8",
            "replace",
        )

        pos = end + 1

        yield index, offset, size, name


def decode_chunkzip(blob: bytes) -> bytes:
    if not blob.startswith(b"chunkzip"):
        print("[chunkzip] bestand is niet gecomprimeerd")
        return blob

    version = int.from_bytes(
        blob[8:12],
        "big",
    )

    expected_size = int.from_bytes(
        blob[12:16],
        "big",
    )

    max_block_size = int.from_bytes(
        blob[16:20],
        "big",
    )

    block_count = int.from_bytes(
        blob[20:24],
        "big",
    )

    alignment = int.from_bytes(
        blob[24:28],
        "big",
    )

    print(
        f"[chunkzip] version={version} "
        f"expected={expected_size} "
        f"max_block={max_block_size} "
        f"blocks={block_count} "
        f"alignment={alignment}"
    )

    output = bytearray()

    # Eerste descriptor begint op 0x28.
    header_pos = 0x28

    for block_index in range(block_count):
        if header_pos + 8 > len(blob):
            raise RuntimeError(
                f"Block {block_index + 1}: "
                f"header buiten bestand op 0x{header_pos:X}"
            )

        compressed_size = int.from_bytes(
            blob[header_pos:header_pos + 4],
            "big",
        )

        marker = int.from_bytes(
            blob[header_pos + 4:header_pos + 8],
            "big",
        )

        payload_pos = header_pos + 8
        payload_end = payload_pos + compressed_size

        if payload_end > len(blob):
            raise RuntimeError(
                f"Block {block_index + 1}: "
                f"payload buiten bestand"
            )

        compressed = blob[
            payload_pos:payload_end
        ]

        try:
            decoded = zlib.decompress(
                compressed,
                -15,
            )
        except zlib.error as exc:
            raise RuntimeError(
                f"Block {block_index + 1} "
                f"@ 0x{payload_pos:X}: "
                f"{exc}"
            ) from exc

        output.extend(decoded)

        print(
            f"[chunkzip] block "
            f"{block_index + 1}/{block_count} "
            f"@ 0x{payload_pos:X}: "
            f"compressed={compressed_size} "
            f"decoded={len(decoded)} "
            f"marker={marker}"
        )

        if block_index + 1 < block_count:
            # Volgende compressed payload begint aligned.
            #
            # Er staan 8 descriptor-bytes vlak vóór die payload.
            next_payload_pos = (
                (
                    payload_end
                    + 8
                    + alignment
                    - 1
                )
                // alignment
            ) * alignment

            header_pos = next_payload_pos - 8

    print(
        f"[chunkzip] total decoded={len(output)}"
    )

    if len(output) != expected_size:
        raise RuntimeError(
            f"Decoded size fout: "
            f"{len(output)} != {expected_size}"
        )

    return bytes(output)


data = ARCHIVE.read_bytes()

found = set()

for index, offset, size, name in read_entries(data):
    normalized = name.lower()

    for target in TARGETS:
        if normalized != target.lower():
            continue

        stored = data[
            offset:
            offset + size
        ]

        decoded = decode_chunkzip(stored)

        OUT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        out = OUT_DIR / Path(target).name
        out.write_bytes(decoded)

        found.add(target.lower())

        print()
        print(f"target : {target}")
        print(f"record : {index}")
        print(f"offset : 0x{offset:08X}")
        print(f"stored : {size}")
        print(f"decoded: {len(decoded)}")
        print(f"magic  : {decoded[:16]!r}")
        print(f"output : {out}")


missing = [
    target
    for target in TARGETS
    if target.lower() not in found
]

if missing:
    print()
    print("NIET GEVONDEN:")
    for target in missing:
        print(target)