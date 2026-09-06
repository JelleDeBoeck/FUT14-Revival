const LOCAL_FUT_HOST = [127, 0, 0, 1];

function ipv4FromBytes(bytes) {
    return (
        bytes[0] + "." +
        bytes[1] + "." +
        bytes[2] + "." +
        bytes[3]
    );
}

function readSockaddr(addr) {
    try {
        const family = addr.readU16();

        if (family === 2) {
            const portBytes = addr.add(2).readByteArray(2);
            const ipBytes = addr.add(4).readByteArray(4);

            const p = new Uint8Array(portBytes);
            const ip = new Uint8Array(ipBytes);

            const port = (p[0] << 8) | p[1];

            return {
                family: "IPv4",
                address: ipv4FromBytes(ip),
                port: port
            };
        }

        return {
            family: family,
            address: "?",
            port: 0
        };
    } catch (e) {
        return {
            family: "error",
            address: "?",
            port: 0
        };
    }
}

function safeUtf16(ptr) {
    try {
        if (ptr.isNull()) {
            return "";
        }

        return ptr.readUtf16String();
    } catch (e) {
        return "<read error>";
    }
}

function safeCString(ptr) {
    try {
        if (ptr.isNull()) {
            return "";
        }

        return ptr.readCString();
    } catch (e) {
        return "<read error>";
    }
}

function hookExport(exportName, callbacks) {
    const address = Module.findGlobalExportByName(exportName);

    if (!address) {
        console.log("[!] Niet gevonden: " + exportName);
        return;
    }

    console.log(
        "[+] Hook " +
        exportName +
        " @ " +
        address
    );

    Interceptor.attach(
        address,
        callbacks
    );
}


// ============================================================
// Raw Winsock connections
// ============================================================

hookExport("connect", {
    onEnter(args) {
        const sockaddr = args[1];
        const dst = readSockaddr(sockaddr);

        console.log(
            "[connect] " +
            dst.address +
            ":" +
            dst.port
        );

        if (dst.port === 44125) {
            sockaddr
                .add(4)
                .writeByteArray(LOCAL_FUT_HOST);

            console.log(
                "[redirect] " +
                dst.address +
                ":44125 -> 127.0.0.1:44125"
            );
        }
    }
});


hookExport("WSAConnect", {
    onEnter(args) {
        const sockaddr = args[1];
        const dst = readSockaddr(sockaddr);

        console.log(
            "[WSAConnect] " +
            dst.address +
            ":" +
            dst.port
        );

        if (dst.port === 44125) {
            sockaddr
                .add(4)
                .writeByteArray(LOCAL_FUT_HOST);

            console.log(
                "[redirect] " +
                dst.address +
                ":44125 -> 127.0.0.1:44125"
            );
        }
    }
});


// ============================================================
// DNS
// ============================================================

hookExport("getaddrinfo", {
    onEnter(args) {
        const host = safeCString(args[0]);

        if (host) {
            console.log(
                "[getaddrinfo] " +
                host
            );
        }
    }
});


hookExport("GetAddrInfoW", {
    onEnter(args) {
        const host = safeUtf16(args[0]);

        if (host) {
            console.log(
                "[GetAddrInfoW] " +
                host
            );
        }
    }
});


hookExport("gethostbyname", {
    onEnter(args) {
        const host = safeCString(args[0]);

        if (host) {
            console.log(
                "[gethostbyname] " +
                host
            );
        }
    }
});


// ============================================================
// WinHTTP
// ============================================================

hookExport("WinHttpConnect", {
    onEnter(args) {
        const host = safeUtf16(args[1]);
        const port = args[2].toInt32() & 0xffff;

        console.log(
            "[WinHttpConnect] " +
            host +
            ":" +
            port
        );

        this.host = host;
        this.port = port;
    }
});


hookExport("WinHttpOpenRequest", {
    onEnter(args) {
        const verb = safeUtf16(args[1]);
        const path = safeUtf16(args[2]);

        console.log(
            "[WinHttpOpenRequest] " +
            (verb || "GET") +
            " " +
            path
        );
    }
});


hookExport("WinHttpSendRequest", {
    onEnter(args) {
        let headers = "";

        try {
            headers = safeUtf16(args[1]);
        } catch (e) {}

        console.log(
            "[WinHttpSendRequest]"
        );

        if (headers) {
            console.log(
                "  headers: " +
                headers.replace(
                    /\r?\n/g,
                    " | "
                )
            );
        }
    }
});


// ============================================================
// WinINet
// ============================================================

hookExport("InternetConnectW", {
    onEnter(args) {
        const host = safeUtf16(args[1]);
        const port = args[2].toInt32() & 0xffff;

        console.log(
            "[InternetConnectW] " +
            host +
            ":" +
            port
        );
    }
});


hookExport("HttpOpenRequestW", {
    onEnter(args) {
        const verb = safeUtf16(args[1]);
        const path = safeUtf16(args[2]);

        console.log(
            "[HttpOpenRequestW] " +
            (verb || "GET") +
            " " +
            path
        );
    }
});


hookExport("HttpSendRequestW", {
    onEnter(args) {
        const headers = safeUtf16(args[1]);

        console.log(
            "[HttpSendRequestW]"
        );

        if (headers) {
            console.log(
                "  headers: " +
                headers.replace(
                    /\r?\n/g,
                    " | "
                )
            );
        }
    }
});


hookExport("InternetOpenUrlW", {
    onEnter(args) {
        const url = safeUtf16(args[1]);

        console.log(
            "[InternetOpenUrlW] " +
            url
        );
    }
});


// ============================================================
// ANSI WinINet fallbacks
// ============================================================

hookExport("InternetConnectA", {
    onEnter(args) {
        const host = safeCString(args[1]);
        const port = args[2].toInt32() & 0xffff;

        console.log(
            "[InternetConnectA] " +
            host +
            ":" +
            port
        );
    }
});


hookExport("HttpOpenRequestA", {
    onEnter(args) {
        const verb = safeCString(args[1]);
        const path = safeCString(args[2]);

        console.log(
            "[HttpOpenRequestA] " +
            (verb || "GET") +
            " " +
            path
        );
    }
});


hookExport("InternetOpenUrlA", {
    onEnter(args) {
        const url = safeCString(args[1]);

        console.log(
            "[InternetOpenUrlA] " +
            url
        );
    }
});


console.log(
    "[+] FIFA 14 uitgebreide netwerklogger actief"
);