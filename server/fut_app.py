import copy
import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response

from server.fut.auth import router as auth_router

from server.fifa14_db import get_player

from server.fut.packs.catalog import purchase_group_response

from server.fut.packs.generator import generate_gold_pack

app = FastAPI(title="FUT14 Revival API")

# /ut/auth
app.include_router(auth_router)


# ============================================================
# Constants
# ============================================================

ICEBREAKER_PATH = Path(__file__).with_name(
    "icebreakerpacklist.local.json"
)

PERSONA_ID = 1000001
USER_ID = 1000001
PERSONA_NAME = "LocalFUT"

LOCAL_CLUB_NAME = "Local FUT"
LOCAL_CLUB_ABBR = "LFT"

LOCAL_BADGE_ID = 241
LOCAL_TEAM_ID = 241

STARTER_SQUAD_ID = 1
STARTER_ITEM_BASE = 170_000_000_000


SQUAD_POSITIONS = [
    "ST",
    "ST",
    "LM",
    "CM",
    "CM",
    "RM",
    "LB",
    "CB",
    "CB",
    "RB",
    "GK",
    "SUB",
    "SUB",
    "SUB",
    "SUB",
    "SUB",
    "SUB",
    "SUB",
    "RES",
    "RES",
    "RES",
    "RES",
    "RES",
]


# ============================================================
# Local FUT state
# ============================================================

FUT_STATE: dict[str, Any] = {
    "club_created": False,
    "starter_pack_claimed": False,

    "club_name": LOCAL_CLUB_NAME,
    "club_abbr": LOCAL_CLUB_ABBR,
    "badge_id": LOCAL_BADGE_ID,
    "team_id": LOCAL_TEAM_ID,

    "active_squad_id": 0,
    "formation": "f442",
    "squad_name": "Local XI",
    "chemistry": 0,
    "star_rating": 0,
    "players": [],

    # Items uit de laatst geopende pack.
    # FIFA haalt deze na de purchase opnieuw
    # op via GET /purchased/items.
    "purchased_items": [],
    "club_items": [],

    "clientdata": {
        "tutorialpopups": {},
        "userHubData": {},
        "managerquest": {},
    },
}

# ============================================================
# FUT World Cup state
# ============================================================

WC_STATE: dict[str, Any] = {
    # WC is bewust volledig gescheiden van normal FUT.
    #
    # Geen normal-FUT Icebreaker spelers of Gold cards
    # mogen automatisch in deze state terechtkomen.
    "club_created": False,
    "starter_pack_claimed": False,

    "club_name": LOCAL_CLUB_NAME,
    "club_abbr": LOCAL_CLUB_ABBR,
    "badge_id": 0,
    "team_id": 0,

    "active_squad_id": 1,
    "formation": "f442",
    "squad_name": "World Cup",
    "chemistry": 0,
    "star_rating": 0,
    "players": [],

    "purchased_items": [],
    "club_items": [],

    # WC-specifieke progression.
    # De precieze wire-contracten vullen we pas in
    # wanneer FIFA ze daadwerkelijk opvraagt.
    "support_nation": None,
    "first_time_complete": False,

    # Python-only onboarding bridge:
    # first /squad/active stays empty, then server arms the 23-player squad
    # for the next squad read without using Frida/JS intervention.
    "starter_active_seen": False,

    "clientdata": {
        "tutorialpopups": {},
        "userHubData": {},
        "managerquest": {},
    },
}


def is_world_cup_request(
    request: Request,
) -> bool:
    return (
        request.query_params
        .get("skuMode", "")
        .upper()
        == "WC"
    )


def state_for_request(
    request: Request,
) -> dict[str, Any]:
    if is_world_cup_request(request):
        return WC_STATE

    return FUT_STATE

@app.middleware("http")
async def debug_request_mode(request: Request, call_next):
    path = request.url.path
    query = request.url.query

    if path.startswith("/ut/"):
        wc = is_world_cup_request(request)

        print()
        print("=" * 90)
        print(
            f"[REQUEST] {request.method} {path}"
            + (f"?{query}" if query else "")
        )
        print(f"[REQUEST] WC_BY_QUERY={wc}")

        try:
            body = await request.body()

            if body:
                try:
                    body_text = body.decode(
                        "utf-8",
                        errors="replace",
                    )
                except Exception:
                    body_text = repr(body)

                print(
                    "[REQUEST BODY] "
                    + body_text[:4000]
                )
        except Exception as exc:
            print(
                f"[REQUEST BODY ERROR] {exc}"
            )

    response = await call_next(request)

    if path.startswith("/ut/"):
        print(
            f"[RESPONSE] {response.status_code} "
            f"{request.method} {path}"
        )
        print("=" * 90)

    return response

# ============================================================
# Helpers
# ============================================================

def bounded_int(
    value: Any,
    default: int = 0,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default

    if minimum is not None:
        result = max(minimum, result)

    if maximum is not None:
        result = min(maximum, result)

    return result


def load_icebreaker_fixture() -> dict[str, Any]:
    document = json.loads(
        ICEBREAKER_PATH.read_text(
            encoding="utf-8"
        )
    )

    packs = document.get("packList")

    if not isinstance(packs, list):
        raise RuntimeError(
            "Icebreaker packList ontbreekt"
        )

    if len(packs) != 4:
        raise RuntimeError(
            "Icebreaker packList moet 4 packs bevatten"
        )

    return document


def validate_icebreaker_pack(
    pack: dict[str, Any],
) -> None:
    required_arrays = [
        "squad",
        "teamId",
        "Rating",
        "Rare",
        "playStyle",
        "Attribute1",
        "Attribute2",
        "Attribute3",
        "Attribute4",
        "Attribute5",
        "Attribute6",
    ]

    for key in required_arrays:
        values = pack.get(key)

        if not isinstance(values, list):
            raise RuntimeError(
                f"{key} is geen array"
            )

        if len(values) != 23:
            raise RuntimeError(
                f"{key} moet 23 values bevatten"
            )

    for resource_id in pack["squad"]:
        if (
            not isinstance(resource_id, int)
            or resource_id <= 0
        ):
            raise RuntimeError(
                "Ongeldige player resourceId"
            )


def build_starter_player(
    pack: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    asset_id = int(pack["squad"][index])

    item_id = (
        STARTER_ITEM_BASE
        + index
        + 1
    )

    db_player = get_player(asset_id)

    # Gebruik waar mogelijk de originele FIFA 14 database.
    # De Icebreaker fixture blijft fallback zodat een ontbrekende
    # DB-record niet meteen de hele onboarding sloopt.
    if db_player:
        rating = bounded_int(
            db_player.get("rating"),
            50,
            minimum=1,
            maximum=99,
        )

        preferred_position = str(
            db_player.get("preferredPosition")
            or ""
        )

        team_id = bounded_int(
            db_player.get("teamId"),
            0,
            minimum=0,
        )

        league_id = bounded_int(
            db_player.get("leagueId"),
            0,
            minimum=0,
        )

        nation = bounded_int(
            db_player.get("nation"),
            0,
            minimum=0,
        )

        player_name = str(
            db_player.get("name")
            or ""
        )

    else:
        slot_position = SQUAD_POSITIONS[index]

        rating = bounded_int(
            pack["Rating"][index],
            50,
            minimum=1,
            maximum=99,
        )

        preferred_position = (
            "CM"
            if slot_position in {"SUB", "RES"}
            else slot_position
        )

        team_id = bounded_int(
            pack["teamId"][index],
            0,
            minimum=0,
        )

        league_id = 0
        nation = 0
        player_name = ""

    rare_flag = bounded_int(
        pack["Rare"][index],
        0,
        minimum=0,
    )

    play_style = bounded_int(
        pack["playStyle"][index],
        0,
        minimum=0,
    )

    attributes = [
        bounded_int(
            pack[f"Attribute{number}"][index],
            rating,
            minimum=0,
            maximum=99,
        )
        for number in range(1, 7)
    ]

    item_data = {
        "id": item_id,
        "itemId": item_id,

        "assetId": asset_id,
        "resourceId": asset_id,
        "playerId": asset_id,
        "definitionId": asset_id,

        "name": player_name,
        "commonName": player_name,

        "rating": rating,

        "preferredPosition": preferred_position,

        "teamid": team_id,
        "teamId": team_id,

        "leagueId": league_id,
        "nation": nation,

        "itemType": "player",
        "itemState": "free",

        "formation": str(
            pack.get("formation")
            or "f442"
        ),

        "contract": 99,
        "fitness": 99,
        "morale": 99,

        "injuryGames": 0,
        "injuryType": "none",
        "suspension": 0,
        "training": 0,

        "playStyle": play_style,

        "discardValue": 0,
        "lastSalePrice": 0,

        "timestamp": 1,

        "untradeable": True,

        "rareflag": rare_flag,
        "rareFlag": rare_flag,

        "cardsubtypeid":
            1 if rare_flag else 0,

        "owners": 1,
        "loyaltyBonus": 1,

        "pile": 7,

        "resourceGameYear": 2014,

        "assists": 0,
        "lifetimeAssists": 0,

        "attributeList": [
            {
                "index": attribute_index,
                "value": attribute_value,
            }
            for (
                attribute_index,
                attribute_value,
            )
            in enumerate(attributes)
        ],

        "attributeArray": attributes,

        "statsList": [
            {
                "index": stat_index,
                "value": 0,
            }
            for stat_index in range(5)
        ],

        "statsArray": [
            0,
            0,
            0,
            0,
            0,
        ],

        "lifetimeStats": [
            {
                "index": stat_index,
                "value": 0,
            }
            for stat_index in range(5)
        ],

        "lifetimeStatsArray": [
            0,
            0,
            0,
            0,
            0,
        ],
    }

    return {
        "index": index,
        "itemData": item_data,
        "kitNumber": 0,
    }


def provision_starter_club() -> None:
    if FUT_STATE["starter_pack_claimed"]:
        return

    fixture = (
        load_icebreaker_fixture()
    )

    # Reference implementation gebruikt
    # deterministic packList[1] voor de
    # persistent starter squad.
    pack = fixture["packList"][1]

    validate_icebreaker_pack(pack)

    players = [
        build_starter_player(
            pack,
            index,
        )
        for index in range(23)
    ]

    ratings = [
        bounded_int(
            rating,
            0,
            minimum=0,
            maximum=99,
        )
        for rating in pack["Rating"]
    ]

    FUT_STATE["club_created"] = True
    FUT_STATE["starter_pack_claimed"] = True

    FUT_STATE["club_name"] = (
        LOCAL_CLUB_NAME
    )
    FUT_STATE["club_abbr"] = (
        LOCAL_CLUB_ABBR
    )
    FUT_STATE["badge_id"] = (
        LOCAL_BADGE_ID
    )
    FUT_STATE["team_id"] = (
        LOCAL_TEAM_ID
    )

    FUT_STATE["active_squad_id"] = (
        STARTER_SQUAD_ID
    )

    FUT_STATE["formation"] = str(
        pack.get("formation")
        or "f442"
    )

    FUT_STATE["squad_name"] = (
        "Local XI"
    )

    FUT_STATE["players"] = players

    FUT_STATE["chemistry"] = 0

    FUT_STATE["star_rating"] = (
        int(
            sum(ratings)
            / len(ratings)
        )
        if ratings
        else 0
    )

    print(
        "[FUT] provisioned "
        "Local FUT / Local XI "
        f"formation={FUT_STATE['formation']} "
        f"players={len(players)}"
    )


def club_document(
    state: dict[str, Any] = FUT_STATE,
) -> dict[str, Any]:
    return {
        "year": "2014",

        "assetId": 1,

        "teamId":
            state["team_id"],

        "lastAccessTime": 0,

        "platform": "pc",

        "clubName":
            state["club_name"],

        "clubAbbr":
            state["club_abbr"],

        "established": 2014,

        "divisionOnline": 10,

        "badgeId":
            state["badge_id"],

        "skuAccessList": {
            "FFA14PC": 0,
        },
    }


def squad_detail(
    state: dict[str, Any] = FUT_STATE,
) -> dict[str, Any]:
    if not state["club_created"]:
        return {}

    players = copy.deepcopy(
        state["players"]
    )

    captain = 0

    for player in players[:11]:
        item_data = player.get(
            "itemData",
            {},
        )

        item_id = bounded_int(
            item_data.get(
                "id",
                item_data.get(
                    "itemId",
                    0,
                ),
            ),
            0,
        )

        if item_id > 0:
            captain = item_id
            break

    rating = bounded_int(
        state["star_rating"],
        0,
        minimum=0,
        maximum=100,
    )

    return {
        "id":
            state[
                "active_squad_id"
            ],

        "squadId":
            state[
                "active_squad_id"
            ],

        "personaId":
            PERSONA_ID,

        "squadName":
            state["squad_name"],

        "formation":
            state["formation"],

        "active": True,

        "changed": False,

        "captain": captain,

        "chemistry": bounded_int(
            state["chemistry"],
            0,
            minimum=0,
            maximum=100,
        ),

        "starRating": rating,

        "rating": rating,

        "valid": True,

        "newsquad": 0,

        "kicktakers": [],

        "tactics": [],

        "dreamSquad": False,

        "custom": "",

        "manager": [],

        "actives": [],

        "players": players,
    }


def compact_squad_record(
    state: dict[str, Any] = FUT_STATE,
) -> dict[str, Any]:
    detail = squad_detail(state)

    return {
        "id": bounded_int(
            detail.get(
                "id",
                detail.get(
                    "squadId",
                    0,
                ),
            ),
            0,
        ),

        "personaId": bounded_int(
            detail.get("personaId"),
            0,
        ),

        "squadName": str(
            detail.get("squadName")
            or "Local XI"
        ),

        "formation": str(
            detail.get("formation")
            or "f442"
        ),

        "active": bool(
            detail.get(
                "active",
                False,
            )
        ),

        "changed": bool(
            detail.get(
                "changed",
                False,
            )
        ),

        "chemistry": bounded_int(
            detail.get("chemistry"),
            0,
        ),

        "starRating": bounded_int(
            detail.get(
                "starRating",
                detail.get(
                    "rating",
                    0,
                ),
            ),
            0,
        ),

        "rating": bounded_int(
            detail.get(
                "rating",
                detail.get(
                    "starRating",
                    0,
                ),
            ),
            0,
        ),

        "valid": bool(
            detail.get(
                "valid",
                True,
            )
        ),

        "newsquad": bounded_int(
            detail.get("newsquad"),
            0,
        ),
    }


def save_squad_document(
    squad_id: int,
    document: dict[str, Any],
    state: dict[str, Any] = FUT_STATE,
) -> dict[str, Any]:
    if not state["club_created"]:
        raise HTTPException(
            status_code=404,
            detail="No FUT club exists",
        )

    if (
        squad_id
        != state[
            "active_squad_id"
        ]
    ):
        raise HTTPException(
            status_code=404,
            detail="Unknown squad",
        )

    if "squadName" in document:
        value = document.get(
            "squadName"
        )

        if (
            isinstance(value, str)
            and value.strip()
        ):
            state["squad_name"] = (
                value.strip()[:32]
            )

    if "formation" in document:
        value = document.get(
            "formation"
        )

        if (
            isinstance(value, str)
            and value.strip()
        ):
            state["formation"] = (
                value.strip()
            )

    if "chemistry" in document:
        state["chemistry"] = (
            bounded_int(
                document.get(
                    "chemistry"
                ),
                state[
                    "chemistry"
                ],
                minimum=0,
                maximum=100,
            )
        )

    if "starRating" in document:
        state[
            "star_rating"
        ] = bounded_int(
            document.get(
                "starRating"
            ),
            state[
                "star_rating"
            ],
            minimum=0,
            maximum=100,
        )

    elif "rating" in document:
        state[
            "star_rating"
        ] = bounded_int(
            document.get(
                "rating"
            ),
            state[
                "star_rating"
            ],
            minimum=0,
            maximum=100,
        )

    players = document.get(
        "players"
    )

    if players is None:
        return squad_detail(state)

    if not isinstance(
        players,
        list,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Squad players "
                "must be an array"
            ),
        )

    owned_items: dict[
        int,
        dict[str, Any],
    ] = {}

    for current in (
        state["players"]
    ):
        if not isinstance(
            current,
            dict,
        ):
            continue

        item_data = current.get(
            "itemData",
            {},
        )

        if not isinstance(
            item_data,
            dict,
        ):
            continue

        item_id = bounded_int(
            item_data.get(
                "id",
                item_data.get(
                    "itemId",
                    0,
                ),
            ),
            0,
        )

        if item_id > 0:
            owned_items[item_id] = (
                copy.deepcopy(
                    current
                )
            )

    incoming_players: dict[
        int,
        dict[str, Any],
    ] = {}

    recognized_count = 0

    for entry in players:
        if not isinstance(
            entry,
            dict,
        ):
            continue

        index = bounded_int(
            entry.get("index"),
            -1,
        )

        if not (
            0 <= index < 23
        ):
            continue

        item_data = entry.get(
            "itemData",
            {},
        )

        if not isinstance(
            item_data,
            dict,
        ):
            item_data = {}

        item_id = bounded_int(
            item_data.get(
                "id",
                item_data.get(
                    "itemId",
                    0,
                ),
            ),
            0,
        )

        owned_player = (
            owned_items.get(
                item_id
            )
        )

        if owned_player is not None:
            owned_player[
                "index"
            ] = index

            owned_player[
                "kitNumber"
            ] = bounded_int(
                entry.get(
                    "kitNumber",
                    owned_player.get(
                        "kitNumber",
                        0,
                    ),
                ),
                0,
                minimum=0,
                maximum=99,
            )

            incoming_players[
                index
            ] = owned_player

            recognized_count += 1

        else:
            incoming_players[
                index
            ] = {
                "index": index,
                "itemData": {
                    "id": 0,
                },
                "kitNumber":
                    bounded_int(
                        entry.get(
                            "kitNumber",
                            0,
                        ),
                        0,
                        minimum=0,
                        maximum=99,
                    ),
            }

    existing_nonzero = len(
        owned_items
    )

    # FIFA can briefly send a sparse squad while
    # card ItemData is resolving. Don't destroy
    # our valid squad with that transient state.
    if (
        existing_nonzero >= 11
        and recognized_count < 11
    ):
        print(
            "[FUT] ignored sparse "
            "squad refresh "
            f"recognized="
            f"{recognized_count} "
            f"existing="
            f"{existing_nonzero}"
        )

        return squad_detail(state)

    normalized_players = []

    for index in range(23):
        player = (
            incoming_players.get(
                index
            )
        )

        if player is None:
            player = {
                "index": index,
                "itemData": {
                    "id": 0,
                },
                "kitNumber": 0,
            }

        player["index"] = index

        normalized_players.append(
            player
        )

    state[
        "players"
    ] = normalized_players

    print(
        "[FUT] squad saved "
        f"id={squad_id} "
        f"recognized="
        f"{recognized_count}/23 "
        f"formation="
        f"{state['formation']}"
    )

    return squad_detail(state)


# ============================================================
# Health
# ============================================================

@app.get("/health")
def health():
    return {
        "service": "fut-api",
        "status": "ok",
    }

def reset_wc_session() -> None:
    WC_STATE["club_created"] = False
    WC_STATE["starter_pack_claimed"] = False

    WC_STATE["club_name"] = LOCAL_CLUB_NAME
    WC_STATE["club_abbr"] = LOCAL_CLUB_ABBR
    WC_STATE["badge_id"] = 0
    WC_STATE["team_id"] = 0

    WC_STATE["active_squad_id"] = 1
    WC_STATE["formation"] = "f442"
    WC_STATE["squad_name"] = "World Cup"
    WC_STATE["chemistry"] = 0
    WC_STATE["star_rating"] = 0

    WC_STATE["players"] = []
    WC_STATE["purchased_items"] = []
    WC_STATE["club_items"] = []

    WC_STATE["support_nation"] = None
    WC_STATE["first_time_complete"] = False
    WC_STATE["starter_active_seen"] = False

    WC_STATE["clientdata"] = {
        "tutorialpopups": {},
        "userHubData": {},
        "managerquest": {},
    }

    print("[WC-RESET] fresh WC session")

# ============================================================
# Account info
# ============================================================

@app.get(
    "/ut/game/fifa14/user/accountinfo"
)
def account_info():
    return {
        "userAccountInfo": {
            "personas": [
                {
                    "personaId":
                        PERSONA_ID,

                    "personaName":
                        PERSONA_NAME,

                    "returningUser":
                        (
                            1
                            if FUT_STATE[
                                "club_created"
                            ]
                            else 0
                        ),

                    "onlineAccess":
                        True,

                    "trial":
                        False,

                    "userState":
                        None,

                    "userClubList":
                        (
                            [
                                club_document()
                            ]
                            if FUT_STATE[
                                "club_created"
                            ]
                            else []
                        ),

                    "trialFree":
                        False,
                }
            ]
        }
    }


# ============================================================
# Phishing / trusted device
# ============================================================

# BELANGRIJK:
# deze lege response is de versie waarmee
# jouw captain chooser/lobby bewezen werkt.
@app.get(
    "/ut/game/fifa14/phishing/trusteddevice"
)
def phishing_trusted_device(
    deviceId: str = "",
):
    return {}


@app.get(
    "/ut/game/fifa14/phishing/question"
)
def phishing_question(
    response: Response,
    deviceId: str = "",
):
    return {
        "question": 0,
        "attempts": 5,
        "recoverAttempts": 20,
    }


@app.get(
    "/ut/game/fifa14/phishing"
)
def phishing_question_legacy(
    response: Response,
    deviceId: str = "",
):
    return {
        "question": 0,
        "attempts": 5,
        "recoverAttempts": 20,
    }


@app.post(
    "/ut/game/fifa14/phishing/validate"
)
def phishing_validate(
    response: Response,
    deviceId: str = "",
    answer: str = "",
):
    token = (
        "LOCAL-FIFA14-PHISHING"
    )

    response.set_cookie(
        key="FUTWebPhishing",
        value=token,
        path="/",
        httponly=True,
    )

    return {
        "debug":
            "Answer is correct.",

        "string":
            "OK",

        "code":
            "200",

        "reason":
            "Answer is correct.",

        "token":
            token,
    }


# ============================================================
# FUT settings
# ============================================================

@app.get(
    "/ut/game/fifa14/settings"
)
def fut_settings(
    request: Request,
):
    return {
        "maximumTradePileSize":
            30,

        "getOperationTimeoutSec":
            300,

        "clubCreateThreshold":
            0,

        "fifaPointsCancelTransactionFix":
            1,

        "tokenRedemptionEnabled":
            0,

        "enableWorldCupMode":
            1
            if is_world_cup_request(request)
            else 0,
    }


# ============================================================
# Localization
# ============================================================

@app.get(
    "/fut/loc/PC/leaderboards.ENG_US.xml"
)
def leaderboards_localization():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<message_set target="fut-leaderboards-locstrings">
  <locstring id="FUT_IB_CAPTAINNAME_0">FALCAO</locstring>
  <locstring id="FUT_IB_CAPTAINNAME_1">MESSI</locstring>
  <locstring id="FUT_IB_CAPTAINNAME_2">EL SHAARAWY</locstring>
  <locstring id="FUT_IB_CAPTAINNAME_3">ALABA</locstring>
  <locstring id="LeagueName_Abbr15">FUT LEAGUE</locstring>
  <locstring id="LAbbr_0">FUT</locstring>
</message_set>
"""

    return Response(
        content=xml,
        media_type=(
            "application/xml"
        ),
        headers={
            "Cache-Control":
                "no-store",
        },
    )


@app.get(
    "/fut/loc/PC/icebreaker.ENG_US.xml"
)
def icebreaker_localization():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<message_set target="fut-icebreaker-locstrings">
  <locstring id="FUT_IB_CAPTAINNAME_0">FALCAO</locstring>
  <locstring id="FUT_IB_CAPTAINNAME_1">MESSI</locstring>
  <locstring id="FUT_IB_CAPTAINNAME_2">EL SHAARAWY</locstring>
  <locstring id="FUT_IB_CAPTAINNAME_3">ALABA</locstring>
</message_set>
"""

    return Response(
        content=xml,
        media_type=(
            "application/xml"
        ),
        headers={
            "Cache-Control":
                "no-store",
        },
    )


@app.get(
    "/fut/packs/loc/storepackdescriptions.en_us.xml"
)
def store_pack_descriptions():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
        <message_set target="storepackdescriptions">
        <locstring id="LOCAL_PACK_NAME_5">Gold Pack</locstring>
        <locstring id="FUT_STORE_PACK_5_DESC">12 Gold items.</locstring>
        </message_set>
        """

    return Response(
        content=xml,
        media_type=(
            "application/xml"
        ),
        headers={
            "Cache-Control":
                "no-store",
        },
    )


# ============================================================
# Match
# ============================================================

@app.put(
    "/ut/game/fifa14/match/reset"
)
def reset_match():
    return {}


@app.put(
    "/ut/game/fifa14/match/ready"
)
def fut_match_ready():
    return {}


# ============================================================
# FUT user
# ============================================================

def provision_wc_starter_club() -> None:
    if WC_STATE["starter_pack_claimed"]:
        return

    fixture = load_icebreaker_fixture()
    pack = fixture["packList"][1]
    validate_icebreaker_pack(pack)

    players = [
        build_starter_player(pack, index)
        for index in range(23)
    ]

    ratings = [
        bounded_int(
            rating,
            0,
            minimum=0,
            maximum=99,
        )
        for rating in pack["Rating"]
    ]

    WC_STATE["starter_pack_claimed"] = True
    WC_STATE["active_squad_id"] = STARTER_SQUAD_ID
    WC_STATE["formation"] = str(
        pack.get("formation") or "f442"
    )
    WC_STATE["squad_name"] = "World Cup"

    # WC native starter baseline.
    # Dit is bewust de server-state uit de eerdere run waarin FIFA zelf
    # na LoadActiveSquad twee SaveSquad PUTs stuurde.
    WC_STATE["players"] = []
    WC_STATE["purchased_items"] = []
    WC_STATE.pop("_starter_players_pending", None)
    WC_STATE["starter_active_seen"] = False

    print(
        "[WC-NATIVE] players=0 purchased_items=0; "
        "waiting for FIFA native starter squad"
    )

    # Native WC onboarding must look internally consistent to FIFA:
    # the squad is still empty at this point, so report empty-squad ratings too.
    WC_STATE["chemistry"] = 0
    WC_STATE["star_rating"] = 0

    print(
        "[WC-NATIVE-RATING0] empty squad metadata: "
        "chemistry=0 starRating=0 rating=0"
    )

    print(
        "[WC] starter squad provisioned "
        f"players={len(players)} "
        f"new_items={len(WC_STATE['purchased_items'])} "
        f"formation={WC_STATE['formation']}"
    )


@app.api_route(
    "/ut/game/fifa14/user",
    methods=[
        "GET",
        "POST",
    ],
)
async def fut_user(
    request: Request,
):
    if (
        request.method == "POST"
        and is_world_cup_request(request)
    ):
        raw = await request.body()

        print(
            "[WC] POST /user body =",
            raw.decode(
                "utf-8",
                errors="replace",
            ),
        )

        body = json.loads(raw or b"{}")

        WC_STATE["support_nation"] = (
            body.get("clubName")
        )

        WC_STATE["team_id"] = bounded_int(
            body.get("clubName"),
            0,
            minimum=0,
        )

        WC_STATE["club_created"] = True
        WC_STATE["starter_pack_claimed"] = False
        WC_STATE["players"] = []
        WC_STATE["purchased_items"] = []
        WC_STATE["starter_active_seen"] = False
        WC_STATE.pop("_starter_players_pending", None)

        print(
            "[WC] support_nation saved =",
            WC_STATE["support_nation"],
        )

    state = state_for_request(request)
    profile_state = state

    if profile_state["club_created"]:
        return {
            "personaId":
                PERSONA_ID,

            "personaName":
                PERSONA_NAME,

            "userId":
                USER_ID,

            "created":
                0,

            "returningUser":
                0,

            "clubName":
                profile_state[
                    "club_name"
                ],

            "clubAbbr":
                profile_state[
                    "club_abbr"
                ],

            "badgeId":
                profile_state[
                    "badge_id"
                ],

            "teamId":
                profile_state[
                    "team_id"
                ],

            "activeSquadId":
                state[
                    "active_squad_id"
                ],

            "userClubList": [
                club_document(
                    profile_state
                )
            ],

            "INTRO_DONE":
                False,
        }

    return {
        "personaId":
            PERSONA_ID,

        "personaName":
            PERSONA_NAME,

        "userId":
            USER_ID,

        "created":
            0,

        "returningUser":
            0,

        "clubName":
            "",

        "clubAbbr":
            "",

        "badgeId":
            0,

        "teamId":
            0,

        "activeSquadId":
            None,

        "userClubList":
            [],
    }

# ============================================================
# Club profile update
# ============================================================

@app.put(
    "/ut/game/fifa14/user/club"
)
async def fut_update_user_club(
    request: Request,
):
    if not FUT_STATE["club_created"]:
        raise HTTPException(
            status_code=404,
            detail="No FUT club exists",
        )

    try:
        body = (
            await request.json()
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON",
        )

    if not isinstance(
        body,
        dict,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Club body "
                "must be an object"
            ),
        )

    if "clubName" in body:
        value = body["clubName"]

        if (
            isinstance(value, str)
            and value.strip()
        ):
            FUT_STATE[
                "club_name"
            ] = value.strip()

    if "clubAbbr" in body:
        value = body["clubAbbr"]

        if (
            isinstance(value, str)
            and value.strip()
        ):
            FUT_STATE[
                "club_abbr"
            ] = value.strip()

    if "badgeId" in body:
        FUT_STATE[
            "badge_id"
        ] = bounded_int(
            body["badgeId"],
            FUT_STATE[
                "badge_id"
            ],
            minimum=0,
        )

    if "teamId" in body:
        FUT_STATE[
            "team_id"
        ] = bounded_int(
            body["teamId"],
            FUT_STATE[
                "team_id"
            ],
            minimum=0,
        )

    print(
        "[FUT] club profile saved "
        f"name="
        f"{FUT_STATE['club_name']} "
        f"abbr="
        f"{FUT_STATE['club_abbr']} "
        f"badge="
        f"{FUT_STATE['badge_id']} "
        f"team="
        f"{FUT_STATE['team_id']}"
    )

    return {
        "club":
            club_document()
    }


# ============================================================
# User data
# ============================================================

@app.get(
    "/ut/game/fifa14/userdata"
)
def fut_userdata():
    return {
        "userData": []
    }


# ============================================================
# Store transaction
# ============================================================

@app.get(
    "/ut/v2/game/fifa14/store/transaction"
)
def fut_store_transaction():
    return {
        "transactionId": 0,
        "state":
            "NOTRANSACTION",
    }


# ============================================================
# Client data
# ============================================================

@app.api_route(
    "/ut/game/fifa14/clientdata/tutorialpopups",
    methods=[
        "GET",
        "PUT",
        "POST",
    ],
)
async def fut_tutorial_popups(
    request: Request,
):
    state = state_for_request(request)
    key = "tutorialpopups"

    if request.method in {
        "PUT",
        "POST",
    }:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON",
            )

        if not isinstance(
            body,
            dict,
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Client data "
                    "must be an object"
                ),
            )

        state[
            "clientdata"
        ][key] = body

    return copy.deepcopy(
        state[
            "clientdata"
        ][key]
    )


@app.get(
    "/ut/game/fifa14/clientdata/pileSize"
)
def fut_clientdata_pile_size():
    return {
        "entries": [
            {
                "key": 2,
                "value": 20000,
            },
            {
                "key": 3,
                "value": 20000,
            },
            {
                "key": 4,
                "value": 20000,
            },
        ]
    }


@app.api_route(
    "/ut/game/fifa14/clientdata/userHubData",
    methods=[
        "GET",
        "PUT",
        "POST",
    ],
)
async def fut_clientdata_user_hub_data(
    request: Request,
):
    state = state_for_request(request)
    key = "userHubData"

    if request.method in {
        "PUT",
        "POST",
    }:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON",
            )

        if not isinstance(
            body,
            dict,
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Client data "
                    "must be an object"
                ),
            )

        state[
            "clientdata"
        ][key] = body

    return copy.deepcopy(
        state[
            "clientdata"
        ][key]
    )


@app.api_route(
    "/ut/game/fifa14/clientdata/managerquest",
    methods=[
        "GET",
        "PUT",
        "POST",
    ],
)
async def fut_clientdata_managerquest(
    request: Request,
):
    state = state_for_request(request)
    key = "managerquest"

    if request.method in {
        "PUT",
        "POST",
    }:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON",
            )

        if not isinstance(
            body,
            dict,
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Client data "
                    "must be an object"
                ),
            )

        state[
            "clientdata"
        ][key] = body

    return copy.deepcopy(
        state[
            "clientdata"
        ][key]
    )


# ============================================================
# Hub
# ============================================================

@app.get(
    "/ut/game/fifa14/hub"
)
def fut_hub():
    club_players = 0

    for player in (
        FUT_STATE["players"]
    ):
        item_data = player.get(
            "itemData",
            {},
        )

        item_id = bounded_int(
            item_data.get(
                "id",
                item_data.get(
                    "itemId",
                    0,
                ),
            ),
            0,
        )

        if item_id > 0:
            club_players += 1

    return {
        "auctionCount": 0,
        "clubPlayers":
            club_players,
        "tradePileCount": 0,
        "tradePileItems": 0,
        "transferListCount": 0,
        "selling": 0,
        "sold": 0,
    }


# ============================================================
# User actions
# ============================================================

@app.get(
    "/ut/game/fifa14/user/action"
)
def fut_user_action(
    actionType: str = "",
):
    return {}


@app.post(
    "/ut/game/fifa14/user/action/{action_name}"
)
def fut_user_action_update(
    action_name: str,
    request: Request,
):
    normalized = (
        action_name
        .strip()
        .upper()
    )

    if (
        is_world_cup_request(request)
        and normalized == "CHARITY_MATCH_PLAYED"
    ):
        print("[WC] CHARITY_MATCH_PLAYED hook reached")

        provision_wc_starter_club()

        print(
            "[WC] starter items now available =",
            len(WC_STATE["purchased_items"]),
        )

    print(
        "[FUT] user action: "
        f"{normalized}"
    )

    if (
        normalized.startswith("ICEBREAKER_")
        and normalized.endswith("_SELECTED")
    ):
        provision_starter_club()

    return {}


# ============================================================
# Purchased items
# ============================================================

@app.api_route(
    "/ut/game/fifa14/purchased/items",
    methods=["GET", "POST"],
)
async def fut_purchased_items(
    request: Request,
):
    if request.method == "GET":
        items = state_for_request(request).get("purchased_items", [])

        print(
            "[FUT PACKS] Returning New Items: "
            f"{len(items)} items"
        )

        return {
            "duplicateItemIdList": [],
            "itemData": items,
            "unopenedPacks": [],
            "packList": [],
        }

    body = await request.json()

    print(
        "[FUT PACKS] Purchase request: "
        f"{body}"
    )

    pack_id = int(
        body.get("packId") or 0
    )

    currency = str(
        body.get("currency") or ""
    ).upper()

    if pack_id != 5:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported packId: "
                f"{pack_id}"
            ),
        )

    if currency != "COINS":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported currency: "
                f"{currency}"
            ),
        )

    items = generate_gold_pack(12)

    # BELANGRIJK:
    # Dezelfde items moeten na de purchase
    # beschikbaar blijven voor GET
    # /purchased/items.
    FUT_STATE["purchased_items"] = items

    transaction_id = int(time.time())

    create_pack_response = {
        "duplicateItemIdList": [],
        "itemList": items,
        "numberItems": len(items),
        "purchasedPackId": pack_id,

        "itemData": items,
        "packId": pack_id,
        "packType": pack_id,
    }

    response = {
        "packId": pack_id,
        "firstPartyStoreId": 0,

        "purchasePackType": "CARDPACK",
        "state": "PURCHASECOMPLETE",

        "transactionId": transaction_id,

        "useAuth": 0,
        "useCount": 1,
        "useTime": 0,

        "createPackResponse":
            create_pack_response,

        "purchasedPackId": pack_id,
        "purchasePackTypeId": pack_id,
        "packType": pack_id,

        "credits": 5000,
        "fifaPoints": 0,

        "itemData": items,
        "duplicateItemIdList": [],

        "unopenedPacks": 1,
    }

    print(
        "[FUT PACKS] Returning purchase response: "
        f"transaction={transaction_id}, "
        f"items={len(items)}"
    )

    return response

@app.get(
    "/ut/game/fifa14/purchased"
)
def fut_purchased():
    return {
        "duplicateItemIdList": [],
        "itemData": [],
        "unopenedPacks": [],
        "packList": [],
    }


# ============================================================
# Club
# ============================================================

@app.get(
    "/ut/game/fifa14/club/stats/staff"
)
def fut_club_staff_stats():
    return {
        "itemData": []
    }


@app.get(
    "/ut/game/fifa14/clubUser"
)
def fut_club_user(
    request: Request,
    start: int = 0,
    count: int = 50,
):
    state = state_for_request(request)

    all_items = []

    for player in state["players"]:
        item_data = player.get(
            "itemData"
        )

        if not isinstance(
            item_data,
            dict,
        ):
            continue

        item_id = bounded_int(
            item_data.get(
                "id",
                item_data.get(
                    "itemId",
                    0,
                ),
            ),
            0,
        )

        if item_id > 0:
            all_items.append(
                copy.deepcopy(
                    item_data
                )
            )

    start = max(
        0,
        start,
    )

    count = min(
        max(
            1,
            count,
        ),
        200,
    )

    page = all_items[
        start:
        start + count
    ]

    return {
        "itemData": page,
        "total":
            len(all_items),
        "count":
            len(page),
        "start":
            start,
    }


# ============================================================
# Leaderboards
# ============================================================

@app.get(
    "/ut/game/fifa14/leaderboards/options"
)
def fut_leaderboard_options():
    return {}


@app.get(
    "/ut/game/fifa14/leaderboards"
)
def fut_leaderboards():
    return {}


# ============================================================
# Icebreaker pack list
# ============================================================

@app.get(
    "/fut/packs/icebreaker/icebreakerpacklist.json"
)
def fut_icebreaker_packlist():
    return (
        load_icebreaker_fixture()
    )


# ============================================================
# Squad list
# ============================================================

@app.get(
    "/ut/game/fifa14/squad/list"
)
def fut_squad_list(
    request: Request,
):
    state = state_for_request(request)

    if not state["club_created"]:
        document = {
            "activeSquadId": 0,
            "squad": [],
        }
    else:
        document = {
            "activeSquadId": state["active_squad_id"],
            "squad": [
                compact_squad_record(state)
            ],
        }

    if is_world_cup_request(request):
        print(
            "[WC-RESPONSE] /squad/list = "
            + json.dumps(
                document,
                separators=(",", ":"),
            )
        )

    return document

# ============================================================
# Active squad
# ============================================================

@app.get(
    "/ut/game/fifa14/squad/active"
)
def fut_active_squad(
    request: Request,
    active: bool = True,
):
    state = state_for_request(request)
    document = squad_detail(state)

    if is_world_cup_request(request):
        print(
            "[WC-RESPONSE] /squad/active = "
            + json.dumps(
                document,
                separators=(",", ":"),
            )
        )

    return document


# ============================================================
# Squad detail
# ============================================================

@app.get(
    "/ut/game/fifa14/squad/{squad_id}"
)
def fut_squad_detail(
    squad_id: int,
    request: Request,
):
    state = state_for_request(request)

    if (
        not state[
            "club_created"
        ]
        or squad_id
        != state[
            "active_squad_id"
        ]
    ):
        raise HTTPException(
            status_code=404,
            detail="Unknown squad",
        )

    return squad_detail(state)


# ============================================================
# Squad update
# ============================================================

@app.put(
    "/ut/game/fifa14/squad/{squad_id}"
)
async def fut_update_squad(
    squad_id: int,
    request: Request,
):
    try:
        document = (
            await request.json()
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON",
        )

    if not isinstance(
        document,
        dict,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Squad body "
                "must be an object"
            ),
        )

    print(
        "[FUT] squad PUT "
        f"id={squad_id} "
        f"keys="
        f"{list(document.keys())}"
    )

    return save_squad_document(
        squad_id,
        document,
        state=state_for_request(request),
    )


# ============================================================
# Logout
# ============================================================

@app.post(
    "/ut/delete/auth"
)
def fut_delete_auth():
    return {}

@app.get(
    "/ut/game/fifa14/user/credits"
)
def fut_user_credits():
    coins = 5000
    points = 0

    return {
        "credits": coins,
        "fifaPoints": points,
        "bidTokens": {
            "count": 0,
            "updateTime": 0,
        },
        "currencies": [
            {
                "name": "coins",
                "funds": coins,
                "finalFunds": coins,
            },
            {
                "name": "points",
                "funds": points,
                "finalFunds": points,
            },
        ],
        "unopenedPacks": {
            "preOrderPacks": 0,
            "recoveredPacks": 0,
        },
    }

@app.get(
    "/ut/game/fifa14/store/purchasegroup/all"
)
def fut_store_purchase_groups():
    return purchase_group_response()

@app.get("/ut/game/fifa14/club/stats/newcards")
def fut_club_stats_newcards():
    stats = [
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "players",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "playersBronze",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "playersSilver",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "playersGold",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "rarePlayers",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "staff",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "stadia",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "balls",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "kits",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "badges",
            "typeValue": 0,
        },
        {
            "contextId": 5,
            "contextValue": 0,
            "type": "trophies",
            "typeValue": 0,
        },
    ]

    return {
        "stat": stats,
        "entries": stats,

        "playerCount": 0,
        "totalPlayers": 0,
        "players": 0,

        "rarePlayers": 0,

        "playersBronze": 0,
        "playersSilver": 0,
        "playersGold": 0,

        "staff": 0,
        "stadia": 0,
        "balls": 0,
        "kits": 0,
        "badges": 0,
        "trophies": 0,
    }


@app.get("/ut/game/fifa14/tradePile")
@app.get("/ut/game/fifa14/tradepile")
def fut_trade_pile():
    return {
        "auctionInfo": [],
        "duplicateItemIdList": [],

        "total": 0,

        "selling": 0,
        "sold": 0,
        "available": 0,
        "unlisted": 0,

        "tradePileCount": 0,
        "tradePileItems": 0,
        "transferListCount": 0,

        "activeCount": 0,
        "soldCount": 0,

        "credits": 5000,
        "totalCredits": 5000,
        "coins": 5000,
    }

@app.put("/ut/game/fifa14/item")
async def fut_move_item(request: Request):
    body = await request.json()

    print(
        "[FUT ITEM] PUT request: "
        f"{body}"
    )

    updates = body.get("itemData", [])

    if isinstance(updates, dict):
        updates = [updates]

    if not isinstance(updates, list):
        raise HTTPException(
            status_code=400,
            detail="itemData must be a list",
        )

    purchased_items = FUT_STATE.get(
        "purchased_items",
        [],
    )

    club_items = FUT_STATE.setdefault(
        "club_items",
        [],
    )

    results = []

    for update in updates:
        if not isinstance(update, dict):
            continue

        item_id = int(
            update.get("id")
            or update.get("itemId")
            or 0
        )

        requested_pile = str(
            update.get("pile") or ""
        ).lower()

        item = next(
            (
                candidate
                for candidate in purchased_items
                if int(candidate.get("id", 0))
                == item_id
            ),
            None,
        )

        if item is None:
            results.append(
                {
                    "id": item_id,
                    "itemId": item_id,
                    "success": False,
                    "reason": "item not found",
                }
            )
            continue

        if requested_pile != "club":
            results.append(
                {
                    "id": item_id,
                    "itemId": item_id,
                    "success": False,
                    "reason": (
                        f"unsupported pile: "
                        f"{requested_pile}"
                    ),
                }
            )
            continue

        # Native club pile = 7.
        item["pile"] = 7
        item["itemState"] = "free"
        item["untradeable"] = False
        item["tradeable"] = True

        purchased_items.remove(item)
        club_items.append(item)

        results.append(
            {
                "id": item_id,
                "itemId": item_id,
                "success": True,
                "reason": "",
                "errorCode": 0,
                "pile": 7,
            }
        )

        print(
            "[FUT ITEM] Moved to club: "
            f"id={item_id}"
        )

    return {
        "itemData": results,
    }