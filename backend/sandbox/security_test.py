import subprocess
import json
import tempfile
import os
import urllib.parse

BASE = "http://localhost:8000"


def curl(args):
    r = subprocess.run(["curl", "-s", "-o", "-", "-w", "\nHTTP_CODE:%{http_code}", *args],
                       capture_output=True, text=True, timeout=30)
    body = r.stdout
    code = "?"
    if "HTTP_CODE:" in body:
        body, code = body.rsplit("HTTP_CODE:", 1)
        code = code.strip()
    return body[:400], code


print("=== SQL injection in /users/search (q=' OR '1'='1)")
q = urllib.parse.quote("' OR '1'='1")
b, c = curl([f"{BASE}/users/search?q={q}"])
print(f"HTTP {c}, body: {b!r}")

print("\n=== SQL injection in path /likes/{uid} (uid contains ;DROP TABLE)")
uid = urllib.parse.quote("test_rpg_fan';DROP TABLE users;--")
b, c = curl([f"{BASE}/likes/{uid}"])
print(f"HTTP {c}, body: {b!r}")

print("\n=== Malformed POST /search (no q)")
b, c = curl(["-X", "POST", "-H", "Content-Type: application/json",
             "-d", json.dumps({"invalid": "x"}), f"{BASE}/search"])
print(f"HTTP {c}, body: {b!r}")

print("\n=== Wrong type in /cross/explain (score=string)")
b, c = curl(["-X", "POST", "-H", "Content-Type: application/json",
             "-d", json.dumps({"pairs": [{"anchor_type": "movie", "anchor_id": 51,
                                          "rec_type": "game", "rec_id": 1, "score": "abc"}]}),
             f"{BASE}/cross/explain"])
print(f"HTTP {c}, body: {b!r}")

print("\n=== CORS preflight evil origin")
r = subprocess.run(["curl", "-s", "-D", "-", "-o", "NUL", "-X", "OPTIONS",
                    "-H", "Origin: http://evil.com",
                    "-H", "Access-Control-Request-Method: GET",
                    f"{BASE}/movies"], capture_output=True, text=True)
first_line = r.stdout.split("\n")[0]
allow_origin = [l for l in r.stdout.split("\n") if "access-control-allow-origin" in l.lower()]
print(f"Status: {first_line}, allow-origin header present: {bool(allow_origin)}")

print("\n=== CORS preflight allowed origin")
r = subprocess.run(["curl", "-s", "-D", "-", "-o", "NUL", "-X", "OPTIONS",
                    "-H", "Origin: http://localhost:4321",
                    "-H", "Access-Control-Request-Method: GET",
                    f"{BASE}/movies"], capture_output=True, text=True)
first_line = r.stdout.split("\n")[0]
allow_origin = [l for l in r.stdout.split("\n") if "access-control-allow-origin" in l.lower()]
print(f"Status: {first_line}, allow-origin: {allow_origin}")

print("\n=== Oversize payload (50KB)")
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump({"q": "x" * 50000, "ai": False}, f)
    tmp = f.name
try:
    b, c = curl(["-X", "POST", "-H", "Content-Type: application/json",
                 "--data-binary", f"@{tmp}", f"{BASE}/search"])
    print(f"HTTP {c}, body length: {len(b)}, first 150: {b[:150]!r}")
finally:
    os.unlink(tmp)

print("\n=== Non-existent uid /likes/<fake>")
b, c = curl([f"{BASE}/likes/this_user_does_not_exist_xyz"])
print(f"HTTP {c}, body: {b!r}")

print("\n=== XSS-like payload as search query (should be stored/returned as-is)")
xss = "<script>alert(1)</script>"
b, c = curl(["-X", "POST", "-H", "Content-Type: application/json",
             "-d", json.dumps({"q": xss, "ai": False}), f"{BASE}/search"])
print(f"HTTP {c}, body first 200: {b[:200]!r}")
