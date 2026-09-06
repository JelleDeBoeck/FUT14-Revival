from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")
OUT = Path(r"D:\Afbeeldingen\FUT14-Revival\extracted\wc_builder_region.txt")

IMAGE_BASE = 0x10000000

START_VA = 0x10088000
END_VA   = 0x1008C000

data = DLL.read_bytes()

e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
num_sections = struct.unpack_from("<H", data, e_lfanew + 6)[0]
opt_size = struct.unpack_from("<H", data, e_lfanew + 20)[0]
section_table = e_lfanew + 24 + opt_size

text = None

for i in range(num_sections):
    off = section_table + i * 40

    name = data[off:off+8].split(b"\0", 1)[0].decode(
        "ascii", errors="ignore"
    )

    if name == ".text":
        text = {
            "rva": struct.unpack_from("<I", data, off + 12)[0],
            "raw_size": struct.unpack_from("<I", data, off + 16)[0],
            "raw_ptr": struct.unpack_from("<I", data, off + 20)[0],
        }
        break

if text is None:
    raise RuntimeError(".text niet gevonden")

text_va = IMAGE_BASE + text["rva"]

start_raw = text["raw_ptr"] + (START_VA - text_va)
end_raw = text["raw_ptr"] + (END_VA - text_va)

code = data[start_raw:end_raw]

md = Cs(CS_ARCH_X86, CS_MODE_32)

lines = []

for insn in md.disasm(code, START_VA):
    raw = " ".join(f"{b:02X}" for b in insn.bytes)

    lines.append(
        f"file=0x{start_raw + (insn.address - START_VA):08X}  "
        f"VA=0x{insn.address:08X}  "
        f"{raw:<24} "
        f"{insn.mnemonic:<8} {insn.op_str}"
    )

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines), encoding="utf-8")

print(f"Geschreven: {OUT}")
print(f"Regels: {len(lines)}")