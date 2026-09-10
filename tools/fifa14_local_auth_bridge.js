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

        for (let i = 0; i < 400; i++) {
            const ins = Instruction.parse(p);

            console.log(
                "[WC-CODE] " +
                ins.address +
                "  " +
                ins.toString()
            );

            if (ins.mnemonic === "ret") {
                break;
            }

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

    dumpCode("FIFA_C41C2", exe.base.add(0x000C41C2));

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

function dumpLoadActiveTarget(target, m) {
    try {
        console.log("[WC-LOADACTIVE-DISASM] ===== BEGIN =====");
        console.log(
            "[WC-LOADACTIVE-DISASM] target=" + target +
            " | " + moduleInfo(target)
        );

        let p = target;

        for (let i = 0; i < 100; i++) {
            const ins = Instruction.parse(p);

            console.log(
                "[WC-LOADACTIVE-DISASM] " +
                p.sub(m.base) +
                "  " +
                ins.mnemonic +
                " " +
                ins.opStr
            );

            p = ins.next;

            if (ins.mnemonic === "ret") {
                break;
            }
        }

        console.log("[WC-LOADACTIVE-DISASM] ===== END =====");
    } catch (e) {
        console.log("[WC-LOADACTIVE-DISASM] fout: " + e);
    }
}

function install(m) {

        // WC LoadActiveSquad callback bridge.
    // A7F90 bewaart:
    //   OUTER+0x1B4 = callback uit native arg1
    //   OUTER+0x1CC = callback uit native arg2
    //
    // We observeren eerst welke callback A6A50 werkelijk kiest.
    // Geen branchpatch en geen resultcodepatch.
    let wcLoadActiveCompletionArmed = false;

        try {
        Interceptor.attach(m.base.add(0xA6A50), {
            onEnter(args) {
                try {
                    if (!wcFirstTimeInitSeen || !wcLoadActiveCompletionArmed) {
                        return;
                    }

                    wcLoadActiveCompletionArmed = false;

                    const result = ptr(args[0]);

                    if (result.isNull()) {
                        console.log("[WC-CALLBACK-BRIDGE] result=NULL");
                        return;
                    }

                    const code = result.add(0x18).readS32();

                    console.log(
                        "[WC-CALLBACK-BRIDGE] completion code=" + code
                    );

                    if (code !== 0) {
                        console.log(
                            "[WC-CALLBACK-BRIDGE] geen success; niets geforceerd"
                        );
                        return;
                    }

                    const outer = ptr(this.context.ecx);

                    if (outer.isNull()) {
                        console.log("[WC-CALLBACK-BRIDGE] OUTER=NULL");
                        return;
                    }

                    const cb1 = outer.add(0x1B4).readPointer();
                    const cb2 = outer.add(0x1CC).readPointer();

                    console.log(
                        "[WC-CALLBACK-BRIDGE] OUTER=" + outer +
                        " cb+1B4=" + cb1 +
                        " cb+1CC=" + cb2
                    );

                    console.log(
                        "[WC-DISPATCH-CHECK] code=0" +
                        " OUTER=" + outer +
                        " success(+1B4)=" + cb1 +
                        " failure(+1CC)=" + cb2
                    );

                    this.wcDispatchCheck = true;

                } catch (e) {
                    console.log(
                        "[WC-CALLBACK-BRIDGE] fout: " + e
                    );
                }
            },

            onLeave(retval) {
                if (this.wcDispatchCheck) {
                    console.log(
                        "[WC-DISPATCH-CHECK] A6A50 RETURNED"
                    );
                }
            }
        });

        console.log("[WC-CALLBACK-BRIDGE] A6A50 hook actief");

    } catch (e) {
        console.log(
            "[WC-CALLBACK-BRIDGE] install fout: " + e
        );
    }

        // =========================================================
    

        // =========================================================
    // WC native 23-player build probe
    // =========================================================
    try {
        Interceptor.attach(m.base.add(0xA6590), {
            onEnter(args) {
                if (!wcFirstTimeInitSeen) {
                    return;
                }

                this.wcHit = true;

                console.log(
                    "[WC-23BUILD] ENTER" +
                    " this=" + this.context.ecx +
                    " arg1=" + args[0] +
                    " arg2=" + args[1] +
                    " arg3=" + args[2]
                );
            },

            onLeave(retval) {
                if (!this.wcHit) {
                    return;
                }

                console.log(
                    "[WC-23BUILD] LEAVE retval=" + retval +
                    " bool=" + (retval.toInt32() & 0xff)
                );
            }
        });

        console.log("[WC-23BUILD] probe actief @ +0xA6590");

    } catch (e) {
        console.log("[WC-23BUILD] install fout: " + e);
    }

    /*    // =========================================================
    // WC A75D0 guard intervention
    // TEST: force internal squad/card count to >= 11
    // only while WC FirstTime flow is active
    // =========================================================
    try {
        Interceptor.attach(m.base.add(0xA75D0), {
            onEnter() {
                if (!wcFirstTimeInitSeen) {
                    return;
                }

                try {
                    // ED80 service object that BuildSquad uses.
                    const root = m.base.add(0x1D0C98);
                    const rootVt = root.readPointer();

                    const lookup1 =
                        rootVt.add(0x18).readPointer();

                    const level1 =
                        new NativeFunction(
                            lookup1,
                            "pointer",
                            ["uint"]
                        )(0x0ED80ED8);

                    if (level1.isNull()) {
                        console.log(
                            "[WC-A75-GUARD] level1=NULL"
                        );
                        return;
                    }

                    const level1Vt = level1.readPointer();
                    const lookup2 =
                        level1Vt.add(0x0C).readPointer();

                    const esi =
                        new NativeFunction(
                            lookup2,
                            "pointer",
                            ["uint"],
                            "thiscall"
                        ).call(level1, 0x0ED80ED9);

                    if (esi.isNull()) {
                        console.log(
                            "[WC-A75-GUARD] ESI=NULL"
                        );
                        return;
                    }

                    const oldValue =
                        esi.add(0x674).readU32();

                    console.log(
                        "[WC-A75-GUARD] ESI=" + esi +
                        " old=" + oldValue
                    );

                    if (oldValue < 11) {
                        esi.add(0x674).writeU32(11);

                        console.log(
                            "[WC-A75-GUARD] FORCED " +
                            oldValue + " -> 11"
                        );
                    } else {
                        console.log(
                            "[WC-A75-GUARD] already >= 11"
                        );
                    }

                } catch (e) {
                    console.log(
                        "[WC-A75-GUARD] fout: " + e
                    );
                }
            }
        });

        console.log(
            "[WC-A75-GUARD] intervention actief @ +0xA75D0"
        );

    } catch (e) {
        console.log(
            "[WC-A75-GUARD] install fout: " + e
        );
    }*/

    try {
        Interceptor.attach(m.base.add(0x3B4D0), {
            onEnter(args) {
                this.wc = wcFirstTimeInitSeen === true;

                if (!this.wc) {
                    return;
                }

                try {
                    console.log(
                        "[WC-3B4D0] ENTER" +
                        " this=" + this.context.ecx +
                        " arg1=" + args[0] +
                        " arg2=" + args[1] +
                        " arg3=" + args[2]
                    );
                } catch (e) {
                    console.log("[WC-3B4D0] enter fout: " + e);
                }
            }
        });

        Interceptor.attach(m.base.add(0x3B50B), {
            onEnter() {
                if (!wcFirstTimeInitSeen) {
                    return;
                }

                try {
                    const ebx = ptr(this.context.ebx);

                    if (ebx.isNull()) {
                        console.log("[WC-3B4D0] EBX=NULL");
                        return;
                    }

                    const vt = ebx.readPointer();
                    const target70 = vt.add(0x70).readPointer();

                    console.log(
                        "[WC-3B4D0] VMOBJ=" + ebx +
                        " VT=" + vt +
                        " VT+70=" + target70 +
                        " VT+70_RVA=" + target70.sub(m.base)
                    );
                } catch (e) {
                    console.log("[WC-3B4D0] VMOBJ fout: " + e);
                }
            }
        });
/*
        Interceptor.attach(m.base.add(0x3B52A), {
            onEnter() {
                if (!wcFirstTimeInitSeen) {
                    return;
                }

                try {
                    console.log(
                        "[WC-3B4D0] CALL+70" +
                        " ecx=" + this.context.ecx +
                        " value=" + this.context.eax
                    );
                } catch (e) {
                    console.log("[WC-3B4D0] CALL+70 fout: " + e);
                }
            }
        });
*/
        console.log("[WC-3B4D0] probes actief");

    } catch (e) {
        console.log("[WC-3B4D0] install fout: " + e);
    }


    try {
        Interceptor.attach(m.base.add(0x73AF0), {
            onEnter() {
                if (wcFirstTimeInitSeen) {
                    wcLoadActiveCompletionArmed = true;
                    console.log(
                        "[WC-CALLBACK-BRIDGE] armed door WC LoadActiveSquad"
                    );
                }

                try {
                    const globalPtr = m.base.add(0x1D6B5C);
                    const obj = globalPtr.readPointer();

                    if (obj.isNull()) {
                        console.log("[WC-FAST] LoadActive: object=NULL");
                        return;
                    }

                    const vt = obj.readPointer();
                    const fn70 = vt.add(0x70).readPointer();

                    console.log("[WC-FAST] ===== LoadActiveSquad =====");
                    console.log("[WC-FAST] object=" + obj);
                    console.log("[WC-FAST] vtable=" + vt);
                    console.log(
                        "[WC-FAST] slot70=" + fn70 +
                        " | " + moduleInfo(fn70)
                    );
                } catch (e) {
                    console.log("[WC-FAST] error: " + e);
                }
            }
        });

        let wcLookup2Hooked = false;

        const root = m.base.add(0x1D0C98);
        const rootVt = root.readPointer();
        const lookup1Target = rootVt.add(0x18).readPointer();

        console.log(
            "[WC-LOADACTIVE-REAL] root=" + root +
            " rootVt=" + rootVt +
            " lookup1=" + lookup1Target +
            " | " + moduleInfo(lookup1Target)
        );

        Interceptor.attach(lookup1Target, {
            onEnter(args) {
                this.wcMatch = false;

                try {
                    const hash = args[0].toUInt32();

                    if (hash === 0x0E9E4F96) {
                        this.wcMatch = true;

                        /*console.log(
                            "[WC-LOADACTIVE-REAL] lookup1 hash=0x" +
                            hash.toString(16)
                        );*/
                    }
                } catch (e) {
                    console.log("[WC-LOADACTIVE-REAL] lookup1 enter fout: " + e);
                }
            },

            onLeave(retval) {
                if (!this.wcMatch) return;

                try {
                    const level1 = ptr(retval);

                    /*console.log(
                        "[WC-LOADACTIVE-REAL] level1=" + level1
                    );*/

                    if (level1.isNull()) {
                        console.log("[WC-LOADACTIVE-REAL] level1 NULL");
                        return;
                    }

                    if (wcLookup2Hooked) return;

                    const level1Vt = level1.readPointer();
                    const lookup2Target =
                        level1Vt.add(0x0C).readPointer();

                    console.log(
                        "[WC-LOADACTIVE-REAL] level1Vt=" + level1Vt +
                        " lookup2=" + lookup2Target +
                        " | " + moduleInfo(lookup2Target)
                    );

                    wcLookup2Hooked = true;

                    Interceptor.attach(lookup2Target, {
                        onEnter(args) {
                            this.wcMatch = false;

                            try {
                                const hash = args[0].toUInt32();

                                if (hash === 0x0E9E4F97) {
                                    this.wcMatch = true;

                                    /*console.log(
                                        "[WC-LOADACTIVE-REAL] lookup2 hash=0x" +
                                        hash.toString(16)
                                    );*/
                                }
                            } catch (e) {
                                console.log(
                                    "[WC-LOADACTIVE-REAL] lookup2 enter fout: " + e
                                );
                            }
                        },

                        onLeave(retval) {
                            if (!this.wcMatch) return;

                            try {
                                const obj = ptr(retval);

                                /*console.log(
                                    "[WC-LOADACTIVE-REAL] obj=" + obj
                                );*/

                                if (obj.isNull()) {
                                    console.log(
                                        "[WC-LOADACTIVE-REAL] obj NULL"
                                    );
                                    return;
                                }

                                const vt = obj.readPointer();
                                const fn18 =
                                    vt.add(0x18).readPointer();

                                /*console.log(
                                    "[WC-LOADACTIVE-REAL] vt=" + vt
                                );

                                console.log(
                                    "[WC-LOADACTIVE-REAL] fn18=" +
                                    fn18 +
                                    " | " +
                                    moduleInfo(fn18)
                                );

                                /*dumpCode(
                                    "LOADACTIVE_REAL_IMPL",
                                    fn18
                                );*/

                            } catch (e) {
                                console.log(
                                    "[WC-LOADACTIVE-REAL] lookup2 leave fout: " + e
                                );
                            }
                        }
                    });

                } catch (e) {
                    console.log(
                        "[WC-LOADACTIVE-REAL] lookup1 leave fout: " + e
                    );
                }
            }
        });

        console.log("[WC-LOADACTIVE] hook actief @ CardsDLLzf+0x73AF0");
        console.log("[WC-LOADACTIVE-REAL] lookup hooks actief");

    } catch (e) {
        console.log("[WC-LOADACTIVE] hook fout: " + e);
    }

    if (installed) return;
    installed = true;

    console.log("[AUTH+WC] Cards gevonden @ " + m.base);

    /*dumpCode(
        "CARDS_RESOLVER_1158E0",
        m.base.add(0x1158E0)
    );*/
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

                    if (
                        index === 1 &&
                        key === "PANEL_GOTO" &&
                        value === "GOTO_WORLD_CUP"
                    ) {
                        wcIndex1Seen = true;
                        wcObject = object;

                        console.log(
                            "[WC-HOLD] WORLD CUP OBJECT = " +
                            wcObject
                        );
                    }

                    if (
                        wcIndex1Seen &&
                        wcObject !== null &&
                        object.equals(wcObject) &&
                        index === 1
                    ) {
                        if (
                            key === "PANEL_GOTO" &&
                            value === "GOTO_WORLD_CUP"
                        ) {
                            console.log(
                                "[WC-HOLD] behoud PANEL_GOTO=GOTO_WORLD_CUP"
                            );
                            return;
                        }

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

                try {
                    const subObject = tile.add(0x20);
                    const subVtable = subObject.readPointer();

                    console.log(
                        "[WC-REAL] subObject = " +
                        subObject
                    );

                    console.log(
                        "[WC-REAL] subVtable = " +
                        subVtable
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

    // =========================================================
    // FIRST TIME INIT WC PROBE
    // =========================================================

    const firstTimeInitWC =
        m.base.add(0x8E290);

    const fccObjectGlobal =
        m.base.add(0x1D73B0);

    console.log(
        "[FirstTimeInitWC] hook @ " +
        firstTimeInitWC
    );

    Interceptor.attach(firstTimeInitWC, {
        onEnter() {
            console.log("[WC-FCC-PATCH] FirstTimeInitWC gezien; WC guard actief");

            wcFirstTimeInitSeen = true;
            wcFccPatched = false;

            try {
                findFccLogin2Branch(true);
            } catch (e) {
                console.log("[FCC-LOGIN2-BRANCH] FirstTimeInitWC scan fout: " + e);
            }

            try {
                const obj = fccObjectGlobal.readPointer();
                const vt = obj.readPointer();
                const fn = vt.add(0x0C).readPointer();

                console.log(
                    "[FirstTimeInitWC] obj=" +
                    obj +
                    " vtable=" +
                    vt +
                    " slot+0x0C=" +
                    fn +
                    " | " +
                    moduleInfo(fn)
                );

                const cardsDownloadedTarget =
                    vt.add(0x1C).readPointer();

                console.log(
                    "[WC-SQUAD-PROBE] FCC vtable=" +
                    vt
                );

                for (let off = 0; off <= 0x80; off += 4) {
                    try {
                        const target = vt.add(off).readPointer();

                        console.log(
                            "[WC-SQUAD-PROBE] slot+0x" +
                            off.toString(16) +
                            " = " +
                            target +
                            " | " +
                            moduleInfo(target)
                        );
                    } catch (_) {}
                }

                console.log(
                    "[WC-CARDSDOWNLOADED] late target=" +
                    cardsDownloadedTarget +
                    " | " +
                    moduleInfo(cardsDownloadedTarget)
                );

                if (!wcCardsDownloadedHooked) {
                    wcCardsDownloadedHooked = true;

                Interceptor.attach(cardsDownloadedTarget, {
                    onEnter() {
                        console.log("[WC-CARDSDOWNLOADED] FIRED");
                    }
                });

                    console.log(
                        "[WC-CARDSDOWNLOADED] hook actief"
                    );
                }

            } catch (e) {
                console.log(
                    "[WC-CARDSDOWNLOADED] late hook fout: " + e
                );
            }
        }
    });

    // =========================================================
    // WC INIT SUBSYSTEM VTABLE PROBE
    // =========================================================

    Interceptor.attach(
        m.base.add(0x38288),
        {
            onEnter() {
                try {
                    const o =
                        this.context.esi;

                    const vt =
                        o.readPointer();

                    console.log(
                        "[WC-INIT-SUB] obj=" +
                        o +
                        " vt=" +
                        vt
                    );

                    [0x30, 0x34, 0x38, 0x3c]
                        .forEach(off => {
                            const fn =
                                vt.add(off)
                                   .readPointer();

                            console.log(
                                "[WC-INIT-SUB] +" +
                                off.toString(16) +
                                " = " +
                                fn +
                                " | " +
                                moduleInfo(fn)
                            );
                        });

                } catch (e) {
                    console.log(
                        "[WC-INIT-SUB] fout: " +
                        e
                    );
                }
            }
        }
    );

    // =========================================================
    // WC INIT STRING PROBE
    // =========================================================

    function dumpMaybeString(label, addr) {
        try {
            const p = ptr(addr);

            let directUtf8 = "";
            let directUtf16 = "";
            let target = NULL;
            let ptrUtf8 = "";
            let ptrUtf16 = "";

            try {
                directUtf8 =
                    p.readUtf8String();
            } catch (_) {}

            try {
                directUtf16 =
                    p.readUtf16String();
            } catch (_) {}

            try {
                target =
                    p.readPointer();
            } catch (_) {}

            if (!target.isNull()) {
                try {
                    ptrUtf8 =
                        target.readUtf8String();
                } catch (_) {}

                try {
                    ptrUtf16 =
                        target.readUtf16String();
                } catch (_) {}
            }

            console.log(
                "[WC-STR] " +
                label +
                " @ " +
                p +
                " ptr=" +
                target +
                " | direct8=" +
                JSON.stringify(directUtf8) +
                " | direct16=" +
                JSON.stringify(directUtf16) +
                " | ptr8=" +
                JSON.stringify(ptrUtf8) +
                " | ptr16=" +
                JSON.stringify(ptrUtf16)
            );

        } catch (e) {
            console.log(
                "[WC-STR] " +
                label +
                " fout: " +
                e
            );
        }
    }

    [
        ["svc1", "0x0AE932D0"],
        ["svc2", "0x0AE932E8"],
        ["g499A82C", "0x499A82C"],
        ["g499AF94", "0x499AF94"],
        ["g499AFB0", "0x499AFB0"],
        ["g499A7CC", "0x499A7CC"],
        ["g499AC24", "0x499AC24"],
        ["g499AC28", "0x499AC28"],
        ["g499ACB8", "0x499ACB8"],
        ["g499ACC0", "0x499ACC0"],
        ["g499AED8", "0x499AED8"],
        ["g499A810", "0x499A810"],
        ["g499ACA8", "0x499ACA8"],
        ["g499D0DC", "0x499D0DC"]
    ].forEach(x =>
        dumpMaybeString(x[0], x[1])
    );

    // =========================================================
    // WORLD CUP CREATE USER PROBE
    // =========================================================

    const wcCreateUser =
        m.base.add(0x3B5D0);

    console.log(
        "[WC-CREATEUSER] hook @ " +
        wcCreateUser
    );

    // Dit is de thunk zelf.
    // We loggen alleen de binnenkomende argumenten.
    Interceptor.attach(wcCreateUser, {
        onEnter(args) {

            wcCreateUserThis = ptr(args[0]);

            console.log(
                "[WC-CREATEUSER] ================================="
            );

            console.log(
                "[WC-CREATEUSER] HIT"
            );

            console.log(
                "[WC-CREATEUSER] this = " +
                wcCreateUserThis
            );

            console.log(
                "[WC-CREATEUSER] arg1 = " +
                args[1]
            );

            console.log(
                "[WC-CREATEUSER] arg2 = " +
                args[2]
            );

            console.log(
                "[WC-CREATEUSER] ================================="
            );
        }
    });

    // =========================================================
    // TEMP: VTABLE TARGET INFO
    // =========================================================
    // GEEN aparte Interceptor.attach() op +0x53360.
    //
    // +0x3B5D0 doet:
    //
    //   mov ecx, [0x101d5978]
    //   mov eax, [ecx]
    //   mov edx, [eax+0x14]
    //   call edx
    //
    // Daarom lezen we hier alleen welk vtable-target gebruikt wordt.
    // =========================================================

        Interceptor.attach(wcCreateUser, {
        onEnter(args) {
            try {
                const obj =
                    m.base.add(0x1D5978)
                        .readPointer();

                if (obj.isNull()) {
                    console.log(
                        "[WC-CREATEUSER-TARGET] global object = NULL"
                    );
                    return;
                }

                const vt =
                    obj.readPointer();

                if (vt.isNull()) {
                    console.log(
                        "[WC-CREATEUSER-TARGET] vtable = NULL"
                    );
                    return;
                }

                const fn =
                    vt.add(0x14)
                      .readPointer();

                console.log(
                    "[WC-CREATEUSER-TARGET] obj=" +
                    obj +
                    " vt=" +
                    vt +
                    " slot+0x14=" +
                    fn +
                    " | " +
                    moduleInfo(fn)
                );

                console.log(
                    "[WC-CREATEUSER-TARGET] args=" +
                    args[0] +
                    " / " +
                    args[1] +
                    " / " +
                    args[2]
                );

            } catch (e) {
                console.log(
                    "[WC-CREATEUSER-TARGET] fout: " +
                    e
                );
            }
        },

        onLeave(retval) {
            console.log(
                "[WC-CREATEUSER-RETURN] CreateUser thunk returned; " +
                "fcc_login2 scan over 750ms"
            );

        setTimeout(() => {
            try {
                findFccLogin2Branch(true);
            } catch (e) {
                console.log(
                    "[FCC-LOGIN2-BRANCH] delayed scan fout: " +
                    e
                );
            }
        }, 750);
        }
    });

//     Interceptor.attach(m.base.add(0x8E290), {
//         onEnter() {
//             console.log("[WC-LOGINHELPER] FirstTimeInitWC hit");
// 
//             const bt = Thread.backtrace(
//                 this.context,
//                 Backtracer.ACCURATE
//             );
// 
//             for (let i = 0; i < bt.length; i++) {
//                 console.log(
//                     "[WC-LOGINHELPER] bt[" + i + "] " +
//                     bt[i] + " | " + moduleInfo(bt[i])
//                 );
//             }
//         }
//     });

    console.log("[WC-CREATEUSER] actief");
    console.log("[WC-VTABLE] actief");
}

let wcFirstTimeInitSeen = false;
let wcFccPatched = false;
let wcCreateUserThis = null;

function findFccLogin2Branch(patchForWC = false) {
    const pattern =
        "AE 21 AF 4A 4C 9D 00 05 00 00 00 17 " +
        "AE 21 AF 4C 12 9D 00 08 00 00 00 59 " +
        "B0 4D 99 03 00 00 00 59 B0 4E";

    const allHits = [];

    for (const r of Process.enumerateRanges("r--")) {
        try {
            const matches = Memory.scanSync(
                r.base,
                r.size,
                pattern
            );

            for (const m of matches) {
                allHits.push(m.address);

                const secondBranch =
                    m.address.add(0x11);

                console.log(
                    "[FCC-LOGIN2-BRANCH] HIT @ " +
                    m.address +
                    " range=" +
                    r.base +
                    " size=0x" +
                    r.size.toString(16)
                );

                console.log(
                    "[FCC-LOGIN2-BRANCH] second BranchIfTrue @ " +
                    secondBranch
                );
            }

        } catch (e) {
            // onleesbare range overslaan
        }
    }

    console.log(
        "[FCC-LOGIN2-BRANCH] scan klaar, hits=" +
        allHits.length
    );

    if (
        patchForWC &&
        wcFirstTimeInitSeen &&
        !wcFccPatched &&
        wcCreateUserThis !== null &&
        allHits.length > 0
    ) {
        let best = null;
        let bestDistance = Number.MAX_SAFE_INTEGER;

        const createUserAddr =
            wcCreateUserThis.toUInt32();

        for (const hit of allHits) {
            const hitAddr =
                hit.toUInt32();

            const distance =
                Math.abs(
                    hitAddr -
                    createUserAddr
                );

            console.log(
                "[WC-FCC-PATCH] kandidaat=" +
                hit +
                " distance=0x" +
                distance.toString(16)
            );

            if (distance < bestDistance) {
                best = hit;
                bestDistance = distance;
            }
        }

        if (best !== null) {
            const secondBranch =
                best.add(0x11);

            console.log(
                "[WC-FCC-PATCH] GEKOZEN instance=" +
                best
            );

            console.log(
                "[WC-FCC-PATCH] PATCH 1 branch @ " +
                secondBranch
            );

            console.log(
                "[WC-FCC-PATCH] PATCH 1 verwacht: " +
                "9D 00 08 00 00 00"
            );

            try {
                Memory.protect(
                    secondBranch,
                    6,
                    "rwx"
                );

                secondBranch.writeByteArray([
                    0x9D,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00
                ]);

                console.log(
                    "[WC-FCC-PATCH] PATCH 1 AFTER = " +
                    Array.from(
                        new Uint8Array(
                            secondBranch.readByteArray(6)
                        )
                    )
                    .map(
                        b =>
                            b
                                .toString(16)
                                .padStart(2, "0")
                    )
                    .join(" ")
                );

                console.log(
                    "[WC-FORCE-LOADSUCCESS] PATCH 2 UITGESCHAKELD"
                );

                wcFccPatched = true;

                console.log(
                    "[WC-FCC-PATCH] PATCH 1 actief op gekozen WC instance"
                );

            } catch (e) {
                console.log(
                    "[WC-FCC-PATCH] fout: " +
                    e
                );
            }
        }
    }

    return allHits.length;
}

/*const ionObj = ptr("0x101D73B0").readPointer();
const ionVtable = ionObj.readPointer();
const cardsDownloadedTarget = ionVtable.add(0x1C).readPointer();

console.log("[WC-CARDSDOWNLOADED] obj=" + ionObj);
console.log("[WC-CARDSDOWNLOADED] vtable=" + ionVtable);
console.log("[WC-CARDSDOWNLOADED] target=" + cardsDownloadedTarget);
*/

// Alleen diagnostische scan bij startup.
// Patcht NIETS.

function dumpRuntimeCode(label, rva, count = 25) {
    try {
        const exe = Process.getModuleByName("fifa14.exe");
        let p = exe.base.add(rva);

        console.log(
            "[WC-CALLER] ===== " +
            label +
            " RVA=0x" +
            rva.toString(16) +
            " ====="
        );

        for (let i = 0; i < count; i++) {
            const ins = Instruction.parse(p);

            console.log(
                "[WC-CALLER] " +
                ins.address +
                "  " +
                ins.mnemonic +
                " " +
                ins.opStr
            );

            p = ins.next;
        }
    } catch (e) {
        console.log(
            "[WC-CALLER] " +
            label +
            " fout: " +
            e
        );
    }
}

/*setTimeout(() => {
    dumpRuntimeCode("F8131", 0xF8131, 30);
    dumpRuntimeCode("F8DBA", 0xF8DBA, 30);
    dumpRuntimeCode("BA1AF", 0xBA1AF, 30);
    dumpRuntimeCode("C4450", 0xC4450, 100);
}, 16000);*/

setTimeout(() => {
    findFccLogin2Branch(false);
}, 15000);

let wcCardsDownloadedHooked = false;
let wcSquadEventProbeInstalled = false;
let wcLoadActiveSquadHooked = false;
let wcLoadActiveSquadTarget = null;
let wcSquadEventProbeCount = 0;
let wcLoadActiveSquadSeen = false;
setInterval(() => {

    if (installed) return;

    for (const m of Process.enumerateModules()) {

        if (/^CardsDLLzf\.dll$/i.test(m.name)) {

            install(m);

            try {

                const dispatchTable =
                    m.base.add(0x1D5314).readPointer();

                const dispatchTarget =
                    dispatchTable.add(0x354).readPointer();

                console.log(
                    "[WC-DISPATCH] table=" +
                    dispatchTable
                );

                console.log(
                    "[WC-DISPATCH] +0x354 target=" +
                    dispatchTarget
                );

                console.log(
                    "[WC-DISPATCH] CardsDLL RVA=" +
                    dispatchTarget.sub(m.base)
                );

                const dispatchModule =
                    Process.findModuleByAddress(dispatchTarget);

                console.log(
                    "[WC-DISPATCH] module=" +
                    (
                        dispatchModule
                            ? dispatchModule.name
                            : "unknown"
                    )
                );

                console.log(
                    "[WC-DISPATCH] moduleRVA=" +
                    (
                        dispatchModule
                            ? dispatchTarget.sub(
                                dispatchModule.base
                            )
                            : "n/a"
                    )
                );

                if (dispatchModule) {
                    console.log(
                        "[WC-DISPATCH] moduleBase=" +
                        dispatchModule.base +
                        " size=" +
                        dispatchModule.size
                    );
                }

                console.log(
                    "[WC-DISPATCH] ===== RUNTIME CODE ====="
                );

                const exe =
                    Process.getModuleByName("fifa14.exe");

                let p =
                    exe.base.add(0xC4170);

                for (let i = 0; i < 80; i++) {

                    const ins =
                        Instruction.parse(p);

                    console.log(
                        "[WC-DISPATCH] " +
                        ins.address +
                        " " +
                        ins.mnemonic +
                        " " +
                        ins.opStr
                    );

                    p = ins.next;
                }

            } catch (e) {

                console.log(
                    "[WC-DISPATCH] read failed: " +
                    e
                );
            }

            break;
        }
    }

}, 100);

function hookOutputDebugString(name, wide) {
    const addr = Module.findGlobalExportByName(name);

    if (addr === null) {
        console.log("[FIFA-TRACE] " + name + " not found");
        return;
    }

    Interceptor.attach(addr, {
        onEnter(args) {
            try {
                const text = wide
                    ? args[0].readUtf16String()
                    : args[0].readCString();

                if (text) {
                    console.log("[FIFA-TRACE] " + text);
                }
            } catch (e) {
                // Ignore unreadable strings.
            }
        }
    });

    console.log("[FIFA-TRACE] hooked " + name + " @ " + addr);
}

hookOutputDebugString("OutputDebugStringA", false);