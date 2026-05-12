import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import APIRouter
from database import get_conn, cached_query, _cache

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _build_recommendations(uid: str, item_type: str, items: list, tag_fields: list) -> list:
    """
    Content-based filtering via cosine similarity (User→Item).

    Крок 1. СЛОВНИК
        Зібрати всі унікальні теги/жанри з усіх айтемів домену.
        Кожен тег отримує індекс: { "rpg": 0, "open world": 1, "dark fantasy": 2, ... }
        Розмірність простору n = кількість унікальних тегів.

    Крок 2. ВЕКТОР СМАКУ КОРИСТУВАЧА  (розмір: 1 × n)
        Для кожного лайкнутого айтему — додати 1.0 до кожної тегової координати.
        Результат: зважений вектор, де більше значення = сильніша перевага.
        Приклад: лайкнув Elden Ring (RPG, Dark Fantasy, Difficult) + Dark Souls (RPG, Difficult):
            user_vec["rpg"] = 2,  user_vec["dark fantasy"] = 1,  user_vec["difficult"] = 2

    Крок 3. МАТРИЦЯ АЙТЕМІВ  (розмір: кандидати × n)
        Кожен кандидат — бінарний рядок:
            item_vec[i] = 1 якщо тег є, 0 якщо немає.

    Крок 4. КОСИНУСНА СХОЖІСТЬ
        sim(u, v) = dot(u, v) / (||u|| × ||v||)  ∈ [0, 1]

        dot(u, v)  = сума user_vec[i] × item_vec[i]  — внесок тільки спільних тегів
        ||u||      = sqrt(сума user_vec[i]²)
        ||v||      = sqrt(кількість тегів у айтему)

        × 100 → ціле число 0–100, відображається як "✦ 87%" в UI.

    Крок 5. MATCHED TAGS
        Теги, що присутні у user_vec (вага > 0) і в кандидаті,
        відсортовані за вагою спадно — топ-3 показуються як пояснення.

    Чому косинус, а не евклідова відстань?
        Косинус нечутливий до довжини вектора — юзер з 10 лайками і з 2 лайками
        отримають схожі рекомендації. Евклідова відстань штрафувала б коротший вектор.
    """
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT item_id FROM likes WHERE user_uid=%s AND item_type=%s", (uid, item_type))
    liked_ids = {r["item_id"] for r in cur.fetchall()}
    cur.close(); conn.close()

    if not liked_ids:
        return []

    vocab: dict[str, int] = {}
    for item in items:
        for field in tag_fields:
            for tag in (item.get(field) or []):
                key = tag.lower()
                if key not in vocab:
                    vocab[key] = len(vocab)

    if not vocab:
        return []

    n = len(vocab)
    idx_to_tag = {v: k for k, v in vocab.items()}

    user_vec = np.zeros(n)
    for item in items:
        if item["id"] not in liked_ids:
            continue
        for field in tag_fields:
            for tag in (item.get(field) or []):
                user_vec[vocab[tag.lower()]] += 1.0

    if not user_vec.any():
        return []

    candidates = [item for item in items if item["id"] not in liked_ids]
    if not candidates:
        return []

    item_matrix = np.zeros((len(candidates), n))
    for i, item in enumerate(candidates):
        for field in tag_fields:
            for tag in (item.get(field) or []):
                item_matrix[i, vocab[tag.lower()]] = 1.0

    scores = cosine_similarity(user_vec.reshape(1, -1), item_matrix)[0]

    top_indices = np.argsort(scores)[::-1]
    results = []
    for idx in top_indices:
        if scores[idx] <= 0 or len(results) >= 50:
            break

        item = candidates[idx]

        item_tag_indices = {
            vocab[tag.lower()]
            for field in tag_fields
            for tag in (item.get(field) or [])
            if tag.lower() in vocab
        }
        matched = sorted(
            [i for i in item_tag_indices if user_vec[i] > 0],
            key=lambda i: -user_vec[i]
        )[:3]
        matched_tags = [idx_to_tag[i].title() for i in matched]

        result = dict(item)
        result["_score"] = round(float(scores[idx]) * 100)
        result["_matched_tags"] = matched_tags
        results.append(result)

    return results


@router.get("/{uid}/tracks")
def recommend_tracks(uid: str):
    key = f"recs_track_{uid}"
    if key not in _cache:
        items = cached_query("tracks", "SELECT * FROM tracks ORDER BY listeners DESC")
        _cache[key] = _build_recommendations(uid, "track", items, ["genres", "tags"])
    return _cache[key]


@router.get("/{uid}/movies")
def recommend_movies(uid: str):
    key = f"recs_movie_{uid}"
    if key not in _cache:
        items = cached_query("movies", "SELECT * FROM movies ORDER BY rating DESC, vote_count DESC")
        _cache[key] = _build_recommendations(uid, "movie", items, ["genres", "keywords"])
    return _cache[key]


@router.get("/{uid}/games")
def recommend_games(uid: str):
    key = f"recs_game_{uid}"
    if key not in _cache:
        items = cached_query("games", "SELECT * FROM games ORDER BY rating DESC")
        _cache[key] = _build_recommendations(uid, "game", items, ["genres", "tags"])
    return _cache[key]
