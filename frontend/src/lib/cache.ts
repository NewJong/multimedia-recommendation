const TTL_MS = 5 * 60 * 1000;

interface Entry<T> { v: T; t: number }

function isBrowser() { return typeof window !== 'undefined' && typeof sessionStorage !== 'undefined'; }

export function cacheGet<T>(key: string): T | null {
  if (!isBrowser()) return null;
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const e = JSON.parse(raw) as Entry<T>;
    if (Date.now() - e.t > TTL_MS) { sessionStorage.removeItem(key); return null; }
    return e.v;
  } catch { return null; }
}

export function cacheSet<T>(key: string, value: T): void {
  if (!isBrowser()) return;
  try {
    sessionStorage.setItem(key, JSON.stringify({ v: value, t: Date.now() }));
  } catch {
  }
}

export function cacheClear(prefix?: string): void {
  if (!isBrowser()) return;
  if (!prefix) { sessionStorage.clear(); return; }
  for (let i = sessionStorage.length - 1; i >= 0; i--) {
    const k = sessionStorage.key(i);
    if (k && k.startsWith(prefix)) sessionStorage.removeItem(k);
  }
}

export async function cachedFetch<T>(key: string, url: string): Promise<T> {
  const hit = cacheGet<T>(key);
  if (hit !== null) return hit;
  const r = await fetch(url);
  const data = await r.json() as T;
  cacheSet(key, data);
  return data;
}
