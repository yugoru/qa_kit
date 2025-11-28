from fastapi import FastAPI

app = FastAPI(title="SOAP Stub Service")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "soap-stub"}
