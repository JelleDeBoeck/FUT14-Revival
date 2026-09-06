from pathlib import Path
import re


PATCH = Path(
    r"C:\Program Files\EA Games\FIFA 14\Game\patch.big"
)

KEYWORDS = (
    "futwc",
    "worldcup",
    "defaultwc",
    "squadwc",
    "futwchub",
    "world cup",
    "enableworldcup",
    "wc_mode",
    "wcmode",
)


data = PATCH.read_bytes()

strings = re.findall(
    rb"[\x20-\x7e]{6,}",
    data,
)

matches = []

for raw in strings:
    text = raw.decode(
        "latin1",
        errors="ignore",
    )

    lower = text.lower()

    if any(
        keyword in lower
        for keyword in KEYWORDS
    ):
        matches.append(text)


print(
    f"Found {len(matches)} candidate strings"
)

for match in sorted(set(matches)):
    print(match)