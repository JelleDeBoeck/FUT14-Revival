from pathlib import Path
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")
OUT = Path(r"D:\Afbeeldingen\FUT14-Revival\extracted\tile_vtable_scan.txt")

pe = pefile.PE(str(DLL))
image_base = pe.OPTIONAL_HEADER.ImageBase

text = next(
    s for s in pe.sections
    if s.Name.rstrip(b"\x00") == b".text"
)

text_va = image_base + text.VirtualAddress
text_raw = text.PointerToRawData
text_data = DLL.read_bytes()[text_raw:text_raw + text.SizeOfRawData]

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

lines = []
lines.append(f"DLL: {DLL}")
lines.append(f"ImageBase: 0x{image_base:08X}")
lines.append(f".text VA: 0x{text_va:08X}")
lines.append("")

instructions = list(md.disasm(text_data, text_va))

# We zoeken alle indirecte vtable-calls via offsets 0x28 en 0x38.
# Daarbij dumpen we genoeg context om te zien:
#   - waar het object vandaan komt
#   - welke argumenten gepusht worden
#   - of dezelfde concrete vtable/object-familie herkenbaar is

targets = ("+ 0x28]", "+ 0x38]", "+ 0x28", "+ 0x38")

hits = []

for i, ins in enumerate(instructions):
    op = ins.op_str.lower()

    if not any(t in op for t in targets):
        continue

    # Alleen interessante loads/calls rond vtable offsets.
    if ins.mnemonic not in ("mov", "call", "jmp"):
        continue

    hits.append(i)

lines.append(f"Hits: {len(hits)}")
lines.append("=" * 80)

for hit_no, i in enumerate(hits, 1):
    ins = instructions[i]

    lines.append("")
    lines.append(
        f"HIT {hit_no}: VA=0x{ins.address:08X} "
        f"{ins.mnemonic} {ins.op_str}"
    )
    lines.append("-" * 80)

    start = max(0, i - 18)
    end = min(len(instructions), i + 19)

    for j in range(start, end):
        x = instructions[j]

        marker = ">>" if j == i else "  "

        file_off = text_raw + (x.address - text_va)

        raw = bytes(x.bytes).hex(" ").upper()

        lines.append(
            f"{marker} file=0x{file_off:08X} "
            f"VA=0x{x.address:08X} "
            f"{raw:<24} "
            f"{x.mnemonic:<8} {x.op_str}"
        )

    lines.append("=" * 80)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines), encoding="utf-8")

print(f"Geschreven: {OUT}")
print(f"Hits: {len(hits)}")