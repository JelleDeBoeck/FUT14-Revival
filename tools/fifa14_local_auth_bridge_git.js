console.log("[AUTH+WC] wachten op CardsDLLzf.dll...");

const RVA = {
    // Bestaande AUTH-BRIDGE
    jsonBuilder: 0x0015ef70,
    sessionGate: 0x0015f2b4,
    tokenGate:   0x0015f2fa,
    submit:      0x0015ee20,

    // WC tile builder - function entry
    wcBuilder:   0x0008A7E0
};

const localSession =
    Memory.allocUtf8String("LOCAL-FIFA14-EASW-SESSION");

const localToken =
    Memory.allocUtf8String("LOCAL-FIFA14-EASW-TOKEN");

let installed = false;
let wcLogged = false;

const builderDepth = {};

function threadKey() {
    return String(Process.getCurrentThreadId());
}

function moduleInfo(addr) {
    const mod = Process.findModuleByAddress(addr);

    if (mod === null) {
        return "module onbekend";
    }

    return (
        mod.name +
        " RVA=" +
        addr.sub(mod.base)
    );
}

function dumpCode(name, addr) {
    try {
        console.log(
            "[WC-CODE] " + name +
            " @ " + addr
        );

        let p = addr;

        for (let i = 0; i < 100; i++) {
            const ins = Instruction.parse(p);

            console.log(
                "[WC-CODE] " +
                ins.address +
                "  " +
                ins.toString()
            );

            p = ins.next;
        }

    } catch (e) {
        console.log(
            "[WC-CODE] " +
            name +
            " fout: " +
            e
        );
    }
}

function safeCString(p) {
    try {
        if (p.isNull()) return "NULL";
        return p.readUtf8String();
    } catch (e) {
        return "<geen string>";
    }
}

function installRealSetterProbe() {
    const exe = Process.getModuleByName("fifa14.exe");
    const real38 = exe.base.add(0x0010C370);

    console.log(
        "[WC-SETTER] hook @ " +
        real38
    );

    Interceptor.attach(real38, {
        onEnter(args) {
            try {
                const index = args[0].toInt32();
                const key   = args[1];
                const value = args[2];

                console.log(
                    "[WC-SETTER] index=" + index +
                    " key=\"" + safeCString(key) + "\"" +
                    " value=\"" + safeCString(value) + "\"" +
                    " rawKey=" + key +
                    " rawValue=" + value
                );

            } catch (e) {
                console.log(
                    "[WC-SETTER] fout: " + e
                );
            }
        }
    });
}

let wcIndex1Seen = false;
let wcObject = null;

function install(m) {
    if (installed) return;
    installed = true;

    console.log("[AUTH+WC] Cards gevonden @ " + m.base);

    // =========================================================
    // AUTH BRIDGE
    // =========================================================

    Interceptor.attach(m.base.add(RVA.jsonBuilder), {
        onEnter() {
            const k = threadKey();

            builderDepth[k] =
                (builderDepth[k] || 0) + 1;
        },

        onLeave() {
            const k = threadKey();

            builderDepth[k] =
                Math.max(
                    0,
                    (builderDepth[k] || 1) - 1
                );
        }
    });

    Interceptor.attach(m.base.add(RVA.sessionGate), {
        onEnter() {
            const k = threadKey();
            const current = ptr(this.context.esi);

            if (
                (builderDepth[k] || 0) > 0 &&
                current.isNull()
            ) {
                this.context.esi = localSession;

                console.log(
                    "[AUTH-BRIDGE] lokale EASW session toegepast"
                );
            }
        }
    });

    Interceptor.attach(m.base.add(RVA.tokenGate), {
        onEnter() {
            const k = threadKey();
            const current = ptr(this.context.esi);

            if (
                (builderDepth[k] || 0) > 0 &&
                current.isNull()
            ) {
                this.context.esi = localToken;

                console.log(
                    "[AUTH-BRIDGE] lokale EASW token toegepast"
                );
            }
        }
    });

    Interceptor.attach(m.base.add(RVA.submit), {
        onEnter() {
            console.log(
                "[AUTH-BRIDGE] AUTH REQUEST SUBMIT BEREIKT"
            );
        }
    });

    console.log("[AUTH-BRIDGE] actief");

    // installWCSetterCallerProbe();

    function installWCSetterCallerProbe() {
        const exe = Process.getModuleByName("fifa14.exe");
        const real38 = exe.base.add(0x0010C370);

        console.log("[WC-HOLD] probe @ " + real38);

        Interceptor.attach(real38, {
            onEnter(args) {
                try {
                    const index = args[0].toInt32();
                    const key = safeCString(args[1]);
                    const value = safeCString(args[2]);
                    const object = ptr(this.context.ecx);

                    // Eerst het echte World Cup-object vinden.
                    if (
                        index === 1 &&
                        key === "PANEL_GOTO" &&
                        value === "GOTO_WORLD_CUP"
                    ) {
                        wcIndex1Seen = true;
                        wcObject = object;

                        console.log(
                            "[WC-HOLD] WORLD CUP OBJECT = " + wcObject
                        );
                    }

                    // Alleen ingrijpen op exact hetzelfde object.
                    if (
                        wcIndex1Seen &&
                        wcObject !== null &&
                        object.equals(wcObject) &&
                        index === 1
                    ) {
                        // Originele World Cup PANEL_GOTO gewoon doorlaten.
                        if (
                            key === "PANEL_GOTO" &&
                            value === "GOTO_WORLD_CUP"
                        ) {
                            console.log(
                                "[WC-HOLD] behoud PANEL_GOTO=GOTO_WORLD_CUP"
                            );
                            return;
                        }

                        // Originele World Cup MC_NAME gewoon doorlaten.
                        if (
                            key === "MC_NAME" &&
                            value ===
                                "external.ion_fut.components.Tile.Addon_GoToWC"
                        ) {
                            console.log(
                                "[WC-HOLD] behoud MC_NAME=Addon_GoToWC"
                            );
                            return;
                        }

                        // FIFA probeert PANEL_GOTO later te vervangen.
                        // Houd dezelfde property, maar forceer de WC-value.
                        if (
                            key === "PANEL_GOTO" &&
                            value !== "GOTO_WORLD_CUP"
                        ) {
                            console.log(
                                "[WC-HOLD] forceer PANEL_GOTO: " +
                                value +
                                " -> GOTO_WORLD_CUP"
                            );

                            args[2] = Memory.allocUtf8String(
                                "GOTO_WORLD_CUP"
                            );

                            return;
                        }

                        // FIFA probeert MC_NAME later te vervangen.
                        // Houd dezelfde property, maar forceer Addon_GoToWC.
                        if (
                            key === "MC_NAME" &&
                            value !==
                                "external.ion_fut.components.Tile.Addon_GoToWC"
                        ) {
                            console.log(
                                "[WC-HOLD] forceer MC_NAME: " +
                                value +
                                " -> Addon_GoToWC"
                            );

                            args[2] = Memory.allocUtf8String(
                                "external.ion_fut.components.Tile.Addon_GoToWC"
                            );

                            return;
                        }
                    }

                } catch (e) {
                    console.log(
                        "[WC-HOLD] fout: " + e
                    );
                }
            }
        });
    }

    // =========================================================
    // WORLD CUP VTABLE PROBE
    // =========================================================

    const wcBuilder =
        m.base.add(RVA.wcBuilder);

    console.log(
        "[WC-VTABLE] function entry @ " +
        wcBuilder
    );

    Interceptor.attach(wcBuilder, {
        onEnter(args) {
            if (wcLogged) return;

            try {
                const tile = args[0];

                console.log(
                    "[WC-VTABLE] builder bereikt"
                );

                if (tile.isNull()) {
                    console.log(
                        "[WC-VTABLE] tile = NULL"
                    );
                    return;
                }

                const vtable =
                    tile.readPointer();

                if (vtable.isNull()) {
                    console.log(
                        "[WC-VTABLE] vtable = NULL"
                    );
                    return;
                }

                const fn28 =
                    vtable
                        .add(0x28)
                        .readPointer();

                const fn34 =
                    vtable
                        .add(0x34)
                        .readPointer();

                const fn38 =
                    vtable
                        .add(0x38)
                        .readPointer();

                console.log(
                    "[WC-VTABLE] ================================="
                );

                console.log(
                    "[WC-VTABLE] tile   = " +
                    tile
                );

                console.log(
                    "[WC-VTABLE] vtable = " +
                    vtable
                );

                console.log(
                    "[WC-VTABLE] +0x28  = " +
                    fn28
                );

                console.log(
                    "[WC-VTABLE]         " +
                    moduleInfo(fn28)
                );

                console.log(
                    "[WC-VTABLE] +0x34  = " +
                    fn34
                );

                console.log(
                    "[WC-VTABLE]         " +
                    moduleInfo(fn34)
                );

                console.log(
                    "[WC-VTABLE] +0x38  = " +
                    fn38
                );

                console.log(
                    "[WC-VTABLE]         " +
                    moduleInfo(fn38)
                );

                console.log(
                    "[WC-VTABLE] ================================="
                );

                // Runtime disassembly van de echte implementations
                // =========================================================
                // Achter de fifa14.exe thunks kijken
                // =========================================================

                try {
                    const subObject = tile.add(0x20);
                    const subVtable = subObject.readPointer();

                    console.log(
                        "[WC-REAL] subObject = " + subObject
                    );

                    console.log(
                        "[WC-REAL] subVtable = " + subVtable
                    );

                    const real28 =
                        subVtable.add(0x04).readPointer();

                    const real34 =
                        subVtable.add(0x0C).readPointer();

                    const real38 =
                        subVtable.add(0x14).readPointer();

                    console.log(
                        "[WC-REAL] +0x28 -> subVT+0x04 = " +
                        real28 +
                        " | " +
                        moduleInfo(real28)
                    );

                    console.log(
                        "[WC-REAL] +0x34 -> subVT+0x0C = " +
                        real34 +
                        " | " +
                        moduleInfo(real34)
                    );

                    console.log(
                        "[WC-REAL] +0x38 -> subVT+0x14 = " +
                        real38 +
                        " | " +
                        moduleInfo(real38)
                    );

                    console.log(
                        "[WC-REAL] ===== REAL +0x38 CODE ====="
                    );

                    // dumpCode("REAL +0x28", real28);
                    // dumpCode("REAL +0x34", real34);
                    // dumpCode("REAL +0x38", real38);

                } catch (e) {
                    console.log(
                        "[WC-REAL] fout: " + e
                    );
                }
                wcLogged = true;

            } catch (e) {
                console.log(
                    "[WC-VTABLE] leesfout: " +
                    e
                );
            }
        }
    });

    console.log("[WC-VTABLE] actief");
}

setInterval(() => {
    if (installed) return;

    for (const m of Process.enumerateModules()) {
        if (/^CardsDLLzf\.dll$/i.test(m.name)) {
            install(m);
            break;
        }
    }
}, 100);