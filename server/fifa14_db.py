from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_ROOT / "database-original"


POSITION_MAP = {
    0: "GK",
    2: "RWB",
    3: "RB",
    5: "CB",
    7: "LB",
    8: "LWB",
    10: "CDM",
    12: "RM",
    14: "CM",
    16: "LM",
    18: "CAM",
    21: "CF",
    23: "RW",
    25: "ST",
    27: "LW",
}


def _read_tsv(filename: str) -> list[dict[str, str]]:
    path = DB_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Database export not found: {path}"
        )

    # DB Master exports are UTF-16 TSV.
    with path.open(
        "r",
        encoding="utf-16",
    ) as f:
        return list(
            csv.DictReader(
                f,
                delimiter="\t",
            )
        )


# ------------------------------------------------------------------
# Raw FIFA 14 database exports
# ------------------------------------------------------------------

PLAYERS = _read_tsv("players.txt")
PLAYER_NAMES = _read_tsv("playernames.txt")
TEAM_PLAYER_LINKS = _read_tsv("teamplayerlinks.txt")
TEAMS = _read_tsv("teams.txt")
LEAGUE_TEAM_LINKS = _read_tsv("leagueteamlinks.txt")
LEAGUES = _read_tsv("leagues.txt")


# ------------------------------------------------------------------
# Basic indexes
# ------------------------------------------------------------------

PLAYER_BY_ID = {
    int(row["playerid"]): row
    for row in PLAYERS
    if row.get("playerid")
}


NAME_BY_ID = {
    int(row["nameid"]): row["name"]
    for row in PLAYER_NAMES
    if row.get("nameid")
}


TEAM_BY_ID = {
    int(row["teamid"]): row
    for row in TEAMS
    if row.get("teamid")
}


LEAGUE_BY_ID = {
    int(row["leagueid"]): row
    for row in LEAGUES
    if row.get("leagueid")
}


# ------------------------------------------------------------------
# Fast relationship indexes
#
# Previously _club_link() scanned TEAM_PLAYER_LINKS and
# LEAGUE_TEAM_LINKS again for every single player.
#
# These indexes make those lookups effectively instant.
# ------------------------------------------------------------------

TEAM_LINKS_BY_PLAYER_ID: dict[
    int,
    list[dict[str, str]],
] = {}


for row in TEAM_PLAYER_LINKS:
    player_id = int(
        row.get("playerid") or 0
    )

    if player_id <= 0:
        continue

    TEAM_LINKS_BY_PLAYER_ID.setdefault(
        player_id,
        [],
    ).append(row)


LEAGUE_LINKS_BY_TEAM_ID: dict[
    int,
    list[dict[str, str]],
] = {}


for row in LEAGUE_TEAM_LINKS:
    team_id = int(
        row.get("teamid") or 0
    )

    if team_id <= 0:
        continue

    LEAGUE_LINKS_BY_TEAM_ID.setdefault(
        team_id,
        [],
    ).append(row)


# ------------------------------------------------------------------
# Player helpers
# ------------------------------------------------------------------

def _player_name(
    player: dict[str, str],
) -> str:
    common_name_id = int(
        player.get("commonnameid") or 0
    )

    first_name_id = int(
        player.get("firstnameid") or 0
    )

    last_name_id = int(
        player.get("lastnameid") or 0
    )

    if common_name_id > 0:
        name = NAME_BY_ID.get(
            common_name_id
        )

        if name:
            return name

    first_name = NAME_BY_ID.get(
        first_name_id,
        "",
    )

    last_name = NAME_BY_ID.get(
        last_name_id,
        "",
    )

    full_name = (
        f"{first_name} {last_name}"
    ).strip()

    if full_name:
        return full_name

    return (
        f"Player {player['playerid']}"
    )


def _club_link(
    player_id: int,
) -> tuple[
    dict[str, str] | None,
    dict[str, str] | None,
]:
    links = TEAM_LINKS_BY_PLAYER_ID.get(
        player_id,
        [],
    )

    for link in links:
        team_id = int(
            link.get("teamid") or 0
        )

        league_links = (
            LEAGUE_LINKS_BY_TEAM_ID.get(
                team_id,
                [],
            )
        )

        for league_link in league_links:
            league_id = int(
                league_link.get(
                    "leagueid"
                )
                or 0
            )

            league = LEAGUE_BY_ID.get(
                league_id
            )

            if not league:
                continue

            league_name = league.get(
                "leaguename",
                "",
            )

            # Players can also have an international
            # team link. FUT base cards should use
            # their normal club.
            if (
                league_name.lower()
                == "international"
            ):
                continue

            return link, league_link

    return None, None


# ------------------------------------------------------------------
# Public player API
# ------------------------------------------------------------------

def get_player(
    player_id: int,
) -> dict[str, Any] | None:
    player = PLAYER_BY_ID.get(
        player_id
    )

    if not player:
        return None

    position_code = int(
        player.get(
            "preferredposition1"
        )
        or -1
    )

    club_link, league_link = (
        _club_link(player_id)
    )

    team_id = 0
    team_name = ""

    league_id = 0
    league_name = ""

    if club_link:
        team_id = int(
            club_link.get("teamid")
            or 0
        )

        team = TEAM_BY_ID.get(
            team_id
        )

        if team:
            team_name = team.get(
                "teamname",
                "",
            )

    if league_link:
        league_id = int(
            league_link.get(
                "leagueid"
            )
            or 0
        )

        league = LEAGUE_BY_ID.get(
            league_id
        )

        if league:
            league_name = league.get(
                "leaguename",
                "",
            )

    return {
        "playerId": player_id,

        "name":
            _player_name(player),

        "rating":
            int(
                player.get(
                    "overallrating"
                )
                or 0
            ),

        "preferredPosition":
            POSITION_MAP.get(
                position_code,
                "",
            ),

        "preferredPositionCode":
            position_code,

        "nation":
            int(
                player.get(
                    "nationality"
                )
                or 0
            ),

        "teamId":
            team_id,

        "teamName":
            team_name,

        "leagueId":
            league_id,

        "leagueName":
            league_name,
    }


def get_all_players() -> list[
    dict[str, Any]
]:
    players: list[
        dict[str, Any]
    ] = []

    for player_id in PLAYER_BY_ID:
        player = get_player(
            player_id
        )

        if not player:
            continue

        if player["rating"] <= 0:
            continue

        if player["teamId"] <= 0:
            continue

        if player["leagueId"] <= 0:
            continue

        if not player[
            "preferredPosition"
        ]:
            continue

        players.append(player)

    return players


if __name__ == "__main__":
    print(get_player(20801))