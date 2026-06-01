import subprocess
import statistics
import json

BASE = "http://localhost:8000"
N = 10
UID = "test_rpg_fan"
UID2 = "test_shooter_fan"
MOVIE_ID = 51
GAME_ID = 1
TRACK_ID = 26

endpoints = [
    ("GET", "/", None),
    ("GET", "/movies", None),
    ("GET", "/games", None),
    ("GET", "/tracks", None),
    ("GET", f"/movies/{MOVIE_ID}", None),
    ("GET", f"/games/{GAME_ID}", None),
    ("GET", f"/tracks/{TRACK_ID}", None),
    ("GET", "/tags/overview", None),
    ("GET", f"/users/{UID}", None),
    ("GET", "/users/search?q=test", None),
    ("GET", f"/likes/{UID}", None),
    ("GET", f"/likes/{UID}/game/{GAME_ID}", None),
    ("GET", f"/likes/friends/{UID}/game/{GAME_ID}", None),
    ("GET", f"/friends/{UID}", None),
    ("GET", f"/friends/{UID}/requests", None),
    ("GET", f"/friends/{UID}/status/{UID2}", None),
    ("GET", f"/recommendations/{UID}/movies", None),
    ("GET", f"/recommendations/{UID}/games", None),
    ("GET", f"/recommendations/{UID}/tracks", None),
    ("GET", f"/cross/movie/{MOVIE_ID}", None),
    ("GET", f"/cross/game/{GAME_ID}", None),
    ("GET", f"/cross/track/{TRACK_ID}", None),
    ("GET", f"/compare/{UID}/{UID2}/insight", None),
]


def measure(method, path, body):
    url = BASE + path
    times = []
    for _ in range(N):
        if method == "GET":
            cmd = ["curl", "-s", "-o", "NUL" if subprocess.os.name == "nt" else "/dev/null",
                   "-w", "%{time_total} %{http_code}", url]
        else:
            cmd = ["curl", "-s", "-o", "NUL" if subprocess.os.name == "nt" else "/dev/null",
                   "-w", "%{time_total} %{http_code}", "-X", "POST",
                   "-H", "Content-Type: application/json",
                   "-d", json.dumps(body), url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        out = r.stdout.strip().split()
        if len(out) < 2:
            return None, f"BAD OUTPUT: {r.stdout}"
        t_sec = float(out[0])
        code = out[1]
        if not code.startswith(("2", "3")):
            return None, f"HTTP {code}"
        times.append(t_sec * 1000)
    return statistics.mean(times), "OK"


print(f"{'METHOD':6} {'PATH':50} {'MEAN_MS':>10} STATUS")
print("-" * 80)
for method, path, body in endpoints:
    mean, status = measure(method, path, body)
    if mean is None:
        print(f"{method:6} {path:50} {'---':>10} {status}")
    else:
        print(f"{method:6} {path:50} {mean:>10.1f} {status}")
