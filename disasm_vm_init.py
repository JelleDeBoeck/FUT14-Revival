from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    print("Capstone ontbreekt.")
    print("Installeer met:")
    print(r'.\.venv\Scripts\python.exe -m pip install capstone')
    raise SystemExit

data = Path("CardsDLLzf_analysis.dll").read_bytes()

BASE = 0x10000000
START_RVA = 0x32C0
END_RVA   = 0x33F0

# .text: RVA 0x1000 -> raw 0x400
raw = 0x400 + (START_RVA - 0x1000)
code = data[raw:raw + (END_RVA - START_RVA)]

md = Cs(CS_ARCH_X86, CS_MODE_32)

print(
    f"===== disasm RVA 0x{START_RVA:X}-0x{END_RVA:X} ====="
)

for ins in md.disasm(code, BASE + START_RVA):
    marker = ""

    if ins.address == BASE + 0x339A:
        marker = "    <<< SET VM GLOBAL"

    print(
        f"{ins.address:08X}  "
        f"{ins.mnemonic:<8} {ins.op_str}"
        f"{marker}"
    )
