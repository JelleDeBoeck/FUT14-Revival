from pathlib import Path
import hashlib
import struct

GAME = Path(r"C:\Program Files\EA Games\FIFA 14\Game")

bh_path = GAME / "patch.bh"
big_path = GAME / "patch.big"

bh = bh_path.read_bytes()

if bh[:4] != b"ViV4":
    raise SystemExit("STOP: patch.bh is geen ViV4-index")

count = struct.unpack_from(">I", bh, 8)[0]
print("BH records:", count)

index = 2146

if index >= count:
    raise SystemExit(
        f"Record {index} bestaat niet; deze patch-layout wijkt af."
    )

pos = 16 + index * 20

offset, size, reserved, hash_hi, hash_lo = struct.unpack_from(
    ">IIIII", bh, pos
)

path_hash = (hash_hi << 32) | hash_lo

print("record:", index)
print("offset:", offset)
print("size:", size)
print("path hash:", f"{path_hash:016X}")

with big_path.open("rb") as f:
    f.seek(offset)
    payload = f.read(size)

print("payload bytes:", len(payload))
print("magic:", payload[:8])
print("sha256:", hashlib.sha256(payload).hexdigest())

expected = {
    "offset": 111_471_040,
    "size": 20_481,
    "hash": 0x56CC043AC27ECC11,
    "sha256": "91e6b9ab3d6a603fff2a5ed73b81c4f472933663b153748e9647cb8d48ca46b6",
}

matches = (
    offset == expected["offset"]
    and size == expected["size"]
    and path_hash == expected["hash"]
    and hashlib.sha256(payload).hexdigest() == expected["sha256"]
)

print()
print("EXACT REFERENCE MATCH:", matches)