import { useMemo, useEffect, useState } from 'react';
import { Heart } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';
import { fmtCompact } from '../lib/format';

interface Track {
  id: number;
  name: string;
  genres: string[];
  tags: string[];
  artist: string;
  album: string;
  duration_ms: number;
  listeners: number;
  playcount: number;
  summary: string;
  image_url: string;
  url: string;
}


function GenreFilters({ genres, selected, onToggle, color }: {
  genres: string[];
  selected: string[];
  onToggle: (g: string) => void;
  color: { active: string; pill: string };
}) {
  return (
    <div className="flex flex-wrap gap-2 mb-6">
      <button
        onClick={() => selected.forEach(g => onToggle(g))}
        className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-150 ${
          selected.length === 0 ? color.active : 'border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'
        }`}
      >
        All
      </button>
      {genres.map(g => (
        <button
          key={g}
          onClick={() => onToggle(g)}
          className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-150 ${
            selected.includes(g) ? color.active : color.pill
          }`}
        >
          {g}
        </button>
      ))}
    </div>
  );
}


interface RecMeta { score: number; matchedTags: string[] }

function TrackCard({ t, index, liked, onToggle, recMeta }: { t: Track; index: number; liked: boolean; onToggle?: (id: number) => void; recMeta?: RecMeta }) {
  const genres = t.genres || [];

  return (
    <a
      href={`/music/${t.id}`}
      className="group relative block"
      style={{ animation: 'card-in 0.35s ease both', animationDelay: `${Math.min(index * 30, 600)}ms`, textDecoration: 'none' }}
    >
      <div className="relative aspect-square rounded-xl overflow-hidden bg-zinc-900 mb-2.5 shadow-md">
        {t.image_url ? (
          <img src={t.image_url} alt={t.name} loading="lazy" decoding="async"
            className="w-full h-full object-cover will-change-transform group-hover:scale-105 transition-transform duration-500" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-zinc-700 text-4xl">🎵</div>
        )}
        {genres.length > 0 && (
          <div className="card-overlay absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/90 to-transparent p-3 translate-y-full group-hover:translate-y-0 transition-transform duration-300">
            <div className="flex flex-wrap gap-1">
              {genres.slice(0, 2).map(g => (
                <span key={g} className="text-xs bg-violet-500/30 text-violet-200 border border-violet-500/30 rounded-full px-2 py-0.5">{g}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {onToggle && (
        <button
          onClick={e => { e.preventDefault(); e.stopPropagation(); onToggle(t.id); }}
          className="absolute top-2 right-2 z-10 p-1.5 rounded-full border border-zinc-700 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:border-violet-400"
        >
          <Heart size={16} className={liked ? 'text-violet-400' : 'text-zinc-300'} fill={liked ? 'currentColor' : 'none'} />
        </button>
      )}

      <h3 className="text-white text-sm font-semibold leading-tight line-clamp-1 group-hover:text-violet-300 transition-colors">{t.name}</h3>
      <p className="text-zinc-400 text-xs mt-0.5 line-clamp-1">{t.artist}</p>
      {recMeta ? (
        <p className="text-xs mt-0.5 flex items-center gap-1.5 flex-wrap">
          <span className="text-violet-400 font-semibold">✦ {recMeta.score}%</span>
          {recMeta.matchedTags.map(tag => <span key={tag} className="text-zinc-600">{tag}</span>)}
        </p>
      ) : (
        fmtCompact(t.listeners) && <p className="text-zinc-600 text-xs mt-0.5">{fmtCompact(t.listeners)} listeners</p>
      )}
    </a>
  );
}

type SortTab = 'popular' | 'trending' | 'new' | 'foryou';

const SORT_TABS: { key: SortTab; label: string }[] = [
  { key: 'popular',  label: 'Popular' },
  { key: 'trending', label: 'Trending' },
  { key: 'new',      label: 'New' },
  { key: 'foryou',   label: '✦ For You' },
];

const PAGE_SIZE = 20;

export default function TracksList() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [focused, setFocused] = useState(false);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const { uid } = useAuth();
  const [likedIds, setLikedIds] = useState<Set<number>>(new Set());
  const [sortTab, setSortTab] = useState<SortTab>('popular');
  const [recs, setRecs] = useState<Track[]>([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [recsLoaded, setRecsLoaded] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    fetch(`${API_BASE}/tracks`)
      .then(r => r.json())
      .then(setTracks)
      .catch(() => setError('Backend offline — run: uvicorn main:app --reload'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!uid) { setLikedIds(new Set()); return; }
    fetch(`${API_BASE}/likes/${uid}`)
      .then(r => r.json())
      .then(d => setLikedIds(new Set((d.tracks ?? []).map((t: any) => t.id as number))))
      .catch(() => {});
  }, [uid]);

  async function toggleLike(trackId: number) {
    if (!uid) return;
    const was = likedIds.has(trackId);
    setLikedIds(prev => { const n = new Set(prev); was ? n.delete(trackId) : n.add(trackId); return n; });
    try {
      await fetch(`${API_BASE}/likes/${uid}/track/${trackId}`, { method: 'POST' });
      setRecsLoaded(false);
    } catch {
      setLikedIds(prev => { const n = new Set(prev); was ? n.add(trackId) : n.delete(trackId); return n; });
    }
  }

  useEffect(() => {
    if (!uid || recsLoaded) return;
    setRecsLoading(true);
    fetch(`${API_BASE}/recommendations/${uid}/tracks`)
      .then(r => r.json())
      .then(d => { setRecs(d); setRecsLoaded(true); })
      .catch(() => setRecsLoaded(true))
      .finally(() => setRecsLoading(false));
  }, [uid, recsLoaded]);

  const recMap = useMemo(() =>
    new Map((recs as any[]).map(r => [r.id, { score: r._score, matchedTags: r._matched_tags || [] }])),
    [recs]
  );

  useEffect(() => { setVisibleCount(PAGE_SIZE); }, [sortTab, search, selectedGenres]);

  const allGenres = useMemo(() => {
    const set = new Set<string>();
    tracks.forEach(t => {
      (t.genres || []).forEach(g => set.add(g));
    });
    return [...set].sort();
  }, [tracks]);

  function toggleGenre(g: string) {
    setSelectedGenres(prev =>
      prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g]
    );
  }

  const ql = search.toLowerCase();
  const filtered = tracks.filter(t => {
    const matchSearch = !search ||
      t.name.toLowerCase().includes(ql) ||
      t.artist.toLowerCase().includes(ql) ||
      t.genres.some(g => g.toLowerCase().includes(ql)) ||
      t.tags.some(tag => tag.toLowerCase().includes(ql));
    const trackGenres = t.genres || [];
    const matchGenre = selectedGenres.length === 0 ||
      selectedGenres.some(g => trackGenres.includes(g));
    return matchSearch && matchGenre;
  });

  const sorted = useMemo(() => {
    if (sortTab === 'trending') return [...filtered].sort((a, b) => (b.playcount || 0) - (a.playcount || 0));
    if (sortTab === 'new')      return [...filtered].sort((a, b) => b.id - a.id);
    return [...filtered].sort((a, b) => (b.listeners || 0) - (a.listeners || 0));
  }, [filtered, sortTab]);

  const filteredRecs = useMemo(() => {
    if (selectedGenres.length === 0) return recs;
    return recs.filter((r: any) => (r.genres || []).some((g: string) => selectedGenres.includes(g)));
  }, [recs, selectedGenres]);

  if (loading) return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {Array.from({ length: 15 }).map((_, i) => (
        <div key={i} className="animate-pulse" style={{ animationDelay: `${i * 50}ms` }}>
          <div className="aspect-square rounded-xl bg-zinc-900 mb-2.5" />
          <div className="h-3 bg-zinc-900 rounded w-3/4 mb-1.5" />
          <div className="h-2.5 bg-zinc-900 rounded w-1/2 mb-1" />
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
      {/* Sort tabs */}
      <div className="flex items-center gap-1 mb-5 border-b border-zinc-800/60 pb-1">
        {SORT_TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setSortTab(tab.key)}
            className={`relative px-3 py-1.5 rounded-t-lg text-sm font-medium transition-all duration-200 ${
              sortTab === tab.key
                ? 'text-violet-300'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {tab.label}
            {sortTab === tab.key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-violet-400 rounded-full" />
            )}
          </button>
        ))}
      </div>

      {sortTab !== 'foryou' && (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-zinc-500 text-sm">
              {sorted.length < tracks.length
                ? <><span className="text-white font-medium">{sorted.length}</span> of {tracks.length}</>
                : <>{tracks.length} tracks</>}
            </p>
            <input
              type="text" placeholder="Search…" value={search}
              onChange={e => setSearch(e.target.value)}
              onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
              className="bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500 w-56 transition-all duration-300"
              style={{ boxShadow: focused ? '0 0 0 3px rgba(139,92,246,0.15)' : 'none' }}
            />
          </div>
          <GenreFilters genres={allGenres} selected={selectedGenres} onToggle={toggleGenre}
            color={{ active: 'bg-violet-500 border-violet-500 text-white', pill: 'border-zinc-700 text-zinc-400 hover:border-violet-600 hover:text-violet-300' }}
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {sorted.slice(0, visibleCount).map((t, i) => (
              <TrackCard key={t.id} t={t} index={i} liked={likedIds.has(t.id)} onToggle={uid ? toggleLike : undefined} recMeta={recMap.get(t.id)} />
            ))}
          </div>
          {visibleCount < sorted.length && (
            <div className="mt-8 flex flex-col items-center gap-2">
              <p className="text-zinc-600 text-xs">{visibleCount} of {sorted.length}</p>
              <button onClick={() => setVisibleCount(v => v + PAGE_SIZE)}
                className="px-6 py-2.5 rounded-xl border border-zinc-700 text-zinc-300 text-sm font-medium hover:border-violet-500 hover:text-violet-300 transition-all duration-200">
                Load more
              </button>
            </div>
          )}
        </>
      )}

      {sortTab === 'foryou' && (
        <div>
          {!uid && (
            <div className="py-20 text-center">
              <p className="text-zinc-500 text-sm">Sign in to get personalized recommendations</p>
            </div>
          )}
          {uid && recsLoading && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="aspect-square rounded-xl bg-zinc-900 mb-2.5" />
                  <div className="h-3 bg-zinc-900 rounded w-3/4 mb-1.5" />
                  <div className="h-2.5 bg-zinc-900 rounded w-1/2" />
                </div>
              ))}
            </div>
          )}
          {uid && !recsLoading && recs.length === 0 && (
            <div className="py-20 text-center">
              <p className="text-zinc-400 text-sm mb-1">Like some tracks to get recommendations</p>
              <p className="text-zinc-600 text-xs">The more you like — the better the results</p>
            </div>
          )}
          {uid && !recsLoading && recs.length > 0 && (
            <>
              <GenreFilters genres={allGenres} selected={selectedGenres} onToggle={toggleGenre}
                color={{ active: 'bg-violet-500 border-violet-500 text-white', pill: 'border-zinc-700 text-zinc-400 hover:border-violet-600 hover:text-violet-300' }}
              />
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {filteredRecs.slice(0, visibleCount).map((t: any, i: number) => (
                  <TrackCard key={t.id} t={t} index={i} liked={likedIds.has(t.id)} onToggle={uid ? toggleLike : undefined}
                    recMeta={{ score: t._score, matchedTags: t._matched_tags || [] }} />
                ))}
              </div>
              {visibleCount < filteredRecs.length && (
                <div className="mt-8 flex flex-col items-center gap-2">
                  <p className="text-zinc-600 text-xs">{visibleCount} of {filteredRecs.length}</p>
                  <button onClick={() => setVisibleCount(v => v + PAGE_SIZE)}
                    className="px-6 py-2.5 rounded-xl border border-zinc-700 text-zinc-300 text-sm font-medium hover:border-violet-500 hover:text-violet-300 transition-all duration-200">
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
