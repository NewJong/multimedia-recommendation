from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import content, users, likes, friends, search, recommendations, compare, cross

app = FastAPI(title="TIOKhor API")

_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:4321")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok"}


app.include_router(content.router)
app.include_router(users.router)
app.include_router(likes.router)
app.include_router(friends.router)
app.include_router(search.router)
app.include_router(recommendations.router)
app.include_router(compare.router)
app.include_router(cross.router)


@app.on_event("startup")
def _warmup_embedding_model():
    """Load the sentence-transformer in a background thread at startup so that
    the first /search call doesn't block for 3-5s while the model imports."""
    from threading import Thread

    def go():
        try:
            from routers.search import _get_st_model
            _get_st_model()
            print("[startup] sentence-transformer warmed")
        except Exception as e:
            print(f"[startup] embedding warmup failed: {e}")

    Thread(target=go, daemon=True).start()
