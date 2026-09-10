from pathlib import Path

data = Path("CardsDLLzf_analysis.dll").read_bytes()
BASE = 0x10000000

sections = [
    (0x1000, 0x183200, 0x400),
    (0x185000, 0x32000, 0x183600),
    (0x1B7000, 0x1E400, 0x1B5600),
]

def off(rva):
    for va, size, raw in sections:
        if va <= rva < va + size:
            return raw + rva - va
    raise ValueError(hex(rva))

def dump(rva, size):
    b = data[off(rva):off(rva)+size]
    print(f"\n===== RVA 0x{rva:X} =====")
    for i in range(0, len(b), 16):
        x = b[i:i+16]
        print(
            f"{BASE+rva+i:08X}  "
            + " ".join(f"{v:02X}" for v in x)
        )

# Helpers die AddPlayerToSquad daadwerkelijk gebruikt.
dump(0x1A980, 0x170)

# LoadActiveSquad + omliggende wrappers.
# Zo kunnen we convertertype/index vergelijken.
dump(0x73A60, 0x120)
