function log(msg) {
    console.log("[AUTH] " + msg);
}

const FIFA_NAME = "fifa14.exe";

const CARDS_RVAS = {
    requestStart: 0x0015f490,
    jsonBuilder: 0x0015ef70,
    requestSubmit: 0x0015ee20,
    easwSessionGate: 0x0015f2b4,
    easwTokenGate: 0x0015f2fa
};

let cardsBase = null;
let installed = false;

function tryFindCards() {
    if (installed)
        return;

    const modules = Process.enumerateModules();

    for (const m of modules) {
        if (/cardsdllzf\.dll/i.test(m.name)) {
            cardsBase = m.base;
            log("CardsDLLzf.dll gevonden @ " + cardsBase);
            installHooks();
            return;
        }
    }
}

function hookPoint(name, rva) {
    const address = cardsBase.add(rva);

    try {
        Interceptor.attach(address, {
            onEnter(args) {
                log(name + " geraakt @ " + address);
            }
        });

        log("hook " + name + " @ " + address);
    } catch (e) {
        log("hook fout " + name + ": " + e);
    }
}

function installHooks() {
    if (installed)
        return;

    installed = true;

    hookPoint(
        "EASW session gate",
        CARDS_RVAS.easwSessionGate
    );

    hookPoint(
        "EASW token gate",
        CARDS_RVAS.easwTokenGate
    );

    hookPoint(
        "auth JSON builder",
        CARDS_RVAS.jsonBuilder
    );

    hookPoint(
        "auth request start",
        CARDS_RVAS.requestStart
    );

    hookPoint(
        "auth request submit",
        CARDS_RVAS.requestSubmit
    );

    log("auth tracer actief");
}

log("passieve FUT auth tracer gestart");

tryFindCards();

setInterval(function () {
    tryFindCards();
}, 250);