import asyncio

HOST = "127.0.0.1"
PORT = 44125


async def handle_client(reader, writer):
    peer = writer.get_extra_info("peername")
    print(f"[44125] connection from {peer}")

    try:
        while True:
            data = await reader.read(4096)

            if not data:
                break

            print(f"[44125] received {len(data)} bytes")
            print(data.hex(" "))

    except Exception as exc:
        print(f"[44125] error: {exc!r}")

    finally:
        print(f"[44125] disconnected: {peer}")
        writer.close()

        try:
            await writer.wait_closed()
        except (ConnectionResetError, OSError):
            pass


async def main():
    server = await asyncio.start_server(
        handle_client,
        HOST,
        PORT,
    )

    print(f"[44125] listening on {HOST}:{PORT}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())