import socket
import ssl
from pathlib import Path


HOST = "127.0.0.1"
PORT = 42127

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CERT_FILE = PROJECT_ROOT / "research" / "certs" / "gosredirector.crt"
KEY_FILE = PROJECT_ROOT / "research" / "certs" / "gosredirector.key"


def main():
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

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()

        print(f"[DEBUG 44125] listening on {HOST}:{PORT}")

        while True:
            client, address = server.accept()
            print(f"[DEBUG 44125] TCP connection from {address}")

            hello = client.recv(4096, socket.MSG_PEEK)

            print(
                f"[DEBUG 42127] ClientHello {len(hello)} bytes:"
            )
            print(hello.hex(" "))

            try:
                with context.wrap_socket(
                    client,
                    server_side=True,
                ) as tls_client:
                    print(
                        "[DEBUG 44125] TLS handshake SUCCESS:",
                        tls_client.version(),
                        tls_client.cipher(),
                    )

                    data = tls_client.recv(4096)

                    print(
                        f"[DEBUG 44125] received {len(data)} bytes"
                    )

                    if data:
                        print(data.hex(" "))

            except ssl.SSLError as exc:
                print(
                    "[DEBUG 44125] TLS handshake FAILED:",
                    repr(exc),
                )

            except Exception as exc:
                print(
                    "[DEBUG 44125] ERROR:",
                    repr(exc),
                )

            finally:
                try:
                    client.close()
                except OSError:
                    pass


if __name__ == "__main__":
    main()