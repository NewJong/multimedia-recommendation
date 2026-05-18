export function fmtCompact(n: number): string | null {
  if (!n) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${Math.round(n / 1_000)}K`;
  return n.toLocaleString();
}

export function fmtDuration(ms: number): string | null {
  if (!ms) return null;
  const s = Math.floor(ms / 1000), m = Math.floor(s / 60);
  return `${m}:${(s % 60).toString().padStart(2, '0')}`;
}

export function fmtRuntime(min: number): string | null {
  if (!min) return null;
  const h = Math.floor(min / 60), m = min % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

const RAWG_WIDTHS = [200, 420, 600, 640, 1280, 1920];

export function thumbUrl(url: string | null | undefined, width: number = 420): string | null {
  if (!url) return null;
  if (url.includes('media.rawg.io/media/') && !url.includes('/resize/') && !url.includes('/crop/')) {
    const w = RAWG_WIDTHS.find(x => x >= width) ?? RAWG_WIDTHS[RAWG_WIDTHS.length - 1];
    return url.replace('media.rawg.io/media/', `media.rawg.io/media/resize/${w}/-/`);
  }
  return url;
}

export function fmtMoney(n: number): string | null {
  if (!n) return null;
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000)     return `$${(n / 1_000_000).toFixed(0)}M`;
  return `$${n.toLocaleString()}`;
}
