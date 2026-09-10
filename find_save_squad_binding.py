from pathlib import Path
import struct

data = Path("CardsDLLzf_analysis.dll").read_bytes()

BASE = 0x10000000
TARGET = 0x10195530
needle = struct.pack("<I", TARGET)

TEXT_RVA = 0x1000
TEXT_RAW = 0x400
TEXT_SIZE = 0x183200

hits = []

p = 0
while True:
    p = data.find(needle, p)
    if p < 0:
        break
    hits.append(p)
    p += 1

print("===== refs to SaveSquad string pointer 0x10195530 =====")
print("TOTAL =", len(hits))

for raw in hits:
    if TEXT_RAW <= raw < TEXT_RAW + TEXT_SIZE:
        rva = TEXT_RVA + (raw - TEXT_RAW)
        print(
            f"TEXT ref: RVA 0x{rva:X} / "
            f"VA 0x{BASE+rva:X} / raw 0x{raw:X}"
        )
    else:
        print(f"non-TEXT ref: raw 0x{raw:X}")

    start = max(0, raw - 0x30)
    end = min(len(data), raw + 0x30)

    # Alleen als dit in .text ligt, toon omliggende bytes als instructies.
    if TEXT_RAW <= start < TEXT_RAW + TEXT_SIZE:
        try:
            from capstone import Cs, CS_ARCH_X86, CS_MODE_32

            start_rva = TEXT_RVA + (start - TEXT_RAW)
            md = Cs(CS_ARCH_X86, CS_MODE_32)

            print("--- surrounding disassembly ---")
            for ins in md.disasm(data[start:end], BASE + start_rva):
                marker = ""
                if TARGET in [
                    op.imm
                    for op in ins.operands
                    if op.type == 2
                ] if md.detail else []:
                    marker = " <<<"
                print(
                    f"{ins.address:08X}  "
                    f"{ins.mnemonic:<8} {ins.op_str}{marker}"
                )
        except Exception:
            # De raw hit zelf is voldoende als Capstone-detail niet aan staat.
            pass

    print()
