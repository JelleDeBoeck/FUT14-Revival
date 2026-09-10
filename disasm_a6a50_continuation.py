from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

data = Path("CardsDLLzf_analysis.dll").read_bytes()

BASE = 0x10000000
START_RVA = 0xA6B38
END_RVA   = 0xA6C60

raw = 0x400 + (START_RVA - 0x1000)
code = data[raw:raw + (END_RVA - START_RVA)]

md = Cs(CS_ARCH_X86, CS_MODE_32)

print("===== A6A50 continuation / callback dispatch =====")

for ins in md.disasm(code, BASE + START_RVA):
    marker = ""

    if ins.address in (
        BASE + 0xA6B79,
        BASE + 0xA6B92,
        BASE + 0xA6BC1,
    ):
        marker = "    <<< TARGET"

    print(
        f"{ins.address:08X}  "
        f"{ins.mnemonic:<8} {ins.op_str}"
        f"{marker}"
    )
