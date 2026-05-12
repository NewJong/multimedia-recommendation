import { useMemo, useEffect, useState } from 'react';
import { Heart } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';

interface Game {
  id: number; title: string; genre: string; genres: string[]; tags: string[];
  description: string; release_year: number; rating: number; metacritic: number;
  platforms: string[]; developers: string[]; publishers: string[];
  esrb_rating: string; poster_url: string; rawg_id: number;
}

const PLATFORM_SHORT: Record<string, string> = {
  'PC': 'PC', 'PlayStation 5': 'PS5', 'PlayStation 4': 'PS4',
  'Xbox One': 'XB1', 'Xbox Series S/X': 'XSX', 'Nintendo Switch': 'Switch',
  'iOS': 'iOS', 'Android': 'Android', 'macOS': 'macOS', 'Linux': 'Linux',
};
const shortPlatform = (p: string) => PLATFORM_SHORT[p] ?? p.replace('PlayStation', 'PS').replace('Xbox', 'XB');

function GenreFilters({ genres, selected, onToggle, color }: {
  genres: string[]; selected: string[];
  onToggle: (g: string) => void; color: { active: string; pill: string };
}) {
  return (
    <div className="flex flex-wrap gap-2 mb-6">
      <button onClick={() => selected.forEach(g => onToggle(g))}
        className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-150 ${selected.length === 0 ? color.active : 'border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'}`}>
        All
      </button>
      {genres.map(g => (
        <button key={g} onClick={() => onToggle(g)}
          className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-150 ${selected.includes(g) ? color.active : color.pill}`}>
          {g}
        </button>
      ))}
    </div>
  );
}

interface RecMeta { score: number; matchedTags: string[] }

function GameCard({ g, index, liked, onToggle, recMeta }: { g: Game; index: number; liked: boolean; onToggle?: (id: number) => void; recMeta?: RecMeta }) {
  return (
    <a href={`/games/${g.id}`} className="group relative block"
      style={{ animation: 'card-in 0.35s ease both', animationDelay: `${Math.min(index * 30, 600)}ms`, textDecoration: 'none' }}>
      <div className="relative aspect-video rounded-xl overflow-hidden bg-zinc-900 mb-2.5 shadow-md">
        {g.poster_url
          ? <img src={g.poster_url} alt={g.title} loading="lazy" decoding="async"
              className="w-full h-full object-cover will-change-transform group-hover:scale-105 transition-transform duration-500" />
          : <div className="w-full h-full flex items-center justify-center text-zinc-700 text-4xl">🎮</div>
        }
        <div className="absolute top-2 left-2 flex gap-1.5">
          {g.rating > 0 && (
            <div className="bg-black/75 rounded-md px-1.5 py-0.5 flex items-center gap-1">
              <span className="text-yellow-400 text-xs">★</span>
              <span className="text-white text-xs font-semibold">{g.rating.toFixed(1)}</span>
            </div>
          )}
          {g.metacritic > 0 && (
            <div className={`bg-black/75 rounded-md px-1.5 py-0.5 text-xs font-bold ${g.metacritic >= 75 ? 'text-green-400' : g.metacritic >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
              {g.metacritic}
            </div>
          )}
        </div>
        {g.esrb_rating && (
          <div className="absolute top-2 right-2 bg-black/75 rounded-md px-1.5 py-0.5">
            <span className="text-zinc-400 text-xs">{g.esrb_rating}</span>
          </div>
        )}
        <div className="card-overlay absolute inset-0 bg-gradient-to-t from-black via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3">
          {g.genres.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-1.5">
              {g.genres.slice(0, 2).map(genre => (
                <span key={genre} className="text-xs bg-emerald-500/30 text-emerald-200 border border-emerald-500/30 rounded-full px-2 py-0.5">{genre}</span>
              ))}
            </div>
          )}
          {g.developers.length > 0 && <p className="text-zinc-300 text-xs font-medium truncate">{g.developers[0]}</p>}
          {g.platforms.length > 0 && (
            <div className="flex gap-1.5 mt-1 flex-wrap">
              {g.platforms.slice(0, 4).map(p => <span key={p} className="text-zinc-500 text-xs">{shortPlatform(p)}</span>)}
            </div>
          )}
        </div>
        {onToggle && (
          <button onClick={e => { e.preventDefault(); e.stopPropagation(); onToggle(g.id); }}
            className="absolute bottom-2 right-2 z-20 p-1.5 rounded-full border border-zinc-700 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:border-emerald-400">
            <Heart size={16} className={liked ? 'text-emerald-400' : 'text-zinc-300'} fill={liked ? 'currentColor' : 'none'} />
          </button>
        )}
      </div>
      <h3 className="text-white text-sm font-semibold leading-tight line-clamp-1 group-hover:text-emerald-300 transition-colors">{g.title}</h3>
      <p className="text-zinc-500 text-xs mt-0.5">{g.release_year || '—'}</p>
      {recMeta ? (
        <p className="text-xs mt-0.5 flex items-center gap-1.5 flex-wrap">
          <span className="text-emerald-400 font-semibold">✦ {recMeta.score}%</span>
          {recMeta.matchedTags.map(tag => <span key={tag} className="text-zinc-600">{tag}</span>)}
        </p>
      ) : (
        g.developers.length > 0 && <p className="text-zinc-600 text-xs mt-0.5 truncate">{g.developers[0]}</p>
      )}
    </a>
  );
}

type SortTab = 'popular' | 'toprated' | 'new' | 'foryou';
const SORT_TABS: { key: SortTab; label: string }[] = [
  { key: 'popular',  label: 'Popular' },
  { key: 'toprated', label: 'Top Rated' },
  { key: 'new',      label: 'New' },
  { key: 'foryou',   label: '✦ For You' },
];

const PAGE_SIZE = 20;

export default function GamesList() {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [focused, setFocused] = useState(false);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const { uid } = useAuth();
  const [likedIds, setLikedIds] = useState<Set<number>>(new Set());
  const [sortTab, setSortTab] = useState<SortTab>('popular');
  const [recs, setRecs] = useState<Game[]>([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [recsLoaded, setRecsLoaded] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    fetch(`${API_BASE}/games`)
      .then(r => r.json()).then(setGames)
      .catch(() => setError('Backend offline — run: uvicorn main:app --reload'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!uid) { setLikedIds(new Set()); return; }
    fetch(`${API_BASE}/likes/${uid}`)
      .then(r => r.json())
      .then(d => setLikedIds(new Set((d.games ?? []).map((g: any) => g.id as number))))
      .catch(() => {});
  }, [uid]);

  async function toggleLike(gameId: number) {
    if (!uid) return;
    const was = likedIds.has(gameId);
    setLikedIds(prev => { const n = new Set(prev); was ? n.delete(gameId) : n.add(gameId); return n; });
    try {
      await fetch(`${API_BASE}/likes/${uid}/game/${gameId}`, { method: 'POST' });
    } catch {
      setLikedIds(prev => { const n = new Set(prev); was ? n.add(gameId) : n.delete(gameId); return n; });
    }
  }

  useEffect(() => {
    if (!uid || recsLoaded) return;
    setRecsLoading(true);
    fetch(`${API_BASE}/recommendations/${uid}/games`)
      .then(r => r.json()).then(d => { setRecs(d); setRecsLoaded(true); })
      .catch(() => setRecsLoaded(true)).finally(() => setRecsLoading(false));
  }, [uid, recsLoaded]);

  const recMap = useMemo(() =>
    new Map((recs as any[]).map(r => [r.id, { score: r._score, matchedTags: r._matched_tags || [] }])),
    [recs]
  );

  // Reset pagination when tab, search or genre filter changes
  useEffect(() => { setVisibleCount(PAGE_SIZE); }, [sortTab, search, selectedGenres]);

  const allGenres = useMemo(() => {
    const set = new Set<string>();
    games.forEach(g => g.genres.forEach(genre => set.add(genre)));
    return [...set].sort();
  }, [games]);

  const ql = search.toLowerCase();
  const filtered = games.filter(g => {
    const matchSearch = !search || g.title.toLowerCase().includes(ql) ||
      g.genre.toLowerCase().includes(ql) ||
      g.genres.some(genre => genre.toLowerCase().includes(ql)) ||
      g.tags.some(tag => tag.toLowerCase().includes(ql)) ||
      g.developers.some(d => d.toLowerCase().includes(ql));
    const matchGenre = selectedGenres.length === 0 || selectedGenres.some(genre => g.genres.includes(genre));
    return matchSearch && matchGenre;
  });

  const sorted = useMemo(() => {
    if (sortTab === 'toprated') return [...filtered].sort((a, b) => (b.metacritic || 0) - (a.metacritic || 0));
    if (sortTab === 'new')      return [...filtered].sort((a, b) => (b.release_year || 0) - (a.release_year || 0));
    return [...filtered].sort((a, b) => (b.rating || 0) - (a.rating || 0));
  }, [filtered, sortTab]);

  const filteredRecs = useMemo(() => {
    if (selectedGenres.length === 0) return recs;
    return recs.filter((r: any) => (r.genres || []).some((genre: string) => selectedGenres.includes(genre)));
  }, [recs, selectedGenres]);

  if (loading) return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {Array.from({ length: 12 }).map((_, i) => (
        <div key={i} className="animate-pulse" style={{ animationDelay: `${i * 50}ms` }}>
          <div className="aspect-video rounded-xl bg-zinc-900 mb-2.5" />
          <div className="h-3 bg-zinc-900 rounded w-3/4 mb-1.5" />
          <div className="h-2.5 bg-zinc-900 rounded w-1/3" />
        </div>
      ))}
    </div>
  );

  if (error) return (
    <div className="bg-red-950/30 border border-red-800/50 rounded-xl p-6 text-red-400 text-sm">{error}</div>
  );

  return (
    <div>
      <div className="flex items-center gap-1 mb-5 border-b border-zinc-800/60 pb-1">
        {SORT_TABS.map(tab => (
          <button key={tab.key} onClick={() => setSortTab(tab.key)}
            className={`relative px-3 py-1.5 rounded-t-lg text-sm font-medium transition-all duration-200 ${sortTab === tab.key ? 'text-emerald-300' : 'text-zinc-500 hover:text-zinc-300'}`}>
            {tab.label}
            {sortTab === tab.key && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-400 rounded-full" />}
          </button>
        ))}
      </div>

      {sortTab !== 'foryou' && (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-zinc-500 text-sm">
              {sorted.length < games.length
                ? <><span className="text-white font-medium">{sorted.length}</span> of {games.length}</>
                : <>{games.length} games</>}
            </p>
            <input type="text" placeholder="Search…" value={search}
              onChange={e => setSearch(e.target.value)}
              onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-emerald-500 w-56 transition-all duration-300"
              style={{ boxShadow: focused ? '0 0 0 3px rgba(16,185,129,0.15)' : 'none' }}
            />
          </div>
          <GenreFilters genres={allGenres} selected={selectedGenres}
            onToggle={g => setSelectedGenres(prev => prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g])}
            color={{ active: 'bg-emerald-500 border-emerald-500 text-white', pill: 'border-zinc-700 text-zinc-400 hover:border-emerald-600 hover:text-emerald-300' }}
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {sorted.slice(0, visibleCount).map((g, i) => <GameCard key={g.id} g={g} index={i} liked={likedIds.has(g.id)} onToggle={uid ? toggleLike : undefined} recMeta={recMap.get(g.id)} />)}
          </div>
          {visibleCount < sorted.length && (
            <div className="mt-8 flex flex-col items-center gap-2">
              <p className="text-zinc-600 text-xs">{visibleCount} of {sorted.length}</p>
              <button onClick={() => setVisibleCount(v => v + PAGE_SIZE)}
                className="px-6 py-2.5 rounded-xl border border-zinc-700 text-zinc-300 text-sm font-medium hover:border-emerald-500 hover:text-emerald-300 transition-all duration-200">
                Load more
              </button>
            </div>
          )}
        </>
      )}

      {sortTab === 'foryou' && (
        <div>
          {!uid && <div className="py-20 text-center"><p className="text-zinc-500 text-sm">Sign in to get personalized recommendations</p></div>}
          {uid && recsLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="aspect-video rounded-xl bg-zinc-900 mb-2.5" />
                  <div className="h-3 bg-zinc-900 rounded w-3/4 mb-1.5" />
                  <div className="h-2.5 bg-zinc-900 rounded w-1/3" />
                </div>
              ))}
            </div>
          )}
          {uid && !recsLoading && recs.length === 0 && (
            <div className="py-20 text-center">
              <p className="text-zinc-400 text-sm mb-1">Like some games to get recommendations</p>
              <p className="text-zinc-600 text-xs">The more you like — the better the results</p>
            </div>
          )}
          {uid && !recsLoading && recs.length > 0 && (
            <>
              <GenreFilters genres={allGenres} selected={selectedGenres}
                onToggle={g => setSelectedGenres(prev => prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g])}
                color={{ active: 'bg-emerald-500 border-emerald-500 text-white', pill: 'border-zinc-700 text-zinc-400 hover:border-emerald-600 hover:text-emerald-300' }}
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {filteredRecs.slice(0, visibleCount).map((g: any, i: number) => (
                  <GameCard key={g.id} g={g} index={i} liked={likedIds.has(g.id)} onToggle={uid ? toggleLike : undefined}
                    recMeta={{ score: g._score, matchedTags: g._matched_tags || [] }} />
                ))}
              </div>
              {visibleCount < filteredRecs.length && (
                <div className="mt-8 flex flex-col items-center gap-2">
                  <p className="text-zinc-600 text-xs">{visibleCount} of {filteredRecs.length}</p>
                  <button onClick={() => setVisibleCount(v => v + PAGE_SIZE)}
                    className="px-6 py-2.5 rounded-xl border border-zinc-700 text-zinc-300 text-sm font-medium hover:border-emerald-500 hover:text-emerald-300 transition-all duration-200">
                    Load more
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
