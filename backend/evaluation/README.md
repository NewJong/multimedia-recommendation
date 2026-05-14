# Recommendation System Evaluation

Експериментальна оцінка системи рекомендацій для глави диплому "Результати дослідження".

## Структура

| Файл | Призначення |
|---|---|
| `evaluate_recommendations.py` | Створює 15 синтетичних юзерів, рахує Precision@K / Recall@K / MRR@K на 5 seeds для TF-IDF vs Popularity vs Random |
| `generate_charts.py` | Генерує PNG-діаграми з результатів |
| `evaluation_results.json` | Сирі дані всіх 5 прогонів + агреговані mean ± std |
| `evaluation_chart_overall.png` | Per-domain бари (P@10, R@10, MRR@10) |
| `evaluation_chart_lift.png` | Overall + lift над baselines |

## Запуск

```bash
cd backend
python evaluation/evaluate_recommendations.py   # створює юзерів, рахує метрики
python evaluation/generate_charts.py            # генерує PNG-діаграми
```

Перший крок створить (або перестворить) **15 тестових юзерів у БД** — `Test: RPG Fan`, `Test: Metal Fan`, тощо. Кожен має 7 фокусованих лайків з одного жанру. Безпечно перезапускати — скрипт спочатку DELETE'ить попередні дані.

## Методологія

**Synthetic user profile testing з multi-seed повтором:**

1. Для кожного жанру G (5 жанрів × 3 домени = 15 personas):
   - Випадково обираємо 7 айтемів з жанром G → training set (лайки)
   - Решта айтемів з жанром G → ground truth
2. Прогоняємо алгоритми, отримуємо топ-K рекомендацій
3. Метрики:
   - **Precision@K** = `|top_K ∩ ground_truth| / K`
   - **Recall@K** = `|top_K ∩ ground_truth| / |ground_truth|`
   - **MRR@K** = `1 / position_of_first_hit` (0 якщо немає у топ-K)
4. Повторюємо з 5 різними random seeds (42, 100, 200, 300, 400)
5. Звітуємо **mean ± std deviation** для оцінки стабільності

**Алгоритми, що порівнюються:**
- **TF-IDF cosine** — наш content-based recommender (`routers/recommendations.py`)
- **Popularity baseline** — топ за рейтингом (movies/games) або listeners (tracks)
- **Random baseline** — випадковий порядок

## Поточні результати (5 seeds × 15 personas)

| Algorithm | P@10 | R@10 | MRR@10 |
|---|---|---|---|
| **TF-IDF (наш)** | **0.859 ± 0.017** | **0.694 ± 0.012** | **0.987 ± 0.016** |
| Popularity | 0.127 ± 0.014 | 0.086 ± 0.017 | 0.253 ± 0.045 |
| Random | 0.165 ± 0.025 | 0.108 ± 0.019 | 0.360 ± 0.042 |

**Lift над baselines @10:**
- Precision: 6.78× над Popularity, 5.19× над Random
- Recall: 8.10× над Popularity, 6.41× над Random
- MRR: 3.89× над Popularity, 2.74× над Random

## Що змінити для нових експериментів

Усе налаштовується константами в `evaluate_recommendations.py`:

```python
SEEDS       = [42, 100, 200, 300, 400]    # додай більше для більшої статистики
SAMPLE_SIZE = 7                            # 7 — sweet spot для нашого корпусу
K_VALUES    = [5, 10]                      # рахуємо @K для цих K
PERSONAS    = [...]                        # 15 синтетичних профілів
```

## Чистка тестових юзерів (опційно)

Тестові юзери залишаються в БД після запуску — це навмисно (для демо).
Щоб видалити:

```sql
DELETE FROM likes WHERE user_uid LIKE 'test_%';
DELETE FROM users WHERE firebase_uid LIKE 'test_%';
```
