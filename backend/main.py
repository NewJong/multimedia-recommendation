from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env") 

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import content, users, likes, friends, search, recommendations, compare

app = FastAPI(title="TIOKhor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],
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
