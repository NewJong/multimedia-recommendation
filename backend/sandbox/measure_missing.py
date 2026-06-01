import subprocess
import statistics
import json

BASE = "http://localhost:8000"
N = 10

cases = [
    ("POST", "/cross/explain", {
        "pairs": [{"anchor_type": "movie", "anchor_id": 51, "rec_type": "game", "rec_id": 1, "score": 70}]
    }),
    ("POST", "/search (substring, ai=false)", "/search", {"q": "dark fantasy", "ai": False}),
    ("POST", "/search (AI, ai=true)",        "/search", {"q": "dark fantasy with moral choices", "ai": True}),
]


def measure(method, path, body):
    url = BASE + path
    times = []
    for _ in range(N):
        cmd = ["curl", "-s", "-o", "NUL",
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


for case in cases:
    if len(case) == 3:
        method, path, body = case
        label = path
    else:
        method, label, path, body = case
    mean, status = measure(method, path, body)
    print(f"{label:50} {mean if mean else '---':>10} {status}")
