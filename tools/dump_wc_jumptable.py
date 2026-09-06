from pathlib import Path

path = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")
data = path.read_bytes()

offset = 0x8A820

for i in range(6):
    pos = offset + i * 4
    value = int.from_bytes(data[pos:pos + 4], "little")
    print(f"case {i + 2}: 0x{value:08X}")