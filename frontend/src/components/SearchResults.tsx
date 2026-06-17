import { useState, useEffect } from 'react';
import { API_BASE } from '../lib/api';
import { thumbUrl } from '../lib/format';

interface Track { id: number; name: string; artist: string; genres: string[]; image_url: string; listeners: number; }
interface Movie { id: number; title: string; genres: string[]; poster_url: string; rating: number; release_year: number; director: string; }
interface Game  { id: number; title: string; genres: string[]; poster_url: string; rating: number; metacritic: number; release_year: number; }

interface Results {
  tracks: Track[];
  movies: Movie[];
  games:  Game[];
  explanation: string | null;
}

function TrackCard({ t }: { t: Track }) {
  return (
    <a href={`/music/${t.id}`} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800/60 hover:border-violet-500/40 hover:bg-violet-500/5 transition-all group">
      {t.image_url
        ? <img src={t.image_url} alt={t.name} className="w-11 h-11 rounded-lg object-cover flex-shrink-0" />
        : <div className="w-11 h-11 rounded-lg bg-zinc-800 flex items-center justify-center text-xl flex-shrink-0">🎵</div>
      }
      <div className="min-w-0">
        <p className="text-white text-sm font-medium truncate group-hover:text-violet-300 transition-colors">{t.name}</p>
        <p className="text-zinc-500 text-xs truncate mt-0.5">{t.artist}</p>
        {t.genres?.length > 0 && <p className="text-zinc-600 text-xs truncate mt-0.5">{t.genres.slice(0,2).join(' · ')}</p>}
      </div>
    </a>
  );
}

function MovieCard({ m }: { m: Movie }) {
  return (
    <a href={`/movies/${m.id}`} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800/60 hover:border-rose-500/40 hover:bg-rose-500/5 transition-all group">
      {m.poster_url
        ? <img src={m.poster_url} alt={m.title} className="w-9 h-[52px] rounded-lg object-cover flex-shrink-0" />
        : <div className="w-9 h-[52px] rounded-lg bg-zinc-800 flex items-center justify-center text-xl flex-shrink-0">🎬</div>
      }
      <div className="min-w-0">
        <p className="text-white text-sm font-medium truncate group-hover:text-rose-300 transition-colors">{m.title}</p>
        <p className="text-zinc-500 text-xs mt-0.5">{m.release_year || '—'}</p>
        {m.rating > 0 && <p className="text-yellow-500 text-xs mt-0.5">★ {m.rating.toFixed(1)}</p>}
      </div>
    </a>
  );
}

function GameCard({ g }: { g: Game }) {
  return (
    <a href={`/games/${g.id}`} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800/60 hover:border-emerald-500/40 hover:bg-emerald-500/5 transition-all group">
      {g.poster_url
        ? <img src={thumbUrl(g.poster_url, 200) ?? ''} alt={g.title} loading="lazy" decoding="async" className="w-[72px] h-10 rounded-lg object-cover flex-shrink-0" />
        : <div className="w-[72px] h-10 rounded-lg bg-zinc-800 flex items-center justify-center text-xl flex-shrink-0">🎮</div>
      }
      <div className="min-w-0">
        <p className="text-white text-sm font-medium truncate group-hover:text-emerald-300 transition-colors">{g.title}</p>
        <p className="text-zinc-500 text-xs mt-0.5">{g.release_year || '—'}</p>
        {g.rating > 0 && <p className="text-yellow-500 text-xs mt-0.5">★ {g.rating.toFixed(1)}</p>}
      </div>
    </a>
  );
}

function Section({ label, color, count, children }: { label: string; color: string; count: number; children: React.ReactNode }) {
  if (count === 0) return null;
  return (
    <div>
      <div className="flex items-center gap-2.5 mb-3">
        <span className={`text-xs font-semibold uppercase tracking-widest ${color}`}>{label}</span>
        <span className="text-zinc-700 text-xs">{count} result{count !== 1 ? 's' : ''}</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {children}
      </div>
    </div>
  );
}

type Domain = 'movies' | 'music' | 'games';
const ALL_DOMAINS: Domain[] = ['movies', 'music', 'games'];

export default function SearchResults() {
  const [inputVal, setInputVal] = useState('');
  const [q, setQ]               = useState('');
  const [aiMode, setAiMode]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [results, setResults]   = useState<Results | null>(null);
  const [aiError, setAiError]   = useState<string | null>(null);
  const [focused, setFocused]   = useState(false);
  const [filter, setFilter]     = useState<Set<Domain>>(new Set(ALL_DOMAINS));

  function toggleDomain(d: Domain) {
    setFilter(prev => {
      if (prev.size === 3) return new Set([d]);         
      const next = new Set(prev);
      if (next.has(d)) {
        next.delete(d);
        return next.size === 0 ? new Set(ALL_DOMAINS) : next;
      }
      next.add(d);
      return next.size === 3 ? new Set(ALL_DOMAINS) : next;
    });
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const initial = params.get('q') || '';
    setInputVal(initial);
    setQ(initial);
    if (params.get('ai') === '1') setAiMode(true);
  }, []);

  useEffect(() => {
    if (!q.trim()) { setResults(null); return; }
    setLoading(true);
    setAiError(null);
    fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q, ai: aiMode }),
    })
      .then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.detail); });
        return r.json();
      })
      .then(setResults)
      .catch(e => setAiError(e.message))
      .finally(() => setLoading(false));
  }, [q, aiMode]);

  function submit() {
    const val = inputVal.trim();
    if (!val) return;
    setQ(val);
    window.history.replaceState(null, '', `/search?q=${encodeURIComponent(val)}${aiMode ? '&ai=1' : ''}`);
  }

  const total = results ? results.tracks.length + results.movies.length + results.games.length : 0;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">

      <div className="flex items-center gap-3 mb-8">
        <a href="/" className="text-zinc-600 hover:text-zinc-300 transition-colors flex-shrink-0">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </a>

        <div
          className="flex-1 flex items-center bg-zinc-900 border border-zinc-800 rounded-2xl transition-colors"
          style={{ boxShadow: focused ? '0 0 0 3px rgba(139,92,246,0.12)' : 'none', borderColor: focused ? 'rgb(113,113,122)' : undefined }}
        >
          <svg className="ml-4 text-zinc-600 w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
          </svg>
          <input
            type="text"
            value={inputVal}
            onChange={e => setInputVal(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder={aiMode ? 'Describe what you want to watch, play or listen to…' : 'Search by title, artist, genre…'}
            className="flex-1 bg-transparent px-3 py-3.5 text-white placeholder-zinc-600 focus:outline-none text-sm"
            autoFocus
          />

          <button
            onClick={() => { setAiMode(v => !v); setResults(null); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl mr-1 text-xs font-semibold transition-all flex-shrink-0 ${
              aiMode
                ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/>
            </svg>
            AI
          </button>

          <button
            onClick={submit}
            className="mr-1.5 px-3.5 py-1.5 bg-gradient-to-r from-violet-600 to-emerald-600 hover:from-violet-500 hover:to-emerald-500 text-white rounded-xl transition-all flex items-center gap-1.5 flex-shrink-0 text-xs font-semibold shadow"
          >
            Search
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </div>

      {results?.explanation && (
        <div className="mb-6 flex items-start gap-3 bg-violet-500/8 border border-violet-500/20 rounded-xl p-4">
          <svg className="w-4 h-4 text-violet-400 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/>
          </svg>
          <p className="text-violet-200 text-sm leading-relaxed">{results.explanation}</p>
        </div>
      )}

      {aiError && (
        <div className="mb-6 bg-red-950/30 border border-red-800/50 rounded-xl p-4 text-red-400 text-sm">{aiError}</div>
      )}

      {loading && (
        <div className="flex flex-col gap-4">
          {[1,2,3].map(s => (
            <div key={s}>
              <div className="h-3 bg-zinc-800 rounded w-20 mb-3 animate-pulse" />
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {[1,2,3].map(i => <div key={i} className="h-[62px] bg-zinc-900 rounded-xl animate-pulse" style={{ animationDelay: `${i*60}ms` }} />)}
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && results && total === 0 && (
        <div className="text-center py-16">
          <p className="text-zinc-500 text-sm">Nothing found for <span className="text-white">"{q}"</span></p>
          {!aiMode && <p className="text-zinc-700 text-xs mt-2">Try enabling AI mode for smarter search</p>}
        </div>
      )}

      {!loading && results && total > 0 && (
        <div className="flex flex-col gap-8">
          <div className="flex items-center justify-between gap-4 -mb-4 flex-wrap">
            <p className="text-zinc-600 text-xs">
              {total} result{total !== 1 ? 's' : ''} for <span className="text-zinc-400">"{q}"</span>
            </p>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setFilter(new Set(ALL_DOMAINS))}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  filter.size === 3 ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >All</button>
              {([
                { d: 'movies' as Domain, label: 'Movies', active: 'bg-rose-500/20 text-rose-300',    idle: 'text-zinc-500 hover:text-rose-400' },
                { d: 'music'  as Domain, label: 'Music',  active: 'bg-violet-500/20 text-violet-300', idle: 'text-zinc-500 hover:text-violet-400' },
                { d: 'games'  as Domain, label: 'Games',  active: 'bg-emerald-500/20 text-emerald-300', idle: 'text-zinc-500 hover:text-emerald-400' },
              ]).map(({ d, label, active, idle }) => (
                <button
                  key={d}
                  onClick={() => toggleDomain(d)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    filter.has(d) && filter.size < 3 ? active : idle
                  }`}
                >{label}</button>
              ))}
            </div>
          </div>

          {(() => {
            const cap = filter.size === 3 ? 3 : 9;
            const movies = results.movies.slice(0, cap);
            const tracks = results.tracks.slice(0, cap);
            const games  = results.games.slice(0, cap);
            return (
              <>
                {filter.has('movies') && (
                  <Section label="Movies" color="text-rose-400" count={movies.length}>
                    {movies.map(m => <MovieCard key={m.id} m={m} />)}
                  </Section>
                )}
                {filter.has('music') && (
                  <Section label="Music" color="text-violet-400" count={tracks.length}>
                    {tracks.map(t => <TrackCard key={t.id} t={t} />)}
                  </Section>
                )}
                {filter.has('games') && (
                  <Section label="Games" color="text-emerald-400" count={games.length}>
                    {games.map(g => <GameCard key={g.id} g={g} />)}
                  </Section>
                )}
              </>
            );
          })()}
        </div>
      )}

      {!loading && !results && !q && (
        <div className="text-center py-20">
          <p className="text-zinc-600 text-sm">Start typing to search across movies, music & games</p>
          {aiMode && <p className="text-violet-500/70 text-xs mt-2">AI mode on — describe what you feel like</p>}
        </div>
      )}

    </div>
  );
}
