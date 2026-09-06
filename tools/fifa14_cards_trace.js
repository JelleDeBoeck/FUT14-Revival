'use strict';

console.log('[+] FIFA 14 CardsDLL auth tracer gestart');

const MODULE_NAME = 'CardsDLLzf.dll';

function hexPtr(p) {
    try {
        return p.toString();
    } catch (_) {
        return '<invalid>';
    }
}

function hookRva(module, rva, name) {
    const address = module.base.add(rva);

    console.log(
        '[+] Hook ' + name +
        ' @ ' + address +
        ' (RVA 0x' + rva.toString(16) + ')'
    );

    Interceptor.attach(address, {
        onEnter(args) {
            console.log(
                '\n[CARDS] >>> ' + name
            );

            console.log(
                '[CARDS] address=' + address
            );

            console.log(
                '[CARDS] arg0=' + hexPtr(args[0]) +
                ' arg1=' + hexPtr(args[1]) +
                ' arg2=' + hexPtr(args[2])
            );
        },

        onLeave(retval) {
            console.log(
                '[CARDS] <<< ' + name +
                ' retval=' + hexPtr(retval)
            );
        }
    });
}

function start() {
    const module = Process.findModuleByName(
        MODULE_NAME
    );

    if (module === null) {
        console.log(
            '[-] ' + MODULE_NAME +
            ' is nog niet geladen'
        );

        console.log(
            '[*] Open FUT en start dit script daarna opnieuw.'
        );

        return;
    }

    console.log(
        '[+] Module gevonden: ' +
        module.name
    );

    console.log(
        '[+] Base: ' +
        module.base
    );

    console.log(
        '[+] Size: ' +
        module.size
    );

    /*
     * RVAs uit onze FIFA 14 reference.
     * Alleen observeren — geen geheugenwijzigingen.
     */

    hookRva(
        module,
        0x00131620,
        'Auth WebService constructor'
    );

    hookRva(
        module,
        0x001316e0,
        'Auth WebService initialize'
    );

    hookRva(
        module,
        0x0015f490,
        'Auth request start'
    );

    hookRva(
        module,
        0x0015ef70,
        'Auth JSON builder'
    );

    hookRva(
        module,
        0x0015ee20,
        'Auth request submit'
    );

    hookRva(
        module,
        0x0015f2b4,
        'EASW session check'
    );

    hookRva(
        module,
        0x0015f2fa,
        'EASW token check'
    );

    console.log(
        '[+] Alle observation hooks geplaatst'
    );
}

start();