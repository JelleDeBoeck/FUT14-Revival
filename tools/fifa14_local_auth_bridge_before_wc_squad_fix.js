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

function install(m) {

    try {
        Interceptor.attach(m.base.add(0x73AF0), {
            onEnter() {
                const holder = m.base.add(0x1D6B5C).readPointer();
                const vt = holder.readPointer();
                const target = vt.add(0x70).readPointer();

                console.log(
                    "[WC-LOADACTIVE] HIT wrapper | holder=" + holder +
                    " vt=" + vt +
                    " target+0x70=" + target +
                    " | " + moduleInfo(target)
                );
            }
        });

        console.log("[WC-LOADACTIVE] hook actief @ CardsDLLzf+0x73AF0");

        Interceptor.attach(m.base.add(0x75250), {
            onEnter(args) {
                const mgr = ptr(this.context.esi);
                const vt = mgr.readPointer();
                const asyncTarget = vt.add(0x18).readPointer();

                console.log(
                    "[WC-LOADACTIVE-NATIVE] ENTER" +
                    " esi=" + mgr +
                    " vt=" + vt +
                    " async+0x18=" + asyncTarget +
                    " | " + moduleInfo(asyncTarget) +
                    " arg0=" + args[0] +
                    " arg1=" + args[1]
                );
            },
            onLeave(retval) {
                console.log(
                    "[WC-LOADACTIVE-NATIVE] RETURN retval=" + retval
                );
            }
        });

        console.log("[WC-LOADACTIVE-NATIVE] hook actief @ CardsDLLzf+0x75250");

    } catch (e) {
        console.log("[WC-LOADACTIVE] hook fout: " + e);
    }

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
            console.log(
                "[WC-CREATEUSER] ================================="
            );

            console.log(
                "[WC-CREATEUSER] HIT"
            );

            console.log(
                "[WC-CREATEUSER] this = " +
                args[0]
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

function findFccLogin2Branch(patchForWC = false) {
    const pattern =
        "AE 21 AF 4A 4C 9D 00 05 00 00 00 17 " +
        "AE 21 AF 4C 12 9D 00 08 00 00 00 59 " +
        "B0 4D 99 03 00 00 00 59 B0 4E";

    let hits = 0;

    for (const r of Process.enumerateRanges("r--")) {
        try {
            const matches = Memory.scanSync(
                r.base,
                r.size,
                pattern
            );

            for (const m of matches) {
                hits++;

                const secondBranch = m.address.add(0x11);

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

                if (
                    patchForWC &&
                    wcFirstTimeInitSeen &&
                    !wcFccPatched
                ) {
                    console.log(
                        "[WC-FCC-PATCH] WC instance gevonden"
                    );

                    try {

                        // =================================================
                        // PATCH 1
                        // LoginFinalizedSuccessContinue()
                        // -> NewUserFlow()
                        // =================================================

                        console.log(
                            "[WC-FCC-PATCH] PATCH 1 branch @ " +
                            secondBranch
                        );

                        console.log(
                            "[WC-FCC-PATCH] PATCH 1 verwacht: " +
                            "9D 00 08 00 00 00"
                        );

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

                        Memory.protect(
                            secondBranch,
                            6,
                            "rwx"
                        );


                        // =================================================
                        // PATCH 2 UITGESCHAKELD
                        // =================================================

                        console.log(
                            "[WC-FORCE-LOADSUCCESS] PATCH 2 UITGESCHAKELD"
                        );

                        wcFccPatched = true;

                        console.log(
                            "[WC-FCC-PATCH] PATCH 1 actief, PATCH 2 UIT"
                        );

                    } catch (e) {
                        console.log(
                            "[WC-FCC-PATCH] fout: " +
                            e
                        );
                    }
                }
            }

        } catch (e) {
            // scan range kan ongeldig zijn; volgende range proberen
        }
    }

    console.log(
        "[FCC-LOGIN2-BRANCH] scan klaar, hits=" +
        hits
    );

    return hits;
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

setTimeout(() => {
    dumpRuntimeCode("F8131", 0xF8131, 30);
    dumpRuntimeCode("F8DBA", 0xF8DBA, 30);
    dumpRuntimeCode("BA1AF", 0xBA1AF, 30);
    dumpRuntimeCode("C4450", 0xC4450, 100);
}, 16000);

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

