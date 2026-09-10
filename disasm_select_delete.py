from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

data = Path("CardsDLLzf_analysis.dll").read_bytes()

BASE = 0x10000000

ranges = [
    ("SelectSquadById", 0x73940, 0x73980),
    ("DeleteSquad",     0x739D0, 0x73A10),
]

md = Cs(CS_ARCH_X86, CS_MODE_32)

for name, start, end in ranges:
    raw = 0x400 + (start - 0x1000)
    code = data[raw:raw + (end - start)]

    print(f"\n===== {name} 0x{start:X} =====")

    for ins in md.disasm(code, BASE + start):
        print(
            f"{ins.address:08X}  "
            f"{ins.mnemonic:<8} {ins.op_str}"
        )
