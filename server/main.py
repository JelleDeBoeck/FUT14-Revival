from fastapi import FastAPI

from server.bootstrap import router as bootstrap_router
from server.fut.auth import router as auth_router


app = FastAPI(title="FUT14 Revival")

app.include_router(bootstrap_router)
app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "project": "FUT14 Revival",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }