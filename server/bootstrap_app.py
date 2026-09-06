from fastapi import FastAPI

from server.bootstrap import router as bootstrap_router


app = FastAPI(title="FUT14 Revival Bootstrap")

app.include_router(bootstrap_router)


@app.get("/health")
def health():
    return {"service": "bootstrap", "status": "ok"}