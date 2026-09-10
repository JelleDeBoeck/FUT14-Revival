const m = Process.findModuleByName("CardsDLLzf.dll");

if (m === null) {
    console.log("CardsDLLzf.dll nog niet geladen");
} else {
    const start = m.base.add(0x75250);

    console.log("CardsDLLzf base = " + m.base);
    console.log("RVA 0x75250 = " + start);
    console.log("===== DISASM 0x75250 =====");

    let p = start;

    for (let i = 0; i < 100; i++) {
        try {
            const ins = Instruction.parse(p);
            console.log(
                ins.address.sub(m.base) +
                "  " +
                ins.mnemonic +
                " " +
                ins.opStr
            );

            p = ins.next;

            if (ins.mnemonic === "ret") {
                break;
            }
        } catch (e) {
            console.log("STOP @ " + p + ": " + e);
            break;
        }
    }
}
