from pathlib import Path
import shutil

SRC = Path(
    r"D:\Afbeeldingen\FUT14-Revival\server\fut_app.py"
)

BACKUP = SRC.with_name(
    "fut_app.py.pre-wc-state-auto.bak"
)

text = SRC.read_text(
    encoding="utf-8"
)

shutil.copy2(
    SRC,
    BACKUP,
)

print(f"[OK] backup: {BACKUP}")
print(f"[INFO] fut_app.py chars: {len(text)}")
print("[INFO] Nog niets gewijzigd.")