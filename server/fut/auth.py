from datetime import datetime, timezone

from fastapi import APIRouter, Response


router = APIRouter(prefix="/ut")


@router.post("/auth")
async def authenticate(response: Response):
    sid = "FUT14-REVIVAL-LOCAL"

    now = datetime.now(timezone.utc)
    server_time = now.isoformat(timespec="seconds").replace("+00:00", "Z")

    response.headers["X-UT-SID"] = sid
    response.headers["Cache-Control"] = "no-store"

    return {
        "sid": sid,
        "serverTime": server_time,
        "lastOnlineTime": "1970-01-01T00:00:00Z",
    }