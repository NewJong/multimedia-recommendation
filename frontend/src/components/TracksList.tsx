import { useMemo, useEffect, useState } from 'react';
import { Heart } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useLikes } from '../hooks/useLikes';
import { useRecommendations } from '../hooks/useRecommendations';
import { API_BASE } from '../lib/api';
import { cacheGet, cachedFetch } from '../lib/cache';
import { fmtCompact } from '../lib/format';
import GenreFilters from './list/GenreFilters';
import LoadMore from './list/LoadMore';
import SortTabs from './list/SortTabs';
import SearchWithAI from './list/SearchWithAI';

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
  const cachedTracks = cacheGet<Track[]>('catalog:tracks');
  const [tracks, setTracks] = useState<Track[]>(cachedTracks ?? []);
  const [loading, setLoading] = useState(cachedTracks === null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const { uid } = useAuth();
  const { likedIds, toggleLike } = useLikes('track', uid);
  const [sortTab, setSortTab] = useState<SortTab>('popular');
  const { recs, loading: recsLoading } = useRecommendations<Track & { _score: number; _matched_tags?: string[] }>('track', uid);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    if (cachedTracks !== null) return;  
    cachedFetch<Track[]>('catalog:tracks', `${API_BASE}/tracks`)
      .then(setTracks)
      .catch(() => setError('Backend offline — run: uvicorn main:app --reload'))
      .finally(() => setLoading(false));
  }, []);

  const recMap = useMemo(() =>
    new Map(recs.map(r => [r.id, { score: r._score, matchedTags: r._matched_tags || [] }])),
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
    return recs.filter(r => (r.genres || []).some((g: string) => selectedGenres.includes(g)));
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
      <SortTabs tabs={SORT_TABS} current={sortTab} onChange={setSortTab}
        activeText="text-violet-300" activeBar="bg-violet-400" />

      {sortTab !== 'foryou' && (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-zinc-500 text-sm">
              {sorted.length < tracks.length
                ? <><span className="text-white font-medium">{sorted.length}</span> of {tracks.length}</>
                : <>{tracks.length} tracks</>}
            </p>
            <SearchWithAI value={search} onChange={setSearch}
              focusBorder="focus-within:border-violet-500"
              focusRing="0 0 0 3px rgba(139,92,246,0.15)"
              aiActiveCls="bg-violet-500/15 text-violet-300 hover:bg-violet-500/25 border border-violet-500/30" />
          </div>
          <GenreFilters genres={allGenres} selected={selectedGenres} onToggle={toggleGenre}
            color={{ active: 'bg-violet-500 border-violet-500 text-white', pill: 'border-zinc-700 text-zinc-400 hover:border-violet-600 hover:text-violet-300' }}
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {sorted.slice(0, visibleCount).map((t, i) => (
              <TrackCard key={t.id} t={t} index={i} liked={likedIds.has(t.id)} onToggle={uid ? toggleLike : undefined} recMeta={recMap.get(t.id)} />
            ))}
          </div>
          <LoadMore visible={Math.min(visibleCount, sorted.length)} total={sorted.length}
            onMore={() => setVisibleCount(v => v + PAGE_SIZE)}
            hoverColor="hover:border-violet-500 hover:text-violet-300" />
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
                {filteredRecs.slice(0, visibleCount).map((t, i) => (
                  <TrackCard key={t.id} t={t} index={i} liked={likedIds.has(t.id)} onToggle={uid ? toggleLike : undefined}
                    recMeta={{ score: t._score, matchedTags: t._matched_tags || [] }} />
                ))}
              </div>
              <LoadMore visible={Math.min(visibleCount, filteredRecs.length)} total={filteredRecs.length}
                onMore={() => setVisibleCount(v => v + PAGE_SIZE)}
                hoverColor="hover:border-violet-500 hover:text-violet-300" />
            </>
          )}
        </div>
      )}
    </div>
  );
}
