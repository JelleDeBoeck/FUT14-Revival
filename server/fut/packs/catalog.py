from __future__ import annotations

import time
from typing import Any


PACK_CATALOG = [
    {
        "id": 5,
        "packId": 5,
        "packType": 5,

        "name": "LOCAL_PACK_NAME_5",
        "description": "FUT_STORE_PACK_5_DESC",

        "displayGroup": {
            "priority": 3,
            "value": "gold",
        },

        "assetId": 3,
        "displayGroupAssetId": 3,

        "purchasePackType": "CARDPACK",

        "coins": 5000,
        "points": 100,

        "quantity": 12,

        "isPremium": False,
        "priority": 1,
        "sortPriority": 1,
    },
]


def purchase_group_response() -> dict[str, Any]:
    now = int(time.time())

    purchase = []

    for pack in PACK_CATALOG:
        purchase.append(
            {
                "actionType": "CREATEPACK",

                "assetId": pack["assetId"],
                "bonus": 0,

                "currencies": [
                    {
                        "name": "coins",
                        "funds": pack["coins"],
                        "finalFunds": pack["coins"],
                    },
                    {
                        "name": "points",
                        "funds": pack["points"],
                        "finalFunds": pack["points"],
                    },
                ],

                "name": pack["name"],
                "description": pack["description"],

                "nameToken": pack["name"],
                "descriptionToken": pack["description"],

                "displayGroup":
                    pack["displayGroup"],

                "displayGroupAssetId":
                    pack["displayGroupAssetId"],

                "displayGroupUseDefaultImage":
                    True,

                "start":
                    max(1, now - 86400),

                "end":
                    min(
                        2_147_483_647,
                        now + (86400 * 3650),
                    ),

                "firstPartyStoreId": "0",

                "id": pack["id"],
                "packId": pack["packId"],
                "packType": pack["packType"],

                "purchasePackType":
                    pack["purchasePackType"],

                "purchaseCount": 0,
                "purchaseLimit": 999999,

                "isPremium":
                    pack["isPremium"],

                "isSeasonTicketDiscount":
                    False,

                "points":
                    pack["points"],

                "priority":
                    pack["priority"],

                "quantity":
                    pack["quantity"],

                "saleType": "NONE",

                "sortPriority":
                    pack["sortPriority"],

                "state": "active",
                "unopened": False,
                "useDefaultImage": True,
                "visible": True,
            }
        )

    return {
        "purchase": purchase,
        "timestamp": now,
    }