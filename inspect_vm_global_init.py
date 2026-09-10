from pathlib import Path

data = Path("CardsDLLzf_analysis.dll").read_bytes()
BASE = 0x10000000

# .text:
# RVA 0x1000 -> raw 0x400
def off(rva):
    return 0x400 + (rva - 0x1000)

def dump(rva, size):
    b = data[off(rva):off(rva)+size]

    print(f"===== RVA 0x{rva:X} =====")

    for i in range(0, len(b), 16):
        x = b[i:i+16]
        print(
            f"{BASE+rva+i:08X}  "
            + " ".join(f"{v:02X}" for v in x)
        )

# Bevat getter/setter van 101D5390 én alle typed argument helpers.
dump(0x1A9A0, 0x180)
