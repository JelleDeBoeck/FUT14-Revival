import struct
from datetime import datetime, timezone
from ipaddress import IPv4Address


# ============================================================
# TDF types
# ============================================================

TDF_VAR_INT = 0x0
TDF_STRING = 0x1
TDF_BLOB = 0x2
TDF_GROUP = 0x3
TDF_LIST = 0x4
TDF_MAP = 0x5
TDF_TAGGED_UNION = 0x6
TDF_VAR_INT_LIST = 0x7
TDF_OBJECT_TYPE = 0x8
TDF_OBJECT_ID = 0x9


# ============================================================
# FIRE protocol
# ============================================================

def parse_fire_header(data: bytes):
    if len(data) < 12:
        raise ValueError(
            "FIRE frame is korter dan 12 bytes"
        )

    return struct.unpack_from(
        ">HHHHBBH",
        data,
        0,
    )


def build_fire_response(
    component: int,
    command: int,
    sequence: int,
    body: bytes = b"",
) -> bytes:
    return (
        struct.pack(
            ">HHHHBBH",
            len(body),
            component,
            command,
            0,
            0x10,
            0x00,
            sequence,
        )
        + body
    )


def build_fire_notification(
    component: int,
    command: int,
    body: bytes,
) -> bytes:
    return (
        struct.pack(
            ">HHHHBBH",
            len(body),
            component,
            command,
            0,
            0x20,
            0x00,
            0,
        )
        + body
    )


# ============================================================
# TDF primitives
# ============================================================

def tdf_tag(
    tag: bytes,
    field_type: int,
) -> bytes:
    if not tag or len(tag) > 4:
        raise ValueError(
            f"TDF tag moet 1 t/m 4 bytes zijn: {tag!r}"
        )

    out = [0, 0, 0, field_type & 0xFF]
    length = len(tag)

    if length > 0:
        out[0] |= (tag[0] & 0x40) << 1
        out[0] |= (tag[0] & 0x10) << 2
        out[0] |= (tag[0] & 0x0F) << 2

    if length > 1:
        out[0] |= (tag[1] & 0x40) >> 5
        out[0] |= (tag[1] & 0x10) >> 4
        out[1] |= (tag[1] & 0x0F) << 4

    if length > 2:
        out[1] |= (tag[2] & 0x40) >> 3
        out[1] |= (tag[2] & 0x10) >> 2
        out[1] |= (tag[2] & 0x0C) >> 2
        out[2] |= (tag[2] & 0x03) << 6

    if length > 3:
        out[2] |= (tag[3] & 0x40) >> 1
        out[2] |= tag[3] & 0x1F

    return bytes(out)


def tdf_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError(
            "Negatieve varints niet ondersteund"
        )

    first = value & 0x3F
    value >>= 6

    if value:
        first |= 0x80

    result = bytearray([first])

    while value:
        current = value & 0x7F
        value >>= 7

        if value:
            current |= 0x80

        result.append(current)

    return bytes(result)


def read_tdf_varint(
    data: bytes,
    offset: int,
):
    if offset >= len(data):
        raise ValueError(
            "Geen varint-data"
        )

    first = data[offset]
    offset += 1

    value = first & 0x3F
    shift = 6

    while first & 0x80:
        if offset >= len(data):
            raise ValueError(
                "Onvolledige varint"
            )

        first = data[offset]
        offset += 1

        value |= (
            (first & 0x7F)
            << shift
        )

        shift += 7

    return value, offset


def extract_tdf_string(
    data: bytes,
    tag: bytes,
):
    marker = tdf_tag(
        tag,
        TDF_STRING,
    )

    pos = data.find(marker)

    if pos == -1:
        return None

    pos += 4

    try:
        length, pos = read_tdf_varint(
            data,
            pos,
        )
    except ValueError:
        return None

    if length <= 0:
        return ""

    raw = data[
        pos:pos + length
    ]

    if raw.endswith(b"\x00"):
        raw = raw[:-1]

    return raw.decode(
        "utf-8",
        errors="replace",
    )

def extract_tdf_string_list(
    data: bytes,
    tag: bytes,
):
    marker = tdf_tag(
        tag,
        TDF_LIST,
    )

    pos = data.find(marker)

    if pos == -1:
        return ()

    pos += 4

    if pos >= len(data):
        return ()

    element_type = data[pos]
    pos += 1

    if element_type != TDF_STRING:
        return ()

    try:
        count, pos = read_tdf_varint(
            data,
            pos,
        )
    except ValueError:
        return ()

    values = []

    for _ in range(count):
        try:
            length, pos = read_tdf_varint(
                data,
                pos,
            )
        except ValueError:
            break

        if length <= 0:
            values.append("")
            continue

        raw = data[
            pos:pos + length
        ]
        pos += length

        if raw.endswith(b"\x00"):
            raw = raw[:-1]

        values.append(
            raw.decode(
                "utf-8",
                errors="replace",
            )
        )

    return tuple(values)

def tdf_u32(
    tag: bytes,
    value: int,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_VAR_INT,
        )
        + tdf_varint(value)
    )


def tdf_u16(
    tag: bytes,
    value: int,
) -> bytes:
    return tdf_u32(
        tag,
        value,
    )


def tdf_bool(
    tag: bytes,
    value: bool,
) -> bytes:
    return tdf_u32(
        tag,
        1 if value else 0,
    )


def tdf_raw_string(
    value: str,
) -> bytes:
    encoded = value.encode(
        "utf-8"
    )

    return (
        tdf_varint(
            len(encoded) + 1
        )
        + encoded
        + b"\x00"
    )


def tdf_string(
    tag: bytes,
    value: str,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_STRING,
        )
        + tdf_raw_string(value)
    )


def tdf_blob(
    tag: bytes,
    value: bytes = b"",
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_BLOB,
        )
        + tdf_varint(
            len(value)
        )
        + value
    )


def tdf_group(
    tag: bytes,
    body: bytes,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_GROUP,
        )
        + body
        + b"\x00"
    )


def tdf_list_u32(
    tag: bytes,
    values,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_LIST,
        )
        + bytes([
            TDF_VAR_INT
        ])
        + tdf_varint(
            len(values)
        )
        + b"".join(
            tdf_varint(value)
            for value in values
        )
    )


def tdf_list_groups(
    tag: bytes,
    values,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_LIST,
        )
        + bytes([
            TDF_GROUP
        ])
        + tdf_varint(
            len(values)
        )
        + b"".join(
            value + b"\x00"
            for value in values
        )
    )

def tdf_empty_list(
    tag: bytes,
    element_type: int,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_LIST,
        )
        + bytes([element_type])
        + tdf_varint(0)
    )


def tdf_list_strings(
    tag: bytes,
    values,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_LIST,
        )
        + bytes([TDF_STRING])
        + tdf_varint(len(values))
        + b"".join(
            tdf_raw_string(value)
            for value in values
        )
    )

def tdf_map_strings(
    tag: bytes,
    values,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_MAP,
        )
        + bytes([
            TDF_STRING,
            TDF_STRING,
        ])
        + tdf_varint(
            len(values)
        )
        + b"".join(
            tdf_raw_string(key)
            + tdf_raw_string(value)
            for key, value in values
        )
    )


def tdf_map_u32(
    tag: bytes,
    values,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_MAP,
        )
        + bytes([
            TDF_VAR_INT,
            TDF_VAR_INT,
        ])
        + tdf_varint(
            len(values)
        )
        + b"".join(
            tdf_varint(key)
            + tdf_varint(value)
            for key, value in values
        )
    )


def tdf_empty_map(
    tag: bytes,
    key_type: int,
    value_type: int,
) -> bytes:
    return (
        tdf_tag(
            tag,
            TDF_MAP,
        )
        + bytes([
            key_type,
            value_type,
        ])
        + tdf_varint(0)
    )


# ============================================================
# Redirector
# ============================================================

def build_redirector_body(
    host: str = "127.0.0.1",
    port: int = 42128,
) -> bytes:
    ip_value = int(
        IPv4Address(host)
    )

    valu_group = (
        tdf_tag(
            b"VALU",
            TDF_GROUP,
        )
        + tdf_u32(
            b"IP",
            ip_value,
        )
        + tdf_u16(
            b"PORT",
            port,
        )
        + b"\x00"
    )

    return (
        tdf_tag(
            b"ADDR",
            TDF_TAGGED_UNION,
        )
        + b"\x00"
        + valu_group
        + tdf_bool(
            b"SECU",
            False,
        )
        + tdf_bool(
            b"XDNS",
            False,
        )
    )


# ============================================================
# Util.PreAuth
# ============================================================

def build_pre_auth_body() -> bytes:
    component_ids = (
        0x01,
        0x19,
        0x04,
        0x1C,
        0x07,
        0x09,
        0xF802,
        0x7800,
        0x0F,
        0x7801,
        0x7802,
        0x7803,
        0x7805,
        0x7806,
        0x07D0,
        0x0A,
        0x0B,
        0x15,
        0x081C,
        0x081D,
        2148,
        2249,
        2268,
    )

    config = tdf_map_strings(
        b"CONF",
        (
            (
                "pingPeriod",
                "30s",
            ),
            (
                "voipHeadsetUpdateRate",
                "1000",
            ),
            (
                "xlspConnectionIdleTimeout",
                "300",
            ),
        ),
    )

    qos = (
        tdf_group(
            b"BWPS",
            (
                tdf_string(
                    b"PSA",
                    "0",
                )
                + tdf_u16(
                    b"PSP",
                    0,
                )
                + tdf_string(
                    b"SNA",
                    "prod-sjc",
                )
            ),
        )
        + tdf_u16(
            b"LNP",
            1,
        )
        + tdf_empty_map(
            b"LTPS",
            TDF_STRING,
            TDF_GROUP,
        )
        + tdf_u32(
            b"SVID",
            0x45410805,
        )
    )

    return (
        tdf_bool(
            b"ANON",
            False,
        )
        + tdf_string(
            b"ASRC",
            "303107",
        )
        + tdf_list_u32(
            b"CIDS",
            component_ids,
        )
        + tdf_string(
            b"CNGN",
            "",
        )
        + tdf_group(
            b"CONF",
            config,
        )
        + tdf_string(
            b"INST",
            "fifa-2014-pc",
        )
        + tdf_bool(
            b"MINR",
            False,
        )
        + tdf_string(
            b"NASP",
            "cem_ea_id",
        )
        + tdf_string(
            b"PILD",
            "",
        )
        + tdf_string(
            b"PLAT",
            "pc",
        )
        + tdf_string(
            b"PTAG",
            "",
        )
        + tdf_group(
            b"QOSS",
            qos,
        )
        + tdf_string(
            b"RSRC",
            "303107",
        )
        + tdf_string(
            b"SVER",
            "Blaze 3.13 local FIFA 14\n",
        )
    )


# ============================================================
# Util.Ping
# ============================================================

def build_ping_body() -> bytes:
    return tdf_u32(
        b"STIM",
        int(
            datetime.now(
                timezone.utc
            ).timestamp()
        ),
    )

def build_post_auth_body(
    player_id: int = 1_000_001,
) -> bytes:
    player_sync = (
        tdf_string(
            b"ADRS",
            "127.0.0.1",
        )
        + tdf_blob(
            b"CSIG",
        )
        + tdf_string(
            b"PJID",
            "303107",
        )
        + tdf_u16(
            b"PORT",
            443,
        )
        + tdf_u32(
            b"RPRT",
            0xF,
        )
        + tdf_u32(
            b"TIID",
            0,
        )
    )

    telemetry = (
        tdf_string(
            b"ADRS",
            "127.0.0.1",
        )
        + tdf_u32(
            b"ANON",
            0,
        )
        + tdf_string(
            b"DISA",
            "",
        )
        + tdf_string(
            b"FILT",
            "-UION/****",
        )
        + tdf_u32(
            b"LOC",
            0x656E5553,
        )
        + tdf_string(
            b"NOOK",
            "",
        )
        + tdf_u16(
            b"PORT",
            42129,
        )
        + tdf_u16(
            b"SDLY",
            15000,
        )
        + tdf_string(
            b"SESS",
            "LOCAL-FIFA14-TELEMETRY",
        )
        + tdf_string(
            b"SKEY",
            "",
        )
        + tdf_u32(
            b"SPCT",
            0,
        )
        + tdf_string(
            b"STIM",
            "",
        )
    )

    ticker = (
        tdf_string(
            b"ADRS",
            "127.0.0.1",
        )
        + tdf_u16(
            b"PORT",
            8999,
        )
        + tdf_string(
            b"SKEY",
            "1000001,127.0.0.1:8999,fifa-2014-pc,0",
        )
    )

    user_options = (
        tdf_u32(
            b"TMOP",
            1,
        )
        + tdf_u32(
            b"UID",
            player_id,
        )
    )

    return (
        tdf_group(
            b"PSS",
            player_sync,
        )
        + tdf_group(
            b"TELE",
            telemetry,
        )
        + tdf_group(
            b"TICK",
            ticker,
        )
        + tdf_group(
            b"UROP",
            user_options,
        )
    )

# ============================================================
# Util.FetchClientConfig
# ============================================================

def build_fetch_config_body(
    config_id: str | None,
) -> bytes:
    configs = {
        "OSDK_CORE": (
            (
                "JOIN_GAME_TIMEOUT",
                "60000",
            ),
            (
                "OSDK_DISTBUFFERSIZE_IN",
                "32768",
            ),
            (
                "OSDK_DISTBUFFERSIZE_OUT",
                "32768",
            ),
            (
                "OSDK_KEEPALIVEINTERVAL",
                "30000",
            ),
            (
                "OSDK_MATCHUP_TIMEOUT",
                "60000",
            ),
            (
                "OSDK_MAXGAMES",
                "100",
            ),
            (
                "OSDK_MAXROOMS",
                "100",
            ),
            (
                "OSDK_PEERBUFFERSIZE",
                "32768",
            ),
            (
                "OSDK_REGISTER_PRODUCT",
                "0",
            ),
            (
                "OSDK_TICKER_COUNT",
                "0",
            ),
        ),

        "OSDK_CLIENT": (
            (
                "FUTBOOTCFGFILE_URL",
                "http://127.0.0.1:8080/futBoot.xml",
            ),
            (
                "FUT_RS4_BASE_URL",
                "http://127.0.0.1:8099/",
            ),
            (
                "FUT_URI",
                "http://127.0.0.1:8099/",
            ),
            (
                "CARDS/DIRECTED_BLAZEENV",
                "prod",
            ),
            (
                "FCC/FUT_DEPLOY_LANGUAGE",
                "en_US",
            ),
            (
                "FUT_ENABLE_MENU",
                "1",
            ),
            (
                "FUT_RS4_APIURL_PC",
                "http://127.0.0.1:8099/",
            ),
            (
                "FUT_RS4_URL_PC",
                "http://127.0.0.1:8099/",
            ),
            (
                "FUTDYNAMICMESSAGES_URL_BASE",
                "http://127.0.0.1:8099",
            ),
            (
                "FUTDYNAMICMESSAGES_URL_GET_MESSAGES",
                "/messages",
            ),
            (
                "FUTDYNAMICMESSAGES_TUTORIAL_MSG_URL",
                "/tutorials",
            ),
            (
                "FUTDYNAMICMESSAGES_REQUEST_TIMEOUT",
                "5000",
            ),
            (
                "FUTDYNAMICMESSAGES_REFRESH_INTERVAL",
                "300000",
            ),
            (
                "FUT/MODULE_BASEURL_PC",
                "http://127.0.0.1:8099/",
            ),
            (
                "FUT/SINGLE_BASEURL_PC",
                "http://127.0.0.1:8099/",
            ),
            (
                "ONLINE/NO_AUTO_SQUAD",
                "0",
            ),
            (
                "FUT/FORCE_TUTORIALS",
                "1",
            ),
            (
                "FUT/DISABLE_TUTORIALS",
                "0",
            ),
            (
                "FUT/ALWAYS_SHOW_SMART_TUTORIALS",
                "1",
            ),
            (
                "FUT/IS_RETURNING_USER",
                "0",
            ),
            (
                "FUT_SKIP_ICEBREAKER_FLOW",
                "0",
            ),
            (
                "OSDK_DDP_UPGRADE_TO_DDR_ENABLED",
                "0",
            ),
            (
                "OSDK_REGISTER_PRODUCT",
                "0",
            ),
            (
                "OSDK_TOLLBOOTH_DDP_COMMERCE_ENABLED",
                "0",
            ),
            (
                "OSDK_TOLLBOOTH_DDR_ONLINE_PASS_ENABLED",
                "0",
            ),
            (
                "OSDK_TOLLBOOTH_ONLINE_PASS_ENABLED",
                "0",
            ),
            (
                "OSDK_TOLLBOOTH_SEASON_TICKET_ENABLED",
                "0",
            ),
            (
                "OSDK_TOLLBOOTH_SHOW_SEASON_TICKET_AT_LOGIN",
                "0",
            ),
        ),

        "OSDK_NUCLEUS": (
            (
                "NUCLEUS_ADDED_URL",
                "",
            ),
            (
                "NUCLEUS_CREATE_INFO_URL",
                "",
            ),
            (
                "NUCLEUS_CREATE_URL",
                "",
            ),
            (
                "NUCLEUS_DEACTIVATED_INFO_URL",
                "",
            ),
            (
                "NUCLEUS_DUPACCT_INFO_URL",
                "",
            ),
            (
                "NUCLEUS_INCOMPLETE_URL",
                "",
            ),
            (
                "OSDK_EASW_ALLOWED_LOCALES",
                "en_US,en_GB",
            ),
            (
                "OSDK_EASW_CONNECT_RETRY_PERIOD",
                "5",
            ),
            (
                "OSDK_REGISTER_PRODUCT",
                "0",
            ),
        ),

        "OSDK_WEBOFFER": (
            (
                "FAQ_URL",
                "",
            ),
            (
                "MENU_ESPN_URL",
                "",
            ),
            (
                "MENU_WEBGM0_URL",
                "",
            ),
            (
                "MENU_WEBGM1_URL",
                "",
            ),
            (
                "MENU_WEBGM2_URL",
                "",
            ),
            (
                "NEWS_URL",
                "",
            ),
            (
                "TOSAC_URL",
                "",
            ),
            (
                "TOSA_URL",
                "",
            ),
            (
                "WEB_OFFER_URL",
                "",
            ),
        ),

        "OSDK_XMS_ABUSE_REPORTING": (
            (
                "OSDK_ABUSE_NUM_TYPES",
                "0",
            ),
            (
                "OSDK_XMS_DEFAULT_VIEW_URL",
                "",
            ),
        ),

        # These are requested during FIFA startup.
        # Empty config maps are intentional for now.
        "OSDK_TICKER": (),
        "OSDK_ABUSE_REPORTING": (),
        "OSDK_ARENA": (),
        "OSDK_ROSTER": (),
    }

    values = configs.get(
        config_id or "",
        (),
    )

    return tdf_map_strings(
        b"CONF",
        values,
    )


# ============================================================
# Authentication.OriginLogin
# ============================================================

def build_origin_login_body(
    player_id: int = 1_000_001,
) -> bytes:
    login_time = int(
        datetime.now(
            timezone.utc
        ).timestamp()
    )

    persona = (
        tdf_string(
            b"DSNM",
            "LocalFUT",
        )
        + tdf_u32(
            b"LAST",
            login_time,
        )
        + tdf_u32(
            b"PID",
            player_id,
        )
        + tdf_u32(
            b"STAS",
            0,
        )
        + tdf_u32(
            b"XREF",
            0,
        )
        + tdf_u32(
            b"XTYP",
            0,
        )
    )

    session = (
        tdf_u32(
            b"BUID",
            player_id,
        )
        + tdf_bool(
            b"FRST",
            False,
        )
        + tdf_string(
            b"KEY",
            "11229301_9b171d92cc562b293e602ee8325612e7",
        )
        + tdf_u32(
            b"LLOG",
            login_time,
        )
        + tdf_string(
            b"MAIL",
            "local@fifa14.invalid",
        )
        + tdf_group(
            b"PDTL",
            persona,
        )
        + tdf_u32(
            b"UID",
            player_id,
        )
    )

    return (
        tdf_u32(
            b"AGUP",
            0,
        )
        + tdf_string(
            b"LDHT",
            "",
        )
        + tdf_u32(
            b"NTOS",
            0,
        )
        + tdf_string(
            b"PCTK",
            "LOCAL-FIFA14-SESSION",
        )
        + tdf_string(
            b"PRIV",
            "",
        )
        + tdf_group(
            b"SESS",
            session,
        )
        + tdf_bool(
            b"SPAM",
            False,
        )
        + tdf_string(
            b"THST",
            "",
        )
        + tdf_string(
            b"TSUI",
            "",
        )
        + tdf_string(
            b"TURI",
            "",
        )
    )


# ============================================================
# UserSessions notifications
# ============================================================

def build_user_authenticated_body(
    player_id: int = 1_000_001,
    user_id: int = 1_000_001,
    display_name: str = "LocalFUT",
    locale: int = 0x656E5553,
) -> bytes:
    login_time = int(
        datetime.now(
            timezone.utc
        ).timestamp()
    )

    return (
        tdf_u32(
            b"ALOC",
            locale,
        )
        + tdf_u32(
            b"BUID",
            player_id,
        )
        + tdf_string(
            b"DSNM",
            display_name,
        )
        + tdf_bool(
            b"FRST",
            False,
        )
        + tdf_string(
            b"KEY",
            "11229301_9b171d92cc562b293e602ee8325612e7",
        )
        + tdf_u32(
            b"LAST",
            0,
        )
        + tdf_u32(
            b"LLOG",
            login_time,
        )
        + tdf_string(
            b"MAIL",
            "",
        )
        + tdf_u32(
            b"PID",
            player_id,
        )
        + tdf_u32(
            b"PLAT",
            4,
        )
        + tdf_u32(
            b"UID",
            user_id,
        )
        + tdf_u32(
            b"USTP",
            1,
        )
        + tdf_u32(
            b"XREF",
            0,
        )
    )


def build_user_added_body(
    player_id: int = 1_000_001,
    user_id: int = 1_000_001,
    display_name: str = "LocalFUT",
    locale: int = 0x656E5553,
) -> bytes:
    session_data = (
        tdf_tag(
            b"ADDR",
            TDF_TAGGED_UNION,
        )
        + b"\x7f"
        + tdf_string(
            b"BPS",
            "",
        )
        + tdf_string(
            b"CTY",
            "",
        )
        + tdf_map_u32(
            b"DMAP",
            (
                (
                    0x70001,
                    55,
                ),
                (
                    0x70002,
                    707,
                ),
            ),
        )
        + tdf_u32(
            b"HWFG",
            0,
        )
        + tdf_group(
            b"QDAT",
            (
                tdf_u32(
                    b"DBPS",
                    0,
                )
                + tdf_u32(
                    b"NATT",
                    0,
                )
                + tdf_u32(
                    b"UBPS",
                    0,
                )
            ),
        )
        + tdf_u32(
            b"UATT",
            0,
        )
    )

    user = (
        tdf_u32(
            b"AID",
            user_id,
        )
        + tdf_u32(
            b"ALOC",
            locale,
        )
        + tdf_u32(
            b"ID",
            player_id,
        )
        + tdf_string(
            b"NAME",
            display_name,
        )
    )

    return (
        tdf_group(
            b"DATA",
            session_data,
        )
        + tdf_group(
            b"USER",
            user,
        )
    )


def build_user_extended_data_body(
    user_id: int = 1_000_001,
) -> bytes:
    data = (
        tdf_string(
            b"BPS",
            "ea-sjc",
        )
        + tdf_string(
            b"CTY",
            "",
        )
        + tdf_u32(
            b"HWFG",
            0,
        )
        + tdf_u32(
            b"UATT",
            0,
        )
    )

    return (
        tdf_group(
            b"DATA",
            data,
        )
        + tdf_bool(
            b"SUBS",
            True,
        )
        + tdf_u32(
            b"USID",
            user_id,
        )
    )


# ============================================================
# FIFA 14 FUT entitlement
# ============================================================

def build_fut_entitlements_body(
    requested_groups=None,
    player_id: int = 1_000_001,
) -> bytes:
    groups = tuple(requested_groups or ())

    if not groups:
        groups = (
            "FIFA14PCBoxContent",
        )

    entitlements = []

    for index, group_name in enumerate(
        groups,
        start=1,
    ):
        entitlement = (
            tdf_string(
                b"DEVI",
                "",
            )
            + tdf_string(
                b"GDAY",
                "2013-09-01T00:00:00Z",
            )
            + tdf_string(
                b"GNAM",
                group_name,
            )
            + tdf_u32(
                b"ID",
                index,
            )
            + tdf_bool(
                b"ISCO",
                False,
            )
            + tdf_u32(
                b"PID",
                player_id,
            )
            + tdf_string(
                b"PJID",
                "FIFA14",
            )
            + tdf_u32(
                b"PRCA",
                2,
            )
            + tdf_string(
                b"PRID",
                "fifa14_pc",
            )
            + tdf_u32(
                b"STAT",
                2,
            )
            + tdf_u32(
                b"STRC",
                1,
            )
            + tdf_string(
                b"TAG",
                "FIFA14PCFUTContentUnlocks",
            )
            + tdf_string(
                b"TDAY",
                "",
            )
            + tdf_u32(
                b"TYPE",
                1,
            )
            + tdf_u32(
                b"UCNT",
                0,
            )
            + tdf_u32(
                b"VER",
                1,
            )
        )

        entitlements.append(
            entitlement
        )

    return tdf_list_groups(
        b"NLST",
        entitlements,
    )

def build_messaging_fetch_body() -> bytes:
    return tdf_u32(
        b"MCNT",
        0,
    )


def build_association_lists_body() -> bytes:
    return tdf_empty_list(
        b"LMAP",
        TDF_GROUP,
    )


def build_clubs_component_settings_body() -> bytes:
    return b"".join(
        tdf_u32(tag, 0)
        for tag in (
            b"CLDS",
            b"MXEV",
            b"MXRV",
            b"PUHR",
            b"SOVR",
            b"STRT",
        )
    )


def build_clubs_invitations_body() -> bytes:
    return tdf_empty_list(
        b"CIST",
        TDF_GROUP,
    )


def build_stats_key_scopes_body() -> bytes:
    return tdf_empty_map(
        b"KSIT",
        TDF_STRING,
        TDF_GROUP,
    )


def build_stats_groups_body() -> bytes:
    return tdf_empty_list(
        b"GRPS",
        TDF_GROUP,
    )


def build_stats_period_ids_body() -> bytes:
    return b"".join(
        tdf_u32(tag, 0)
        for tag in (
            b"DBUF",
            b"DHOU",
            b"DLY",
            b"DRET",
            b"MBUF",
            b"MDAY",
            b"MHOU",
            b"MLY",
            b"MRET",
            b"WBUF",
            b"WDAY",
            b"WHOU",
            b"WLY",
            b"WRET",
        )
    )


def build_osdk_settings_body() -> bytes:
    ticker_filter = (
        tdf_string(
            b"ID",
            "O_TKfilter",
        )
        + tdf_u32(
            b"LOCF",
            0,
        )
        + tdf_u32(
            b"TOGG",
            0,
        )
    )

    return tdf_list_groups(
        b"LSST",
        (
            ticker_filter,
        ),
    )


def build_osdk_setting_groups_body() -> bytes:
    ticker_group = (
        tdf_string(
            b"ID",
            "O_SG_TCKR",
        )
        + tdf_list_strings(
            b"LSET",
            (
                "O_TKfilter",
            ),
        )
    )

    return tdf_list_groups(
        b"LGRP",
        (
            ticker_group,
        ),
    )