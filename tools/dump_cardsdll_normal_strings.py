from pathlib import Path
import struct

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")

START = 0x87810
END   = 0x88010


def u16(data, off):
    return struct.unpack_from("<H", data, off)[0]


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


data = DLL.read_bytes()

pe = u32(data, 0x3C)
coff = pe + 4
num_sections = u16(data, coff + 2)
opt_size = u16(data, coff + 16)
opt = coff + 20

image_base = u32(data, opt + 28)
section_table = opt + opt_size

sections = []

for i in range(num_sections):
    o = section_table + i * 40

    name = data[o:o+8].split(b"\0", 1)[0].decode(
        "ascii", errors="replace"
    )

    sections.append({
        "name": name,
        "rva": u32(data, o + 12),
        "raw_size": u32(data, o + 16),
        "raw_ptr": u32(data, o + 20),
    })


def va_to_file(va):
    rva = va - image_base

    for s in sections:
        start = s["rva"]
        end = start + s["raw_size"]

        if start <= rva < end:
            return s["raw_ptr"] + (rva - start)

    return None


def read_ascii(off, max_len=300):
    if off is None or not (0 <= off < len(data)):
        return None

    out = bytearray()

    for i in range(max_len):
        if off + i >= len(data):
            break

        b = data[off + i]

        if b == 0:
            break

        if b < 0x20 or b > 0x7E:
            return None

        out.append(b)

    if len(out) < 3:
        return None

    return out.decode("ascii")


seen = set()

print(f"[INFO] scanning file 0x{START:X} - 0x{END:X}")
print()

for pos in range(START, END - 4):

    # x86 PUSH imm32 = 68 xx xx xx xx
    if data[pos] != 0x68:
        continue

    va = u32(data, pos + 1)

    if not (image_base <= va < image_base + 0x02000000):
        continue

    file_off = va_to_file(va)
    text = read_ascii(file_off)

    if not text:
        continue

    key = (va, text)

    if key in seen:
        continue

    seen.add(key)

    print(
        f"instruction file=0x{pos:08X}  "
        f"VA=0x{va:08X}  "
        f"file=0x{file_off:08X}  "
        f"{text!r}"
    )

print()
print("[DONE]")