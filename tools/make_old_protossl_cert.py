from pathlib import Path
import os
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CERT_DIR = ROOT / "research" / "certs"

OPENSSL = Path(r"C:\Program Files\Git\usr\bin\openssl.exe")
OPENSSL_CONFIG = CERT_DIR / "openssl-old-protossl.cnf"

OUTPUT_CERT = CERT_DIR / "gosredirector.crt"
OUTPUT_KEY = CERT_DIR / "gosredirector.key"

HOSTNAME = "gosredirector.ea.com"

CA_SUBJECT = (
    "/OU=Online Technology Group"
    "/O=Electronic Arts, Inc."
    "/L=Redwood City"
    "/ST=California"
    "/C=US"
    "/CN=OTG3 Certificate Authority"
)

SERVER_SUBJECT = (
    f"/CN={HOSTNAME}"
    "/OU=Global Online Studio"
    "/O=Electronic Arts, Inc."
    "/ST=California"
    "/C=US"
)


def run(*args):
    env = os.environ.copy()
    env["OPENSSL_CONF"] = str(OPENSSL_CONFIG)

    command = [str(OPENSSL), *map(str, args)]

    print()
    print(">", " ".join(command))

    subprocess.run(
        command,
        check=True,
        env=env,
    )


def patch_old_protossl_certificate(der_path: Path):
    data = bytearray(der_path.read_bytes())

    # md5WithRSAEncryption:
    # 1.2.840.113549.1.1.4
    md5_rsa_oid = bytes.fromhex(
        "2a864886f70d010104"
    )

    positions = []
    start = 0

    while True:
        pos = data.find(md5_rsa_oid, start)

        if pos == -1:
            break

        positions.append(pos)
        start = pos + 1

    print()
    print("md5WithRSAEncryption OID-posities:", positions)

    if len(positions) < 2:
        raise RuntimeError(
            "Kon de twee verwachte MD5-RSA OIDs "
            "niet vinden in het certificaat."
        )

    # Laat de signatureAlgorithm in TBSCertificate intact.
    #
    # Alleen de BUITENSTE signatureAlgorithm wordt aangepast:
    #
    # md5WithRSAEncryption ...1.1.4
    # ->
    # rsaEncryption        ...1.1.1
    #
    # Dit reproduceert de encoding die de oude ProtoSSL-client
    # nodig heeft.
    outer_oid = positions[-1]

    old_value = data[outer_oid + len(md5_rsa_oid) - 1]

    if old_value != 0x04:
        raise RuntimeError(
            f"Onverwachte OID-byte: 0x{old_value:02x}"
        )

    data[outer_oid + len(md5_rsa_oid) - 1] = 0x01

    der_path.write_bytes(data)

    print(
        "Outer signatureAlgorithm gepatcht: "
        "md5WithRSAEncryption -> rsaEncryption"
    )


def main():
    if not OPENSSL.exists():
        raise FileNotFoundError(
            f"OpenSSL niet gevonden: {OPENSSL}"
        )

    if not OPENSSL_CONFIG.exists():
        raise FileNotFoundError(
            f"OpenSSL-config niet gevonden: {OPENSSL_CONFIG}"
        )

    CERT_DIR.mkdir(parents=True, exist_ok=True)

    # Maak eerst backups van onze huidige bestanden.
    if OUTPUT_CERT.exists():
        shutil.copy2(
            OUTPUT_CERT,
            CERT_DIR / "gosredirector-before-protossl.crt",
        )

    if OUTPUT_KEY.exists():
        shutil.copy2(
            OUTPUT_KEY,
            CERT_DIR / "gosredirector-before-protossl.key",
        )

    with tempfile.TemporaryDirectory() as temp_name:
        temp = Path(temp_name)

        ca_key = temp / "otg3-ca.key"
        ca_cert = temp / "otg3-ca.crt"

        server_key = temp / "server.key"
        server_csr = temp / "server.csr"
        server_cert = temp / "server.crt"

        server_der = temp / "server.der"
        patched_pem = temp / "server-patched.crt"

        extensions = temp / "server-ext.cnf"

        extensions.write_text(
            """
[v3_server]
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[alt_names]
DNS.1=gosredirector.ea.com
DNS.2=localhost
IP.1=127.0.0.1
""".strip()
            + "\n",
            encoding="ascii",
        )

        print("=== 1. Oude OTG3 CA maken ===")

        run(
            "req",
            "-x509",
            "-newkey",
            "rsa:1024",
            "-md5",
            "-nodes",
            "-days",
            "3650",
            "-keyout",
            ca_key,
            "-out",
            ca_cert,
            "-subj",
            CA_SUBJECT,
        )

        print()
        print("=== 2. Server key + CSR maken ===")

        run(
            "req",
            "-new",
            "-newkey",
            "rsa:1024",
            "-md5",
            "-nodes",
            "-keyout",
            server_key,
            "-out",
            server_csr,
            "-subj",
            SERVER_SUBJECT,
        )

        print()
        print("=== 3. Servercertificaat ondertekenen ===")

        run(
            "x509",
            "-req",
            "-in",
            server_csr,
            "-CA",
            ca_cert,
            "-CAkey",
            ca_key,
            "-set_serial",
            "1001",
            "-days",
            "3650",
            "-md5",
            "-extfile",
            extensions,
            "-extensions",
            "v3_server",
            "-out",
            server_cert,
        )

        print()
        print("=== 4. PEM -> DER ===")

        run(
            "x509",
            "-in",
            server_cert,
            "-outform",
            "DER",
            "-out",
            server_der,
        )

        print()
        print("=== 5. Oude ProtoSSL encoding toepassen ===")

        patch_old_protossl_certificate(server_der)

        print()
        print("=== 6. Gepatchte DER -> PEM ===")

        run(
            "x509",
            "-inform",
            "DER",
            "-in",
            server_der,
            "-outform",
            "PEM",
            "-out",
            patched_pem,
        )

        shutil.copy2(
            patched_pem,
            OUTPUT_CERT,
        )

        shutil.copy2(
            server_key,
            OUTPUT_KEY,
        )

        # CA bewaren voor onderzoek/debugging.
        shutil.copy2(
            ca_cert,
            CERT_DIR / "otg3-ca.crt",
        )

        print()
        print("=== Klaar ===")
        print("Cert:", OUTPUT_CERT)
        print("Key :", OUTPUT_KEY)

        print()
        print("=== Controle ===")

        run(
            "x509",
            "-in",
            OUTPUT_CERT,
            "-noout",
            "-subject",
            "-issuer",
            "-text",
        )


if __name__ == "__main__":
    main()