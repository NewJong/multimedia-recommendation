import { useEffect, useRef, useState } from 'react';
import { API_BASE } from '../lib/api';
import { thumbUrl } from '../lib/format';
import { cacheGet, cacheSet } from '../lib/cache';

type ItemType = 'track' | 'movie' | 'game';

interface CrossItem {
  id: number;
  name?: string; artist?: string; image_url?: string;
  title?: string; poster_url?: string;
  release_year?: number;
  _score: number;
  _shared_tags: string[];
}

interface CrossResponse {
  anchor: unknown;
  tracks?: CrossItem[];
  movies?: CrossItem[];
  games?: CrossItem[];
}

const TYPE_META: Record<ItemType, { label: string; plural: 'tracks' | 'movies' | 'games'; route: string; accent: string; chipBg: string; cardBorder: string; cardHover: string; iconBg: string; icon: string }> = {
  track: { label: 'Music',  plural: 'tracks', route: '/music',  accent: 'text-violet-300',  chipBg: 'bg-violet-500/15 text-violet-300 border-violet-500/25',  cardBorder: 'border-zinc-800',  cardHover: 'hover:border-violet-500/50',  iconBg: 'bg-violet-500/10',  icon: '🎵' },
  movie: { label: 'Movies', plural: 'movies', route: '/movies', accent: 'text-rose-300',    chipBg: 'bg-rose-500/15 text-rose-300 border-rose-500/25',        cardBorder: 'border-zinc-800',  cardHover: 'hover:border-rose-500/50',    iconBg: 'bg-rose-500/10',    icon: '🎬' },
  game:  { label: 'Games',  plural: 'games',  route: '/games',  accent: 'text-emerald-300', chipBg: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25', cardBorder: 'border-zinc-800', cardHover: 'hover:border-emerald-500/50', iconBg: 'bg-emerald-500/10', icon: '🎮' },
};

const OTHER_TYPES: Record<ItemType, ItemType[]> = {
  track: ['movie', 'game'],
  movie: ['track', 'game'],
  game:  ['track', 'movie'],
};

function itemTitle(it: CrossItem): string { return it.title ?? it.name ?? '—'; }
function itemImage(it: CrossItem): string | undefined {
  const raw = it.poster_url ?? it.image_url;
  return thumbUrl(raw, 420) ?? undefined;
}
function itemSubtitle(it: CrossItem, type: ItemType): string {
  if (type === 'track') return it.artist ?? '';
  return it.release_year ? String(it.release_year) : '';
}


function HorizontalRow({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd]     = useState(false);

  function updateEdges() {
    const el = ref.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 2);
    setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 2);
  }

  useEffect(() => {
    updateEdges();
    const el = ref.current;
    if (!el) return;
    el.addEventListener('scroll', updateEdges, { passive: true });
    const ro = new ResizeObserver(updateEdges);
    ro.observe(el);
    return () => { el.removeEventListener('scroll', updateEdges); ro.disconnect(); };
  }, []);

  function nudge(dir: 1 | -1) {
    const el = ref.current;
    if (!el) return;
    el.scrollBy({ left: dir * el.clientWidth * 0.82, behavior: 'smooth' });
  }

  const btnCls = "absolute top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-zinc-950/80 hover:bg-zinc-900 border border-zinc-700/60 hover:border-zinc-500 text-zinc-200 hover:text-white flex items-center justify-center shadow-lg shadow-black/40 backdrop-blur-md transition-all duration-200 disabled:opacity-0 disabled:pointer-events-none disabled:scale-90";

  return (
    <div className="relative">
      <div ref={ref}
        className="flex gap-3 overflow-x-auto scroll-smooth snap-x snap-mandatory pb-1 [&::-webkit-scrollbar]:hidden"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' } as React.CSSProperties}>
        {children}
      </div>

      <div className={`pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-black/70 via-black/30 to-transparent transition-opacity duration-300 ${atStart ? 'opacity-0' : 'opacity-100'}`} />
      <div className={`pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-black/70 via-black/30 to-transparent transition-opacity duration-300 ${atEnd ? 'opacity-0' : 'opacity-100'}`} />

      <button onClick={() => nudge(-1)} disabled={atStart} aria-label="Previous" className={`${btnCls} left-2`}>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" /></svg>
      </button>
      <button onClick={() => nudge(1)} disabled={atEnd} aria-label="Next" className={`${btnCls} right-2`}>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" /></svg>
      </button>
    </div>
  );
}


export default function CrossEchoes({ anchorType, anchorId }: { anchorType: ItemType; anchorId: number }) {
  const [data, setData]       = useState<CrossResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const [explanations, setExplanations] = useState<Record<string, string>>({});

  useEffect(() => {
    const cacheKey = `cross:${anchorType}:${anchorId}:15`;
    setError(null);
    setExplanations({});

    const cached = cacheGet<CrossResponse>(cacheKey);
    if (cached) {
      setData(cached);
      setLoading(false);
      return;
    }

    setLoading(true);
    setData(null);

    fetch(`${API_BASE}/cross/${anchorType}/${anchorId}?k=15`)
      .then(async r => {
        if (!r.ok) {
          const e = await r.json().catch(() => ({}));
          throw new Error(e.detail || `HTTP ${r.status}`);
        }
        return r.json() as Promise<CrossResponse>;
      })
      .then(d => { setData(d); cacheSet(cacheKey, d); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [anchorType, anchorId]);

  async function fetchExplanation(recType: ItemType, recId: number, score: number) {
    const key = `${recType}-${recId}`;
    if (explanations[key]) return;

    setExplanations(prev => ({ ...prev, [key]: 'loading' }));
    try {
      const r = await fetch(`${API_BASE}/cross/explain`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ pairs: [{ anchor_type: anchorType, anchor_id: anchorId, rec_type: recType, rec_id: recId, score }] }),
      });
      if (!r.ok) throw new Error();
      const map: Record<string, string> = await r.json();
      const sentence = map[`${anchorType}-${anchorId}__${recType}-${recId}`];
      setExplanations(prev => ({ ...prev, [key]: sentence || '' }));
    } catch {
      setExplanations(prev => ({ ...prev, [key]: '' }));
    }
  }

  if (error && error.toLowerCase().includes('embedding')) return null;
  if (error) return (
    <div className="mt-10 bg-red-950/20 border border-red-900/40 rounded-2xl p-4 text-red-400/80 text-sm">
      Couldn't load cross-domain echoes — {error}
    </div>
  );

  const hasAny = data && OTHER_TYPES[anchorType].some(t => (data[TYPE_META[t].plural]?.length ?? 0) > 0);

  return (
    <div className="mt-12">
      <div className="flex items-baseline gap-3 mb-1">
        <h2 className="text-xl font-bold">
          <span className="bg-gradient-to-r from-cyan-300 via-violet-300 to-rose-300 bg-clip-text text-transparent">Echoes from other domains</span>
        </h2>
        <span className="text-cyan-400/70 text-lg leading-none">✦</span>
      </div>
      <p className="text-zinc-500 text-sm mb-6">The closest experiential matches across media — same vibe, different form.</p>

      {loading && (
        <div className="space-y-8">
          {[1, 2].map(s => (
            <div key={s}>
              <div className="h-3 bg-zinc-800/80 rounded w-20 mb-3 animate-pulse" />
              <div className="flex gap-3 overflow-hidden pb-2">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="rounded-xl overflow-hidden bg-zinc-900/60 border border-zinc-800 animate-pulse flex-shrink-0 w-[180px]" style={{ animationDelay: `${i * 60}ms` }}>
                    <div className="aspect-square bg-zinc-800/60" />
                    <div className="p-2.5 space-y-2">
                      <div className="h-3 bg-zinc-800/60 rounded w-3/4" />
                      <div className="h-2 bg-zinc-800/60 rounded w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !hasAny && (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-8 text-center text-zinc-600 text-sm">
          No cross-domain matches above the noise floor for this one.
        </div>
      )}

      {!loading && hasAny && data && (
        <div className="flex flex-col gap-8">
          {OTHER_TYPES[anchorType].map(other => {
            const meta  = TYPE_META[other];
            const items = (data[meta.plural] ?? []) as CrossItem[];
            if (items.length === 0) return null;
            return (
              <section key={other}>
                <div className="flex items-baseline gap-2 mb-3">
                  <span className={`text-xs font-semibold uppercase tracking-widest ${meta.accent}`}>{meta.label}</span>
                  <span className="text-zinc-700 text-xs">{items.length} matches</span>
                </div>
                <HorizontalRow>
                  {items.map(it => {
                    const img    = itemImage(it);
                    const key    = `${other}-${it.id}`;
                    const expl   = explanations[key];
                    const isLoad = expl === 'loading';
                    const hasExpl = typeof expl === 'string' && expl !== '' && expl !== 'loading';

                    return (
                      <div key={it.id}
                        className={`group snap-start flex-shrink-0 w-[180px] rounded-xl overflow-hidden bg-zinc-900/60 border ${meta.cardBorder} ${meta.cardHover} transition-colors flex flex-col`}>
                        <a href={`${meta.route}/${it.id}`} className="block relative">
                          <div className="aspect-square bg-zinc-900 overflow-hidden">
                            {img
                              ? <img src={img} alt={itemTitle(it)} loading="lazy" decoding="async"
                                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                              : <div className={`w-full h-full flex items-center justify-center text-3xl ${meta.iconBg}`}>{meta.icon}</div>}
                          </div>
                          <div className="absolute top-2 left-2 bg-black/75 backdrop-blur rounded-md px-2 py-0.5 flex items-center gap-1">
                            <span className="text-cyan-400 text-xs font-bold">✦</span>
                            <span className="text-white text-xs font-semibold">{it._score}%</span>
                          </div>
                        </a>

                        <div className="p-2.5 flex-1 flex flex-col">
                          <a href={`${meta.route}/${it.id}`}
                            className={`text-sm font-semibold leading-tight truncate ${meta.accent} hover:text-white transition-colors`}>{itemTitle(it)}</a>
                          <p className="text-zinc-500 text-xs truncate mt-0.5">{itemSubtitle(it, other)}</p>

                          {it._shared_tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {it._shared_tags.map(t => (
                                <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-full border border-cyan-500/25 bg-cyan-500/10 text-cyan-300/90">{t}</span>
                              ))}
                            </div>
                          )}

                          <div className="mt-auto pt-2.5">
                            {hasExpl ? (
                              <p className="text-zinc-400 text-[11px] italic leading-snug">"{expl}"</p>
                            ) : isLoad ? (
                              <p className="text-zinc-600 text-[11px] italic flex items-center gap-1.5">
                                <span className="w-1 h-1 rounded-full bg-cyan-400/70 animate-pulse" />
                                thinking…
                              </p>
                            ) : (
                              <button onClick={() => fetchExplanation(other, it.id, it._score)}
                                className="text-[11px] text-cyan-400/80 hover:text-cyan-300 font-medium inline-flex items-center gap-1">
                                <span>✨</span> Why does this match?
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </HorizontalRow>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
