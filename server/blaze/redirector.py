import asyncio

from server.blaze.protocol import (
    build_fire_response,
    build_redirector_body,
    parse_fire_header,
)


HOST = "127.0.0.1"
PORT = 42127


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
    print(f"[REDIRECTOR] connection from {peer}")

    try:
        while True:
            try:
                frame = await read_frame(reader)
            except asyncio.IncompleteReadError:
                break

            header = parse_fire_header(frame)

            print(
                "[REDIRECTOR] "
                f"component={header['component']} "
                f"command={header['command']} "
                f"sequence={header['sequence']} "
                f"body={header['length']} bytes"
            )

            body = build_redirector_body(
                host="127.0.0.1",
                port=42128,
            )

            response = build_fire_response(frame, body)

            writer.write(response)
            await writer.drain()

            print(
                f"[REDIRECTOR] redirected client to 127.0.0.1:42128"
            )

    finally:
        print(f"[REDIRECTOR] disconnected: {peer}")
        writer.close()
        await writer.wait_closed()


async def main():
    server = await asyncio.start_server(
        handle_client,
        HOST,
        PORT,
    )

    print(f"[REDIRECTOR] listening on {HOST}:{PORT}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())