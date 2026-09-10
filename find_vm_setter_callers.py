from pathlib import Path
import struct

data = Path("CardsDLLzf_analysis.dll").read_bytes()

BASE = 0x10000000
TARGET = 0x1001A9D0

TEXT_RVA = 0x1000
TEXT_RAW = 0x400
TEXT_SIZE = 0x183200

hits = []

for raw in range(TEXT_RAW, TEXT_RAW + TEXT_SIZE - 5):
    if data[raw] != 0xE8:
        continue

    rel = struct.unpack_from("<i", data, raw + 1)[0]

    rva = TEXT_RVA + (raw - TEXT_RAW)
    call_va = BASE + rva
    dest = call_va + 5 + rel

    if dest == TARGET:
        hits.append((raw, rva))

print("===== direct calls to 0x1001A9D0 =====")

for raw, rva in hits:
    print(
        f"CALL at RVA 0x{rva:X} "
        f"/ VA 0x{BASE+rva:X} "
        f"/ file offset 0x{raw:X}"
    )

print(f"\nTOTAL = {len(hits)}")

print("\n===== surrounding bytes =====")

for raw, rva in hits:
    start_raw = max(TEXT_RAW, raw - 0x40)
    end_raw = min(TEXT_RAW + TEXT_SIZE, raw + 0x50)

    blob = data[start_raw:end_raw]

    start_rva = TEXT_RVA + (start_raw - TEXT_RAW)

    print(f"\n--- around CALL RVA 0x{rva:X} ---")

    for i in range(0, len(blob), 16):
        b = blob[i:i+16]
        print(
            f"{BASE+start_rva+i:08X}  "
            + " ".join(f"{x:02X}" for x in b)
        )
