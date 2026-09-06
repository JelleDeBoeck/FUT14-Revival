import asyncio
import ssl
from pathlib import Path

from server.blaze.protocol import (
    build_fire_response,
    build_redirector_body,
    parse_fire_header,
)


HOST = "127.0.0.1"
PORT = 44125

CERT_DIR = Path("research/certs")
CERT_FILE = CERT_DIR / "gosredirector.crt"
KEY_FILE = CERT_DIR / "gosredirector.key"


async def read_frame(reader: asyncio.StreamReader) -> bytes:
    header = await reader.readexactly(12)
    body_length = int.from_bytes(header[0:2], "big")
    body = await reader.readexactly(body_length)
    return header + body


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
):
    peer = writer.get_extra_info("peername")
    print(f"[TLS 44125] connection from {peer}")

    try:
        frame = await read_frame(reader)
        header = parse_fire_header(frame)

        print(
            f"[TLS 44125] component={header['component']} "
            f"command={header['command']} "
            f"sequence={header['sequence']}"
        )

        body = build_redirector_body(
            host="127.0.0.1",
            port=42128,
        )

        writer.write(build_fire_response(frame, body))
        await writer.drain()

        print("[TLS 44125] redirected to 127.0.0.1:42128")

    except asyncio.IncompleteReadError:
        print("[TLS 44125] client disconnected early")

    finally:
        writer.close()

        try:
            await writer.wait_closed()
        except (ConnectionResetError, OSError):
            pass


async def main():
    if not CERT_FILE.exists() or not KEY_FILE.exists():
        raise FileNotFoundError(
            "TLS certificate ontbreekt. Genereer eerst research/certs/"
        )

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    context.minimum_version = ssl.TLSVersion.TLSv1
    context.maximum_version = ssl.TLSVersion.TLSv1_2

    context.set_ciphers(
        "AES256-SHA:AES128-SHA:DES-CBC3-SHA:@SECLEVEL=0"
    )

    if hasattr(ssl, "OP_NO_TICKET"):
        context.options |= ssl.OP_NO_TICKET

    context.load_cert_chain(
        certfile=CERT_FILE,
        keyfile=KEY_FILE,
    )

    server = await asyncio.start_server(
        handle_client,
        HOST,
        PORT,
        ssl=context,
    )

    print(f"[TLS 44125] listening on {HOST}:{PORT}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())