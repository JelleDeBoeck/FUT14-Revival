from __future__ import annotations

import random
import time
from typing import Any

from server.fifa14_db import get_all_players


_PLAYER_POOL: list[dict[str, Any]] | None = None
_NEXT_ITEM_ID = 180_000_000_000


# Kleine, gecontroleerde Gold-consumable pool.
# Dit is genoeg om eerst de retail pack parser te testen.
GOLD_CONSUMABLES = [
    {
        "resourceId": 5001003,
        "cardassetid": 7,
        "cardsubtypeid": 201,
        "rating": 80,
        "rareFlag": 0,
        "rareflag": 0,
        "amount": 13,
        "bronze": 15,
        "silver": 11,
        "gold": 13,
        "itemType": "development",
        "discardValue": 80,
    },
    {
        "resourceId": 5001009,
        "cardassetid": 8,
        "cardsubtypeid": 202,
        "rating": 80,
        "rareFlag": 0,
        "rareflag": 0,
        "amount": 13,
        "bronze": 11,
        "silver": 11,
        "gold": 13,
        "itemType": "development",
        "discardValue": 80,
    },
    {
        "resourceId": 5002003,
        "cardassetid": 10,
        "cardsubtypeid": 219,
        "rating": 80,
        "rareFlag": 0,
        "rareflag": 0,
        "amount": 60,
        "bronze": 0,
        "silver": 0,
        "gold": 0,
        "itemType": "development",
        "discardValue": 80,
    },
    {
        "resourceId": 5002009,
        "cardassetid": 9,
        "cardsubtypeid": 211,
        "rating": 80,
        "rareFlag": 0,
        "rareflag": 0,
        "amount": 5,
        "bronze": 0,
        "silver": 0,
        "gold": 0,
        "itemType": "development",
        "discardValue": 80,
    },
    {
        "resourceId": 5002021,
        "cardassetid": 9,
        "cardsubtypeid": 215,
        "rating": 80,
        "rareFlag": 0,
        "rareflag": 0,
        "amount": 5,
        "bronze": 0,
        "silver": 0,
        "gold": 0,
        "itemType": "development",
        "discardValue": 80,
    },
    {
        "resourceId": 5003024,
        "cardassetid": 1,
        "cardsubtypeid": 61,
        "rating": 85,
        "rareFlag": 0,
        "rareflag": 0,
        "amount": 15,
        "bronze": 0,
        "silver": 0,
        "gold": 0,
        "itemType": "training",
        "discardValue": 80,
    },
    {
        "resourceId": 5003030,
        "cardassetid": 1,
        "cardsubtypeid": 63,
        "rating": 85,
        "rareFlag": 0,
        "rareflag": 0,
        "amount": 15,
        "bronze": 0,
        "silver": 0,
        "gold": 0,
        "itemType": "training",
        "discardValue": 80,
    },
    {
        "resourceId": 5003095,
        "cardassetid": 50,
        "cardsubtypeid": 250,
        "rating": 75,
        "rareFlag": 0,
        "rareflag": 0,
        "amount": 0,
        "bronze": 0,
        "silver": 0,
        "gold": 0,
        "itemType": "training",
        "discardValue": 80,
    },
    {
        "resourceId": 5002030,
        "cardassetid": 9,
        "cardsubtypeid": 218,
        "rating": 85,
        "rareFlag": 1,
        "rareflag": 1,
        "amount": 4,
        "bronze": 0,
        "silver": 0,
        "gold": 0,
        "itemType": "development",
        "discardValue": 160,
    },
]


def _get_player_pool() -> list[dict[str, Any]]:
    global _PLAYER_POOL

    if _PLAYER_POOL is None:
        print("[FUT PACKS] Loading FIFA 14 player pool...")

        _PLAYER_POOL = [
            player
            for player in get_all_players()
            if player["rating"] >= 75
        ]

        print(
            "[FUT PACKS] Gold player pool ready: "
            f"{len(_PLAYER_POOL)} players"
        )

    return _PLAYER_POOL


def _next_item_id() -> int:
    global _NEXT_ITEM_ID

    _NEXT_ITEM_ID += 1
    return _NEXT_ITEM_ID


def _rating_attributes(rating: int) -> list[int]:
    value = max(1, min(99, rating))

    return [
        value,
        value,
        value,
        value,
        value,
        value,
    ]


def _build_player_item(
    player: dict[str, Any],
    *,
    rare: bool = False,
) -> dict[str, Any]:
    item_id = _next_item_id()

    player_id = int(player["playerId"])
    rating = int(player["rating"])
    team_id = int(player["teamId"])
    league_id = int(player["leagueId"])
    nation = int(player["nation"])

    attributes = _rating_attributes(rating)
    rare_flag = 1 if rare else 0

    return {
        # Native-critical stream first.
        "id": item_id,
        "assetId": player_id,
        "resourceId": player_id,
        "rating": rating,
        "preferredPosition":
            player["preferredPosition"],
        "teamid": team_id,
        "leagueId": league_id,
        "nation": nation,

        "itemType": "player",
        "itemState": "free",

        "formation": "f442",

        "contract": 7,
        "fitness": 99,

        "injuryGames": 0,
        "injuryType": "none",

        "suspension": 0,
        "training": 0,

        "playStyle": 0,

        "discardValue": max(
            300,
            rating * 10,
        ),

        "lastSalePrice": 0,
        "timestamp": int(time.time()),

        "untradeable": False,

        "rareflag": rare_flag,
        "cardsubtypeid":
            1 if rare_flag else 0,

        "assists": 0,
        "lifetimeAssists": 0,

        "attributeList": [
            {
                "index": index,
                "value": value,
            }
            for index, value
            in enumerate(attributes)
        ],

        "statsList": [
            {
                "index": index,
                "value": 0,
            }
            for index in range(5)
        ],

        "lifetimeStats": [
            {
                "index": index,
                "value": 0,
            }
            for index in range(5)
        ],

        # Compatibility aliases afterwards.
        "itemId": item_id,
        "teamId": team_id,

        "name": player["name"],
        "commonName": player["name"],

        "owners": 1,
        "morale": 99,

        "playerId": player_id,

        "rareFlag": rare_flag,

        "loyaltyBonus": 1,

        # Pack/New Items pile.
        "pile": 6,

        "resourceGameYear": 2014,

        "attributeArray": attributes,

        "statsArray": [
            0,
            0,
            0,
            0,
            0,
        ],

        "lifetimeStatsArray": [
            0,
            0,
            0,
            0,
            0,
        ],

        "definitionId": player_id,

        "tradeable": True,
    }


def _build_consumable_item(
    consumable: dict[str, Any],
) -> dict[str, Any]:
    item_id = _next_item_id()

    payload = dict(consumable)

    payload.update(
        {
            "id": item_id,
            "itemId": item_id,

            "timestamp": int(time.time()),

            "lastSalePrice": 0,
            "owners": 1,

            "untradeable": False,
            "tradeable": True,

            "itemState": "free",

            # New Items / purchased pile.
            "pile": 6,

            "resourceGameYear": 2014,
        }
    )

    payload["rareflag"] = int(
        payload.get(
            "rareFlag",
            payload.get("rareflag", 0),
        )
    )

    payload["rareFlag"] = (
        payload["rareflag"]
    )

    return payload


def generate_gold_pack(
    quantity: int = 12,
) -> list[dict[str, Any]]:
    if quantity != 12:
        raise ValueError(
            "Gold Pack 5 must contain 12 items"
        )

    pool = _get_player_pool()

    selected_players = random.sample(
        pool,
        3,
    )

    # Voor deze eerste native-parser test
    # maken we de Rare gegarandeerd een
    # consumable. Later maken we rarity
    # volledig gewogen/random.
    player_items = [
        _build_player_item(
            player,
            rare=False,
        )
        for player in selected_players
    ]

    consumable_items = [
        _build_consumable_item(item)
        for item in GOLD_CONSUMABLES
    ]

    items = (
        player_items
        + consumable_items
    )

    # Retail-like reveal:
    # spelers eerst, hoogste rating eerst.
    items.sort(
        key=lambda item: (
            0
            if item.get("itemType")
            == "player"
            else 1,

            -int(
                item.get(
                    "rating",
                    0,
                )
            ),

            int(
                item.get(
                    "id",
                    0,
                )
            ),
        )
    )

    print(
        "[FUT PACKS] Generated Gold Pack: "
        f"{len(player_items)} players + "
        f"{len(consumable_items)} consumables"
    )

    print(
        "[FUT PACKS] Players: "
        + ", ".join(
            f"{item['name']} "
            f"({item['rating']})"
            for item in player_items
        )
    )

    return items