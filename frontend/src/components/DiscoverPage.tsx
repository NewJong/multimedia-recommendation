import { useEffect, useMemo, useRef, useState } from 'react';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider } from '../lib/firebase';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';
import { thumbUrl } from '../lib/format';
import CrossEchoes from './CrossEchoes';

type ItemType = 'track' | 'movie' | 'game';

interface Like {
  id: number;
  name?: string; artist?: string; image_url?: string;
  title?: string; poster_url?: string;
  release_year?: number;
}

interface LikesResponse {
  tracks: Like[];
  movies: Like[];
  games:  Like[];
}

const TYPE_META: Record<ItemType, { label: string; plural: 'tracks' | 'movies' | 'games'; accent: string; chip: string; chipActive: string; icon: string }> = {
  track: { label: 'Music',  plural: 'tracks', accent: 'text-violet-300',  chip: 'border-violet-500/30',  chipActive: 'bg-violet-500/20 text-violet-300 border-violet-500/40',    icon: '🎵' },
  movie: { label: 'Movies', plural: 'movies', accent: 'text-rose-300',    chip: 'border-rose-500/30',    chipActive: 'bg-rose-500/20 text-rose-300 border-rose-500/40',          icon: '🎬' },
  game:  { label: 'Games',  plural: 'games',  accent: 'text-emerald-300', chip: 'border-emerald-500/30', chipActive: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40', icon: '🎮' },
};

function likeTitle(it: Like): string { return it.title ?? it.name ?? '—'; }
function likeImage(it: Like): string | null { return thumbUrl(it.poster_url ?? it.image_url, 420); }
function likeSubtitle(it: Like, type: ItemType): string {
  if (type === 'track') return it.artist ?? '';
  return it.release_year ? String(it.release_year) : '';
}


/**
 * Discover: pick any item you've liked, see how it echoes in the other two
 * domains. The page reuses CrossEchoes for the result rendering, so the layout
 * is identical to the detail pages — predictability over novelty. The only
 * new piece is the anchor picker (dropdown with thumbnails, searchable).
 */
export default function DiscoverPage() {
  const { user, uid, loading: authLoading } = useAuth();
  const [likes, setLikes]             = useState<LikesResponse>({ tracks: [], movies: [], games: [] });
  const [likesLoaded, setLikesLoaded] = useState(false);
  const [tab, setTab]                 = useState<ItemType>('movie');
  const [anchorId, setAnchorId]       = useState<number | null>(null);

  useEffect(() => {
    if (!uid) { setLikes({ tracks: [], movies: [], games: [] }); setLikesLoaded(false); return; }
    fetch(`${API_BASE}/likes/${uid}`)
      .then(r => r.json())
      .then((d: LikesResponse) => {
        setLikes(d);
        // Pick first non-empty domain + first item as default.
        const first: ItemType | null =
          d.movies?.length ? 'movie' : d.tracks?.length ? 'track' : d.games?.length ? 'game' : null;
        if (first) {
          setTab(first);
          setAnchorId(d[TYPE_META[first].plural][0].id);
        }
      })
      .catch(() => {})
      .finally(() => setLikesLoaded(true));
  }, [uid]);

  // Likes available in the currently active tab.
  const currentLikes = likes[TYPE_META[tab].plural];
  const anchor       = currentLikes.find(a => a.id === anchorId) ?? null;

  // When tab changes, ensure the anchor belongs to the new tab.
  useEffect(() => {
    if (currentLikes.length === 0) { setAnchorId(null); return; }
    if (!currentLikes.some(a => a.id === anchorId)) {
      setAnchorId(currentLikes[0].id);
    }
  }, [tab, currentLikes]);

  function pickRandom() {
    if (currentLikes.length === 0) return;
    let pick = currentLikes[Math.floor(Math.random() * currentLikes.length)];
    // Avoid landing on the same one twice in a row when possible.
    if (currentLikes.length > 1 && pick.id === anchorId) {
      pick = currentLikes[(currentLikes.findIndex(a => a.id === anchorId) + 1) % currentLikes.length];
    }
    setAnchorId(pick.id);
  }

  const totalLikes = likes.tracks.length + likes.movies.length + likes.games.length;

  if (authLoading) return <div className="py-24 text-center text-zinc-600">Loading…</div>;

  if (!user) return (
    <div className="max-w-2xl mx-auto py-24 px-6 text-center">
      <p className="text-6xl mb-4">✦</p>
      <h1 className="text-2xl font-bold text-white mb-2">Cross-domain Discovery</h1>
      <p className="text-zinc-500 mb-8 leading-relaxed">
        Pick any of your likes — see the closest tracks, movies and games from other domains by vibe.
      </p>
      <button onClick={() => signInWithPopup(auth, googleProvider)}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-zinc-700 hover:border-zinc-500 text-sm text-zinc-200 transition-all">
        Sign in to start
      </button>
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">
          <span className="bg-gradient-to-r from-cyan-300 via-violet-300 to-rose-300 bg-clip-text text-transparent">Cross-domain Discovery</span>
        </h1>
        <p className="text-zinc-500 text-sm mt-1">
          Pick anything you've liked — see the closest items from the other two domains, ranked by semantic similarity.
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
          {/* Domain tabs — only enabled where the user has at least one like. */}
          <div className="flex items-center gap-1.5 mb-4">
            {(['movie', 'track', 'game'] as ItemType[]).map(t => {
              const meta  = TYPE_META[t];
              const count = likes[meta.plural].length;
              return (
                <button key={t} onClick={() => setTab(t)} disabled={count === 0}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border disabled:opacity-30 disabled:cursor-not-allowed ${
                    tab === t ? meta.chipActive : `text-zinc-500 border-zinc-800 hover:border-zinc-700`
                  }`}>
                  {meta.label} <span className="ml-1 opacity-60">{count}</span>
                </button>
              );
            })}
          </div>

          {/* Anchor picker + selected anchor card */}
          {currentLikes.length === 0 ? (
            <p className="text-zinc-600 text-sm py-8">Nothing liked in this domain yet.</p>
          ) : (
            <AnchorPicker
              type={tab}
              likes={currentLikes}
              anchor={anchor}
              onPick={setAnchorId}
              onRandom={pickRandom}
            />
          )}

          {/* Reuse the same cross-domain layout as detail pages. */}
          {anchor && anchorId != null && (
            <CrossEchoes anchorType={tab} anchorId={anchorId} />
          )}
        </>
      )}
    </div>
  );
}


/**
 * Custom searchable combobox with thumbnails. Native <select> can't show
 * posters, and a thumb grid would be massive for users with 50+ likes — this
 * compact dropdown scales to any library size and gives the demo a polished feel.
 */
function AnchorPicker({ type, likes, anchor, onPick, onRandom }: {
  type:     ItemType;
  likes:    Like[];
  anchor:   Like | null;
  onPick:   (id: number) => void;
  onRandom: () => void;
}) {
  const [open, setOpen]     = useState(false);
  const [query, setQuery]   = useState('');
  const wrapRef             = useRef<HTMLDivElement | null>(null);
  const inputRef            = useRef<HTMLInputElement | null>(null);
  const meta = TYPE_META[type];

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    function handle(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [open]);

  // Auto-focus the search box when the dropdown opens.
  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);

  const filtered = useMemo(() => {
    if (!query.trim()) return likes;
    const q = query.toLowerCase();
    return likes.filter(l => likeTitle(l).toLowerCase().includes(q) || (l.artist?.toLowerCase().includes(q) ?? false));
  }, [likes, query]);

  return (
    <div ref={wrapRef} className="relative mb-6">
      <div className="flex items-stretch gap-2">
        {/* The big anchor card itself is the dropdown trigger. */}
        <button onClick={() => setOpen(v => !v)}
          className={`flex-1 flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border ${meta.chip} hover:bg-zinc-900 transition-colors text-left`}>
          {anchor ? (
            <>
              {likeImage(anchor)
                ? <img src={likeImage(anchor)!} alt="" className="w-12 h-12 rounded-md object-cover flex-shrink-0 bg-zinc-900" />
                : <div className="w-12 h-12 rounded-md bg-zinc-900 flex items-center justify-center text-xl flex-shrink-0">{meta.icon}</div>}
              <div className="min-w-0 flex-1">
                <p className={`text-[10px] uppercase tracking-widest ${meta.accent} font-semibold mb-0.5`}>Anchor · your liked {meta.label.slice(0, -1).toLowerCase()}</p>
                <p className="text-white text-sm font-semibold truncate">{likeTitle(anchor)}</p>
                <p className="text-zinc-500 text-xs truncate">{likeSubtitle(anchor, type)}</p>
              </div>
              <svg className={`w-4 h-4 text-zinc-500 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </>
          ) : (
            <span className="text-zinc-500 text-sm">Pick a {meta.label.slice(0, -1).toLowerCase()} you liked…</span>
          )}
        </button>

        <button onClick={onRandom} title="Random pick"
          className={`px-3.5 rounded-xl bg-zinc-900/60 border ${meta.chip} hover:bg-zinc-900 text-zinc-300 text-sm font-medium transition-colors`}>
          🎲
        </button>
      </div>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-30 top-full left-0 right-0 mt-2 rounded-xl bg-zinc-950 border border-zinc-800 shadow-2xl shadow-black/60 overflow-hidden">
          <div className="p-2 border-b border-zinc-800">
            <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)}
              placeholder={`Search your ${likes.length} liked ${meta.label.toLowerCase()}…`}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-600" />
          </div>
          <div className="max-h-72 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="text-zinc-600 text-xs text-center py-6">No matches.</p>
            ) : filtered.map(l => (
              <button key={l.id}
                onClick={() => { onPick(l.id); setOpen(false); setQuery(''); }}
                className={`w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors ${
                  l.id === anchor?.id ? 'bg-zinc-900' : 'hover:bg-zinc-900/70'
                }`}>
                {likeImage(l)
                  ? <img src={likeImage(l)!} alt="" loading="lazy" className="w-8 h-8 rounded object-cover flex-shrink-0 bg-zinc-900" />
                  : <div className="w-8 h-8 rounded bg-zinc-900 flex items-center justify-center text-sm flex-shrink-0">{meta.icon}</div>}
                <div className="min-w-0 flex-1">
                  <p className="text-white text-sm truncate">{likeTitle(l)}</p>
                  <p className="text-zinc-500 text-xs truncate">{likeSubtitle(l, type)}</p>
                </div>
                {l.id === anchor?.id && <span className={`text-xs ${meta.accent}`}>•</span>}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
