# Що реалізовано — фактична довідка

Один плоский текст, що описує програмну реалізацію системи рекомендацій. Призначений для звірки з розділами 2.1 і 2.2 курсової роботи: дозволяє вилучити пункти, що не відповідають реалізації, або уточнити формулювання тих, що відповідають.

---

## Загальний огляд

Реалізовано web-систему рекомендацій мультимедійного контенту з трьох доменів: треки (Last.fm), фільми (TMDB), ігри (RAWG). Каталог ~313 елементів (100 + 100 + 113). Бекенд на FastAPI + PostgreSQL з розширенням pgvector. Фронтенд на Astro + React. Авторизація через Firebase. У системі присутні три типи рекомендацій: однодоменна (content-based), крос-доменна (на основі семантичних вкладень), а також соціальне порівняння смаків. Усі генеративні AI-функції побудовані на Claude Haiku 4.5.

---

## Однодоменна рекомендація — content-based filtering з TF-IDF

Кожен елемент представлений набором тегів. Для треків і ігор використано поля genres + tags, для фільмів genres + keywords. Користувач представлений сумою тегових ваг його лайків.

Формула IDF (Inverse Document Frequency):

    IDF(t) = log(N / (df(t) + 1))

де N — кількість елементів у домені, df(t) — кількість елементів, що містять тег t.

User vector u — для кожного тега, що зустрічається в лайкнутих елементах:

    u[t] = sum over liked items containing t of IDF(t)

Item vector v_i — бінарний (1, якщо item містить тег; 0 інакше).

Косинусна подібність:

    cos(u, v_i) = (u · v_i) / (||u|| × ||v_i||)

Результат — top-K елементів каталогу за спаданням cos(u, v_i), за виключенням уже вподобаних. Для фільмів застосовано min_df = 2 (тег враховується, якщо зустрічається щонайменше у 2 елементах); для треків і ігор min_df = 1.

**Колаборативна фільтрація НЕ реалізована.** Якщо у Word описано CF — це варто видалити або переформулювати на content-based filtering. Причини відсутності CF: cold-start (нові користувачі без історії), малий каталог, відсутність достатньої кількості активних користувачів для побудови user-item matrix.

**Класичний гібрид (CF + CB) також НЕ реалізований.** У системі є "hybrid scoring", але це інше — це гібрид усередині крос-доменного режиму (semantic + tag bonus), а не комбінація CF і CB.

---

## Крос-доменна рекомендація — vibe-pipeline через LLM-нормалізацію

Проблема прямого застосування embedding-моделей: різні домени мають різну лексику (плот фільму, механіки гри, музичні теги). Cosine у такому просторі низький навіть для тематично близьких пар.

Рішення — двоступенева побудова вкладень:

**Крок 1.** Для кожного елемента (трек/фільм/гра) Claude Haiku генерує vibe_text — параграф 60-90 слів у спільному experiential словнику (mood, energy, atmosphere, activity-fit, thematic abstractions), без згадок назви, плоту, механіки. Параграф зберігається у колонці vibe_text відповідної таблиці.

**Крок 2.** Параграф vibe_text вкладається у 384-вимірний вектор через sentence-transformers/all-MiniLM-L6-v2. Вектор зберігається у колонці embedding (тип vector(384), pgvector).

Семантична близькість між елементами:

    sem(a, b) = 1 - cosine_distance(emb(a), emb(b))

У pgvector cosine_distance позначається оператором <=>.

**Hybrid scoring.** До чистого семантичного сигналу додається бонус за перетин тегів (для випадків franchise-матчингу типу Spider-Man movie ↔ Spider-Man game, де семантика недостатня):

    bonus(a, b) = min(MAX_BONUS, |tags(a) ∩ tags(b)| × TAG_BONUS)
    hybrid(a, b) = min(1, sem(a, b) + bonus(a, b))

Константи: TAG_BONUS = 0.07, MAX_BONUS = 0.35.

**Pool re-rank.** Для anchor спочатку через pgvector витягується pool з K × 4 кандидатів за чистим semantic. Потім pool переранжовується у Python за hybrid scoring. Повертається top-K.

**Display calibration.** Raw cosine на vibe-text вкладеннях концентрується у діапазоні 0.55-0.95 (випадкові пари ~0.60). Тому 60% raw виглядає як "збіг", хоча це шумовий поріг. Лінійне перетворення для відображення:

    displayed_percent = clamp((hybrid - 0.5) × 2, 0, 1) × 100

Raw 0.50 → 0%, 0.75 → 50%, 0.90 → 80%, 1.00 → 100%.

---

## LLM-функції

1. **Генерація vibe_text** — одноразово при додаванні нових елементів у каталог. Скрипт backend/evaluation/cross_domain/embed_items.py.

2. **AI-пояснення крос-доменних пар** — на вимогу користувача (по кліку на кнопку у UI). Виклик: POST /cross/explain з batch-парами. Claude Haiku пише одне речення англійською мовою у плейн-стилі (max 14 слів), що пояснює спільність mood/energy/theme. Результат кешується у таблиці cross_explanations (PK: anchor_type, anchor_id, rec_type, rec_id). Повторний виклик тієї самої пари — 0 токенів LLM.

3. **LLM-інсайт порівняння смаків.** При перегляді чужого профілю генерується 3 речення (~80-100 слів): що спільне, що відрізняється, що варто спробувати з distinctive picks (елементів, що відображають унікальність смаку другого користувача). Endpoint /compare/{uid1}/{uid2}/insight.

4. **AI-режим пошуку.** Користувач описує бажане плейн-мовою ("epic late-night drive"). Claude отримує топ-40 елементів кожного домену з каталогу і обирає до 5 найрелевантніших з поясненням. Endpoint /search з параметром ai=true.

---

## Соціальне порівняння смаків

- Спільні лайки — перетин між трьома доменами окремо.
- Сумісність смаків — cosine між тегово-зваженими векторами топ-тегів двох користувачів (IDF-зваження, як у однодоменній рекомендації).
- Distinctive picks — елементи бібліотеки другого користувача з тегами, відсутніми у бібліотеці першого, ранжовані за різницею (their_vec − my_vec).
- LLM-інсайт (див. п. вище).

---

## Метрики оцінки якості рекомендацій

### Для однодоменної рекомендації

Методологія: synthetic user profile testing. Для кожного з 15 синтетичних користувачів (5 на домен × 3 домени, кожен прив'язаний до конкретного жанру) випадково семплимо SAMPLE_SIZE = 7 елементів цього жанру як training set (лайки), решта елементів того ж жанру = ground truth. Прогоняємо алгоритм, отримуємо ранжований список. Повторюємо з 5 random seeds для довірчих інтервалів (mean ± std).

Метрики @ K = 5, 10:

    Precision@K = |top_K ∩ ground_truth| / K
    Recall@K    = |top_K ∩ ground_truth| / |ground_truth|
    MRR@K       = mean(1 / rank_of_first_hit), 0 якщо немає влучень у top_K

Базові алгоритми для порівняння: popularity (топ-K за рейтингом/слухачами) і random (випадкові K).

Результат: P@10 = 0.86, лифт ~6.8× над popularity. Деталі у backend/evaluation/single_domain/results.json та chart_*.png.

### Для крос-доменної рекомендації

Крос-доменна задача не має labeled ground truth (немає розмітки "цей фільм має матчитись з цією грою"). Тому метрики іньші — порівняння нашого алгоритму проти random baseline на тих самих anchor'ах.

Методологія: для кожної з 6 спрямованих пар доменів (track→movie, track→game, movie→track, movie→game, game→track, game→movie) семплимо 25 anchor'ів і для кожного запускаємо три алгоритми: hybrid (semantic + tag bonus, production-алгоритм), semantic (pure cosine, без bonus, ablation), random (випадкові K елементів іншого домену). Повторюємо з 5 random seeds.

Метрики @ K = 1, 5, 15:

    sem_score    = mean of raw cosine in top-K
    shared_tags  = mean count of shared tags between anchor and top-K
    overlap_rate = fraction of top-K that have ≥1 shared tag with anchor

Lift = hybrid_metric / random_metric. Чим більший lift, тим сильніше алгоритм відрізняється від випадкового вибору.

Результати @ K = 5: sem_score lift 1.21×, shared_tags lift 2.64×, overlap_rate lift 2.04×. Ablation: tag-bonus додає +0.30 shared_tags при майже нульовій втраті semantic score. Ranking discrimination: top-1 score 0.744 > top-5 0.723 > top-15 0.698 — алгоритм правильно ранжує. Деталі у backend/evaluation/cross_domain/results.json та chart_*.png.

---

## Технології (просто перелік)

**Бекенд:** Python 3.10+, FastAPI, psycopg2, scikit-learn, NumPy, anthropic SDK, sentence-transformers, python-dotenv, httpx.

**База даних:** PostgreSQL (Neon), розширення pgvector. Таблиці: users, tracks, movies, games, likes, friend_requests, friendships, cross_explanations. У tracks/movies/games додано колонки embedding (vector(384)) і vibe_text (TEXT).

**Фронтенд:** Astro 6, React 19, TypeScript, Tailwind CSS v4, Firebase Auth.

**Зовнішні API:** TMDB (фільми), RAWG (ігри), Last.fm (треки).

**LLM:** Claude Haiku 4.5 (claude-haiku-4-5-20251001) — генерація vibe_text, крос-доменні пояснення, інсайт порівняння, AI-режим пошуку.

**Embedding-модель:** sentence-transformers/all-MiniLM-L6-v2 (384-dim, ~22M параметрів).

**Інструменти оцінки:** matplotlib для графіків, власні скрипти evaluation/single_domain/ та evaluation/cross_domain/.

---

## Що в Word, ймовірно, доведеться правити

1. Якщо є пункт **"Колаборативна фільтрація"** — у системі її немає. Вилучити або переформулювати на content-based filtering з TF-IDF.

2. Якщо є **"Гібридна фільтрація"** і там описано класичний гібрид CF + CB — це не реалізовано. У реалізації "hybrid" — це semantic + tag bonus у крос-доменному режимі. Або переформулювати, або вилучити.

3. Якщо у пункті про embedding описано, що вони генеруються з сирого тексту (опис, метадані) — це не так. Вони генеруються з vibe_text, який своєю чергою генерується LLM з метаданих. Двоступеневий процес.

4. Якщо згадано Word2Vec/GloVe/doc2vec — використано саме sentence-transformer (sentence-BERT family), all-MiniLM-L6-v2, 384 виміри.

5. Якщо згадано matrix factorization, SVD, deep learning з власною тренованою моделлю — нічого з цього не реалізовано. Використано лише pre-trained моделі (transfer learning).

6. Якщо метрики описано як "тест на реальних користувачах" — реалізовано synthetic users (15 personas з фіксованими жанрами). Крос-доменна оцінка — порівняння до random baseline на семплованих anchor'ах.

7. Якщо у списку технологій є Docker, Redis, Celery, Kubernetes — нічого з цього не використано. Бекенд запускається через uvicorn напряму. Кеш — простий dict у пам'яті процесу + кеш у PostgreSQL для cross_explanations.

8. Якщо описано real-time обчислення рекомендацій — не зовсім. Каталог завантажується у in-memory кеш на старті. User-specific рекомендації обчислюються при першому запиті користувача і кешуються в пам'яті процесу.
