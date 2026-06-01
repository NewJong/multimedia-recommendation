import asyncio
import time
import statistics
import aiohttp

BASE = "http://localhost:8000"
TOTAL_REQUESTS = 200
CONCURRENCY_LEVELS = [1, 5, 10, 25, 50, 100]

ENDPOINTS = [
    ("GET /movies (catalog)",                       "/movies"),
    ("GET /recommendations/{uid}/movies (TF-IDF)",  "/recommendations/test_rpg_fan/movies"),
    ("GET /cross/movie/{id} (pgvector kNN)",        "/cross/movie/51"),
]


async def one_request(session, url):
    t0 = time.perf_counter()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
            await r.read()
            return (time.perf_counter() - t0) * 1000, r.status
    except Exception:
        return (time.perf_counter() - t0) * 1000, 0


async def run_level(url, concurrency, total):
    sem = asyncio.Semaphore(concurrency)

    async def bounded(session):
        async with sem:
            return await one_request(session, url)

    connector = aiohttp.TCPConnector(limit=concurrency)
    start = time.perf_counter()
    async with aiohttp.ClientSession(connector=connector) as session:
        results = await asyncio.gather(*[bounded(session) for _ in range(total)])
    wall = time.perf_counter() - start

    latencies = [r[0] for r in results]
    ok = sum(1 for r in results if 200 <= r[1] < 400)
    err = total - ok
    latencies_sorted = sorted(latencies)
    return {
        "concurrency": concurrency,
        "total": total,
        "ok": ok,
        "err": err,
        "wall_s": wall,
        "rps": total / wall if wall else 0,
        "mean_ms": statistics.mean(latencies),
        "p50_ms": latencies_sorted[int(0.50 * (total - 1))],
        "p95_ms": latencies_sorted[int(0.95 * (total - 1))],
        "p99_ms": latencies_sorted[int(0.99 * (total - 1))],
    }


async def main():
    for label, path in ENDPOINTS:
        print(f"\n=== {label} ===")
        print(f"{'C':>4} {'OK':>4} {'ERR':>4} {'RPS':>7} {'mean':>7} {'p50':>7} {'p95':>7} {'p99':>7}")
        for c in CONCURRENCY_LEVELS:
            r = await run_level(BASE + path, c, TOTAL_REQUESTS)
            print(f"{r['concurrency']:>4} {r['ok']:>4} {r['err']:>4} "
                  f"{r['rps']:>7.1f} {r['mean_ms']:>7.0f} "
                  f"{r['p50_ms']:>7.0f} {r['p95_ms']:>7.0f} {r['p99_ms']:>7.0f}")


asyncio.run(main())
