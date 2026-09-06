console.log("[WC-VTABLE] wachten op CardsDLLzf.dll...");

const TARGET_RVA = 0x0008A7E0;

let installed = false;
let logged = false;

function install(m) {
    if (installed) return;
    installed = true;

    const target = m.base.add(TARGET_RVA);

    console.log("[WC-VTABLE] Cards gevonden @ " + m.base);
    console.log("[WC-VTABLE] hook function entry @ " + target);

    Interceptor.attach(target, {
        onEnter(args) {
            if (logged) return;

            try {
                // 0x1008A7E0 doet later:
                //   mov esi, [ebp+8]
                // dus args[0] is precies het tile/interface object.
                const tile = args[0];

                if (tile.isNull()) {
                    console.log("[WC-VTABLE] tile=NULL");
                    return;
                }

                const vtable = tile.readPointer();

                if (vtable.isNull()) {
                    console.log("[WC-VTABLE] vtable=NULL");
                    return;
                }

                const fn28 = vtable.add(0x28).readPointer();
                const fn34 = vtable.add(0x34).readPointer();
                const fn38 = vtable.add(0x38).readPointer();

                console.log("[WC-VTABLE] =================================");
                console.log("[WC-VTABLE] tile   = " + tile);
                console.log("[WC-VTABLE] vtable = " + vtable);
                console.log("[WC-VTABLE] +0x28  = " + fn28);
                console.log("[WC-VTABLE] +0x34  = " + fn34);
                console.log("[WC-VTABLE] +0x38  = " + fn38);

                for (const [name, addr] of [
                    ["+0x28", fn28],
                    ["+0x34", fn34],
                    ["+0x38", fn38]
                ]) {
                    const mod = Process.findModuleByAddress(addr);

                    if (mod) {
                        const rva = addr.sub(mod.base);
                        console.log(
                            "[WC-VTABLE] " + name +
                            " -> " + mod.name +
                            " RVA=" + rva
                        );
                    } else {
                        console.log(
                            "[WC-VTABLE] " + name +
                            " -> module onbekend"
                        );
                    }
                }

                console.log("[WC-VTABLE] =================================");

                logged = true;

            } catch (e) {
                console.log("[WC-VTABLE] fout: " + e);
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