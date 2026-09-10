from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

data = Path("CardsDLLzf_analysis.dll").read_bytes()

BASE = 0x10000000
START_RVA = 0x73880
END_RVA   = 0x73940

raw = 0x400 + (START_RVA - 0x1000)
code = data[raw:raw + (END_RVA - START_RVA)]

md = Cs(CS_ARCH_X86, CS_MODE_32)

print("===== GetSquads / neighboring wrappers =====")

for ins in md.disasm(code, BASE + START_RVA):
    print(
        f"{ins.address:08X}  "
        f"{ins.mnemonic:<8} {ins.op_str}"
    )
