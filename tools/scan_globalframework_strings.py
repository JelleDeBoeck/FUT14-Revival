from pathlib import Path
import re

src = Path(
    r"D:\Afbeeldingen\FUT14-Revival\extracted\globalframework.big"
)

data = src.read_bytes()

terms = (
    b"world",
    b"cup",
    b"fut",
    b"hub",
    b"buynow",
    b"action",
    b"main",
    b"dlc",
)

for m in re.finditer(rb"[\x20-\x7e]{4,}", data):
    raw = m.group()

    if any(term in raw.lower() for term in terms):
        print(
            f"0x{m.start():05X}  "
            f"{raw.decode('ascii', errors='replace')}"
        )