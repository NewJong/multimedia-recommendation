from fastapi import APIRouter, HTTPException
from database import get_conn, serialize_rows, cached_query, _cache

router = APIRouter(tags=["content"])


@router.get("/tracks")
def get_tracks():
    return cached_query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")


@router.get("/tracks/{track_id}")
def get_track_by_id(track_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM tracks WHERE id = %s", (track_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Track not found")
    return serialize_rows([dict(row)])[0]


@router.get("/movies")
def get_movies():
    return cached_query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")


@router.get("/movies/{movie_id}")
def get_movie_by_id(movie_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Movie not found")
    return serialize_rows([dict(row)])[0]


@router.get("/games")
def get_games():
    return cached_query("games", "SELECT * FROM games ORDER BY rating DESC")


@router.get("/games/{game_id}")
def get_game_by_id(game_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM games WHERE id = %s", (game_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Game not found")
    return serialize_rows([dict(row)])[0]


@router.get("/tags/overview")
def get_tags_overview():
    if "tags_overview" in _cache:
        return _cache["tags_overview"]

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT tag, COUNT(*) AS cnt FROM tracks, unnest(tags) AS tag GROUP BY tag ORDER BY cnt DESC LIMIT 60")
            music_tags = [{"tag": r["tag"], "count": r["cnt"]} for r in cur.fetchall()]

            cur.execute("SELECT kw, COUNT(*) AS cnt FROM movies, unnest(keywords) AS kw GROUP BY kw ORDER BY cnt DESC LIMIT 60")
            movie_keywords = [{"tag": r["kw"], "count": r["cnt"]} for r in cur.fetchall()]

            cur.execute("SELECT tag, COUNT(*) AS cnt FROM games, unnest(tags) AS tag GROUP BY tag ORDER BY cnt DESC LIMIT 60")
            game_tags = [{"tag": r["tag"], "count": r["cnt"]} for r in cur.fetchall()]
    finally:
        conn.close()

    music_set = {t["tag"].lower() for t in music_tags}
    movie_set = {t["tag"].lower() for t in movie_keywords}
    game_set  = {t["tag"].lower() for t in game_tags}

    result = {
        "music":  music_tags,
        "movies": movie_keywords,
        "games":  game_tags,
        "overlap": {
            "music_and_games":  sorted(music_set & game_set),
            "music_and_movies": sorted(music_set & movie_set),
            "movies_and_games": sorted(movie_set & game_set),
            "all_three":        sorted(music_set & movie_set & game_set),
        },
    }
    _cache["tags_overview"] = result
    return result
