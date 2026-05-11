import { useMemo, useEffect, useState } from 'react';
import { Heart } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';
import { fmtRuntime } from '../lib/format';

interface Movie {
  id: number; title: string; genre: string; genres: string[]; keywords: string[];
  overview: string; tagline: string; release_year: number; runtime: number;
  rating: number; vote_count: number; popularity: number; language: string;
  status: string; director: string; actors: string[];
  poster_url: string; backdrop_url: string; budget: number; revenue: number;
  collection: string; tmdb_id: number;
}

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

function MovieCard({ m, index, liked, onToggle }: { m: Movie; index: number; liked: boolean; onToggle?: (id: number) => void }) {
  return (
    <a href={`/movies/${m.id}`} className="group relative block"
      style={{ animation: 'card-in 0.35s ease both', animationDelay: `${Math.min(index * 30, 600)}ms`, textDecoration: 'none' }}>
      <div className="relative aspect-[2/3] rounded-xl overflow-hidden bg-zinc-900 mb-2.5 shadow-md">
        {m.poster_url
          ? <img src={m.poster_url} alt={m.title} loading="lazy" decoding="async"
              className="w-full h-full object-cover will-change-transform group-hover:scale-105 transition-transform duration-500" />
          : <div className="w-full h-full flex items-center justify-center text-zinc-700 text-4xl">🎬</div>
        }
        {m.rating > 0 && (
          <div className="absolute top-2 left-2 bg-black/75 rounded-md px-1.5 py-0.5 flex items-center gap-1">
            <span className="text-yellow-400 text-xs">★</span>
            <span className="text-white text-xs font-semibold">{m.rating.toFixed(1)}</span>
          </div>
        )}
        <div className="card-overlay absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3">
          {m.genres.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {m.genres.slice(0, 2).map(g => (
                <span key={g} className="text-xs bg-rose-500/30 text-rose-200 border border-rose-500/30 rounded-full px-2 py-0.5">{g}</span>
              ))}
            </div>
          )}
          {m.director && <p className="text-zinc-300 text-xs font-medium truncate">{m.director}</p>}
          {m.runtime > 0 && <p className="text-zinc-500 text-xs">{fmtRuntime(m.runtime)}</p>}
          {m.tagline && <p className="text-zinc-400 text-xs italic mt-1 line-clamp-2">"{m.tagline}"</p>}
        </div>
      </div>
      {onToggle && (
        <button onClick={e => { e.preventDefault(); e.stopPropagation(); onToggle(m.id); }}
          className="absolute top-2 right-2 z-10 p-1.5 rounded-full border border-zinc-700 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:border-rose-400">
          <Heart size={16} className={liked ? 'text-rose-400' : 'text-zinc-300'} fill={liked ? 'currentColor' : 'none'} />
        </button>
      )}
      <h3 className="text-white text-sm font-semibold leading-tight line-clamp-1 group-hover:text-rose-300 transition-colors">{m.title}</h3>
      <p className="text-zinc-500 text-xs mt-0.5">{m.release_year || '—'}</p>
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

export default function MoviesList() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [focused, setFocused] = useState(false);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const { uid } = useAuth();
  const [likedIds, setLikedIds] = useState<Set<number>>(new Set());
  const [sortTab, setSortTab] = useState<SortTab>('popular');
  const [recs, setRecs] = useState<Movie[]>([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [recsLoaded, setRecsLoaded] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/movies`)
      .then(r => r.json()).then(setMovies)
      .catch(() => setError('Backend offline — run: uvicorn main:app --reload'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!uid) { setLikedIds(new Set()); return; }
    fetch(`${API_BASE}/likes/${uid}`)
      .then(r => r.json())
      .then(d => setLikedIds(new Set((d.movies ?? []).map((m: any) => m.id as number))))
      .catch(() => {});
  }, [uid]);

  async function toggleLike(movieId: number) {
    if (!uid) return;
    const was = likedIds.has(movieId);
    setLikedIds(prev => { const n = new Set(prev); was ? n.delete(movieId) : n.add(movieId); return n; });
    try {
      await fetch(`${API_BASE}/likes/${uid}/movie/${movieId}`, { method: 'POST' });
    } catch {
      setLikedIds(prev => { const n = new Set(prev); was ? n.add(movieId) : n.delete(movieId); return n; });
    }
  }

  useEffect(() => {
    if (sortTab !== 'foryou' || !uid || recsLoaded) return;
    setRecsLoading(true);
    fetch(`${API_BASE}/recommendations/${uid}/movies`)
      .then(r => r.json()).then(d => { setRecs(d); setRecsLoaded(true); })
      .catch(() => setRecsLoaded(true)).finally(() => setRecsLoading(false));
  }, [sortTab, uid, recsLoaded]);

  const allGenres = useMemo(() => {
    const set = new Set<string>();
    movies.forEach(m => m.genres.forEach(g => set.add(g)));
    return [...set].sort();
  }, [movies]);

  const ql = search.toLowerCase();
  const filtered = movies.filter(m => {
    const matchSearch = !search || m.title.toLowerCase().includes(ql) ||
      m.director.toLowerCase().includes(ql) ||
      m.genres.some(g => g.toLowerCase().includes(ql)) ||
      m.actors.some(a => a.toLowerCase().includes(ql));
    const matchGenre = selectedGenres.length === 0 || selectedGenres.some(g => m.genres.includes(g));
    return matchSearch && matchGenre;
  });

  const sorted = useMemo(() => {
    if (sortTab === 'toprated') return [...filtered].sort((a, b) => (b.rating || 0) - (a.rating || 0));
    if (sortTab === 'new')      return [...filtered].sort((a, b) => (b.release_year || 0) - (a.release_year || 0));
    return [...filtered].sort((a, b) => (b.popularity || 0) - (a.popularity || 0));
  }, [filtered, sortTab]);

  if (loading) return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {Array.from({ length: 15 }).map((_, i) => (
        <div key={i} className="animate-pulse" style={{ animationDelay: `${i * 50}ms` }}>
          <div className="aspect-[2/3] rounded-xl bg-zinc-900 mb-2.5" />
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
            className={`relative px-3 py-1.5 rounded-t-lg text-sm font-medium transition-all duration-200 ${sortTab === tab.key ? 'text-rose-300' : 'text-zinc-500 hover:text-zinc-300'}`}>
            {tab.label}
            {sortTab === tab.key && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-rose-400 rounded-full" />}
          </button>
        ))}
      </div>

      {sortTab !== 'foryou' && (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-zinc-500 text-sm">
              {sorted.length < movies.length
                ? <><span className="text-white font-medium">{sorted.length}</span> of {movies.length}</>
                : <>{movies.length} movies</>}
            </p>
            <input type="text" placeholder="Search…" value={search}
              onChange={e => setSearch(e.target.value)}
              onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-rose-500 w-56 transition-all duration-300"
              style={{ boxShadow: focused ? '0 0 0 3px rgba(244,63,94,0.15)' : 'none' }}
            />
          </div>
          <GenreFilters genres={allGenres} selected={selectedGenres}
            onToggle={g => setSelectedGenres(prev => prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g])}
            color={{ active: 'bg-rose-500 border-rose-500 text-white', pill: 'border-zinc-700 text-zinc-400 hover:border-rose-600 hover:text-rose-300' }}
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {sorted.map((m, i) => <MovieCard key={m.id} m={m} index={i} liked={likedIds.has(m.id)} onToggle={uid ? toggleLike : undefined} />)}
          </div>
        </>
      )}

      {sortTab === 'foryou' && (
        <div>
          {!uid && <div className="py-20 text-center"><p className="text-zinc-500 text-sm">Sign in to get personalized recommendations</p></div>}
          {uid && recsLoading && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="aspect-[2/3] rounded-xl bg-zinc-900 mb-2.5" />
                  <div className="h-3 bg-zinc-900 rounded w-3/4 mb-1.5" />
                  <div className="h-2.5 bg-zinc-900 rounded w-1/3" />
                </div>
              ))}
            </div>
          )}
          {uid && !recsLoading && recs.length === 0 && (
            <div className="py-20 text-center">
              <p className="text-zinc-400 text-sm mb-1">Like some movies to get recommendations</p>
              <p className="text-zinc-600 text-xs">The more you like — the better the results</p>
            </div>
          )}
          {uid && !recsLoading && recs.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {recs.map((m, i) => <MovieCard key={m.id} m={m} index={i} liked={likedIds.has(m.id)} onToggle={uid ? toggleLike : undefined} />)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
