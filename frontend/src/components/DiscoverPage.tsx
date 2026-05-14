import { useEffect, useState } from 'react';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider } from '../lib/firebase';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';

type AnchorType = 'track' | 'movie' | 'game';

interface Anchor {
  id: number;
  // tracks
  name?: string; artist?: string; image_url?: string;
  // movies / games
  title?: string; poster_url?: string;
  release_year?: number;
  genres?: string[];
}

interface CrossItem extends Anchor {
  _score: number;
  _shared_tags: string[];
}

interface CrossResponse {
  anchor: Anchor;
  tracks?: CrossItem[];
  movies?: CrossItem[];
  games?: CrossItem[];
}

const TYPE_META: Record<AnchorType, { label: string; plural: 'tracks' | 'movies' | 'games'; accent: string; chip: string; ring: string; route: string; icon: string }> = {
  track: { label: 'Music',  plural: 'tracks', accent: 'text-violet-300',  chip: 'bg-violet-500/20 text-violet-300 border-violet-500/30',  ring: 'ring-violet-500/40',  route: '/music',  icon: '🎵' },
  movie: { label: 'Movies', plural: 'movies', accent: 'text-rose-300',    chip: 'bg-rose-500/20 text-rose-300 border-rose-500/30',        ring: 'ring-rose-500/40',    route: '/movies', icon: '🎬' },
  game:  { label: 'Games',  plural: 'games',  accent: 'text-emerald-300', chip: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', ring: 'ring-emerald-500/40', route: '/games',  icon: '🎮' },
};

const OTHER_TYPES: Record<AnchorType, AnchorType[]> = {
  track: ['movie', 'game'],
  movie: ['track', 'game'],
  game:  ['track', 'movie'],
};

function itemTitle(it: Anchor): string { return it.title ?? it.name ?? '—'; }
function itemImage(it: Anchor): string | undefined { return it.poster_url ?? it.image_url; }
function itemSubtitle(it: Anchor, type: AnchorType): string {
  if (type === 'track') return it.artist ?? '';
  return it.release_year ? String(it.release_year) : '';
}


function AnchorThumb({ it, type, active, onClick }: { it: Anchor; type: AnchorType; active: boolean; onClick: () => void }) {
  const meta = TYPE_META[type];
  const img = itemImage(it);
  return (
    <button onClick={onClick}
      className={`group relative rounded-xl overflow-hidden border-2 transition-all duration-200 ${active ? `border-cyan-400 ${meta.ring} ring-2` : 'border-transparent hover:border-zinc-700'}`}
      style={{ width: 110 }}>
      <div className="aspect-square bg-zinc-900">
        {img
          ? <img src={img} alt="" className="w-full h-full object-cover" loading="lazy" />
          : <div className="w-full h-full flex items-center justify-center text-2xl">{meta.icon}</div>}
      </div>
      <p className="text-white text-[11px] font-medium truncate px-1.5 pt-1 leading-tight">{itemTitle(it)}</p>
      <p className="text-zinc-500 text-[10px] truncate px-1.5 pb-1.5 leading-tight">{itemSubtitle(it, type)}</p>
    </button>
  );
}


function ResultCard({ it, type }: { it: CrossItem; type: AnchorType }) {
  const meta = TYPE_META[type];
  const img = itemImage(it);
  return (
    <a href={`${meta.route}/${it.id}`} className="group block rounded-xl overflow-hidden bg-zinc-900/60 border border-zinc-800 hover:border-cyan-500/40 transition-colors">
      <div className="aspect-square bg-zinc-900 overflow-hidden relative">
        {img
          ? <img src={img} alt={itemTitle(it)} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" />
          : <div className="w-full h-full flex items-center justify-center text-3xl">{meta.icon}</div>}
        <div className="absolute top-2 left-2 bg-black/75 backdrop-blur rounded-md px-2 py-0.5 flex items-center gap-1">
          <span className="text-cyan-400 text-xs font-bold">✦</span>
          <span className="text-white text-xs font-semibold">{it._score}%</span>
        </div>
      </div>
      <div className="p-2.5">
        <p className={`text-sm font-semibold leading-tight truncate ${meta.accent} group-hover:text-white transition-colors`}>{itemTitle(it)}</p>
        <p className="text-zinc-500 text-xs truncate mt-0.5">{itemSubtitle(it, type)}</p>
        {it._shared_tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {it._shared_tags.map(t => (
              <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300">{t}</span>
            ))}
          </div>
        )}
      </div>
    </a>
  );
}


export default function DiscoverPage() {
  const { user, uid, loading: authLoading } = useAuth();
  const [tab, setTab] = useState<AnchorType>('track');
  const [likes, setLikes] = useState<{ tracks: Anchor[]; movies: Anchor[]; games: Anchor[] }>({ tracks: [], movies: [], games: [] });
  const [likesLoaded, setLikesLoaded] = useState(false);
  const [anchorId, setAnchorId] = useState<number | null>(null);
  const [cross, setCross] = useState<CrossResponse | null>(null);
  const [crossLoading, setCrossLoading] = useState(false);
  const [crossErr, setCrossErr] = useState<string | null>(null);

  useEffect(() => {
    if (!uid) { setLikes({ tracks: [], movies: [], games: [] }); setLikesLoaded(false); return; }
    fetch(`${API_BASE}/likes/${uid}`)
      .then(r => r.json())
      .then(d => {
        setLikes(d);
        // pick first non-empty tab and first anchor
        const first: AnchorType | null =
          d.tracks?.length ? 'track' : d.movies?.length ? 'movie' : d.games?.length ? 'game' : null;
        if (first) {
          setTab(first);
          setAnchorId(d[TYPE_META[first].plural][0].id);
        }
      })
      .catch(() => {})
      .finally(() => setLikesLoaded(true));
  }, [uid]);

  const currentAnchors = likes[TYPE_META[tab].plural];

  // Reset anchor when tab changes — pick first item of that tab
  useEffect(() => {
    if (currentAnchors.length === 0) { setAnchorId(null); return; }
    if (!currentAnchors.some(a => a.id === anchorId)) {
      setAnchorId(currentAnchors[0].id);
    }
  }, [tab, currentAnchors]);

  // Fetch cross when anchor changes
  useEffect(() => {
    if (anchorId == null) { setCross(null); return; }
    setCrossLoading(true);
    setCrossErr(null);
    fetch(`${API_BASE}/cross/${tab}/${anchorId}?k=5`)
      .then(async r => {
        if (!r.ok) {
          const e = await r.json().catch(() => ({}));
          throw new Error(e.detail || `HTTP ${r.status}`);
        }
        return r.json();
      })
      .then((d: CrossResponse) => setCross(d))
      .catch(e => setCrossErr(e.message))
      .finally(() => setCrossLoading(false));
  }, [tab, anchorId]);

  if (authLoading) return <div className="py-24 text-center text-zinc-600">Loading…</div>;

  if (!user) return (
    <div className="max-w-2xl mx-auto py-24 px-6 text-center">
      <p className="text-6xl mb-4">✦</p>
      <h1 className="text-2xl font-bold text-white mb-2">Cross-domain Discovery</h1>
      <p className="text-zinc-500 mb-8 leading-relaxed">
        Find movies, games and tracks that resonate with what you already love —
        across different media, ranked by semantic similarity.
      </p>
      <button onClick={() => signInWithPopup(auth, googleProvider)}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-zinc-700 hover:border-zinc-500 text-sm text-zinc-200 transition-all">
        Sign in to start
      </button>
    </div>
  );

  const totalLikes = likes.tracks.length + likes.movies.length + likes.games.length;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-1">
          <span className="bg-gradient-to-r from-cyan-300 via-violet-300 to-rose-300 bg-clip-text text-transparent">Cross-domain Discovery</span>
        </h1>
        <p className="text-zinc-500 text-sm">
          Pick any of your likes — we'll surface the closest items from the other two domains using semantic embeddings.
        </p>
      </div>

      {likesLoaded && totalLikes === 0 && (
        <div className="py-24 text-center border border-zinc-800/60 rounded-2xl">
          <p className="text-5xl mb-3">♡</p>
          <p className="text-zinc-400 text-sm mb-1">Like at least one track, movie or game first.</p>
          <p className="text-zinc-600 text-xs">Then come back — we'll connect the dots.</p>
        </div>
      )}

      {likesLoaded && totalLikes > 0 && (
        <>
          {/* Type tabs */}
          <div className="flex items-center gap-1 mb-4 border-b border-zinc-800/60 pb-1">
            {(['track', 'movie', 'game'] as AnchorType[]).map(t => {
              const meta = TYPE_META[t];
              const count = likes[meta.plural].length;
              return (
                <button key={t} onClick={() => setTab(t)} disabled={count === 0}
                  className={`relative px-3 py-1.5 rounded-t-lg text-sm font-medium transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed ${tab === t ? meta.accent : 'text-zinc-500 hover:text-zinc-300'}`}>
                  {meta.label}
                  <span className="ml-1.5 text-xs text-zinc-600">{count}</span>
                  {tab === t && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 rounded-full" />}
                </button>
              );
            })}
          </div>

          {/* Anchor row */}
          <p className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Anchor — your {TYPE_META[tab].label.toLowerCase()}</p>
          {currentAnchors.length === 0 ? (
            <p className="text-zinc-600 text-sm py-8">Nothing liked in this domain yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2 mb-8">
              {currentAnchors.map(a => (
                <AnchorThumb key={a.id} it={a} type={tab} active={a.id === anchorId} onClick={() => setAnchorId(a.id)} />
              ))}
            </div>
          )}

          {/* Results */}
          {anchorId != null && (
            <>
              {crossLoading && (
                <div className="flex flex-col gap-8">
                  {OTHER_TYPES[tab].map(o => (
                    <div key={o}>
                      <div className="h-3 w-24 bg-zinc-800 rounded animate-pulse mb-3" />
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                        {[1,2,3,4,5].map(i => (
                          <div key={i} className="animate-pulse rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800" style={{ animationDelay: `${i*60}ms` }}>
                            <div className="aspect-square bg-zinc-800" />
                            <div className="p-2.5 space-y-2">
                              <div className="h-3 bg-zinc-800 rounded w-3/4" />
                              <div className="h-2 bg-zinc-800 rounded w-1/2" />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {crossErr && (
                <div className="bg-red-950/30 border border-red-800/50 rounded-xl p-4 text-red-400 text-sm">
                  {crossErr}
                  {crossErr.includes('embedding') && (
                    <p className="text-red-300/70 text-xs mt-2">Run <code className="font-mono">python backend/evaluation/cross_domain/embed_items.py</code> to generate embeddings.</p>
                  )}
                </div>
              )}

              {!crossLoading && !crossErr && cross && (
                <div className="flex flex-col gap-10">
                  {OTHER_TYPES[tab].map(o => {
                    const items = (cross[TYPE_META[o].plural] ?? []) as CrossItem[];
                    if (items.length === 0) return null;
                    return (
                      <div key={o}>
                        <div className="flex items-baseline gap-2 mb-3">
                          <h2 className={`text-sm font-semibold uppercase tracking-widest ${TYPE_META[o].accent}`}>{TYPE_META[o].label}</h2>
                          <span className="text-zinc-700 text-xs">{items.length} closest</span>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                          {items.map(it => <ResultCard key={it.id} it={it} type={o} />)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
