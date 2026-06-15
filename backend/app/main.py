from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, cards, collection, scan

app = FastAPI(
    title="CardTrackr API",
    description="Pokemon card scanner and collection tracker.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(scan.router, prefix="/api")
app.include_router(collection.router, prefix="/api")
app.include_router(cards.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
