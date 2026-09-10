from pathlib import Path

data = Path("CardsDLLzf_analysis.dll").read_bytes()

RVA_START = 0x1951E0
RVA_END   = 0x195390

# .rdata
RDATA_RVA = 0x185000
RDATA_RAW = 0x183600

raw_start = RDATA_RAW + (RVA_START - RDATA_RVA)
raw_end   = RDATA_RAW + (RVA_END   - RDATA_RVA)

p = raw_start

print("===== exact strings 0x1951E0-0x195390 =====")

while p < raw_end:
    # Skip NUL/padding/non-printable bytes.
    if not (0x20 <= data[p] <= 0x7E):
        p += 1
        continue

    start = p

    while p < raw_end and 0x20 <= data[p] <= 0x7E:
        p += 1

    # Only accept actual NUL-terminated strings.
    if p < len(data) and data[p] == 0 and p - start >= 3:
        rva = RDATA_RVA + (start - RDATA_RAW)
        text = data[start:p].decode("ascii", errors="replace")
        print(f"RVA 0x{rva:X}  {text}")

    p += 1
