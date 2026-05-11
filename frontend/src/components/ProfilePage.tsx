import { useEffect, useState } from 'react';
import { signInWithPopup } from 'firebase/auth';
import { Heart } from 'lucide-react';
import type { User } from 'firebase/auth';
import { auth, googleProvider } from '../lib/firebase';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';

interface Likes { tracks: any[]; movies: any[]; games: any[] }
type Tab = 'music' | 'movies' | 'games' | 'friends';

interface FriendUser { firebase_uid: string; name: string; email: string; photo_url: string | null }

function UserAvatar({ u, size = 'sm' }: { u: FriendUser; size?: 'sm' | 'md' }) {
  const sz = size === 'md' ? 'w-10 h-10 text-base' : 'w-8 h-8 text-sm';
  return u.photo_url
    ? <img src={u.photo_url} alt={u.name} referrerPolicy="no-referrer" className={`${sz} rounded-full object-cover flex-shrink-0`} />
    : <div className={`${sz} rounded-full bg-zinc-700 flex items-center justify-center font-semibold text-zinc-300 flex-shrink-0`}>{u.name?.[0] ?? '?'}</div>;
}

const TABS: { key: Tab; label: string; active: string; dot: string }[] = [
  { key: 'music',   label: 'Music',   active: 'text-violet-300 bg-violet-500/12 border-violet-500/30',   dot: 'bg-violet-400' },
  { key: 'movies',  label: 'Movies',  active: 'text-rose-300 bg-rose-500/12 border-rose-500/30',         dot: 'bg-rose-400' },
  { key: 'games',   label: 'Games',   active: 'text-emerald-300 bg-emerald-500/12 border-emerald-500/30', dot: 'bg-emerald-400' },
  { key: 'friends', label: 'Friends', active: 'text-sky-300 bg-sky-500/12 border-sky-500/30',            dot: 'bg-sky-400' },
];


function TrackCard({ t, onUnlike }: { t: any; onUnlike: (id: number) => void }) {
  const genres: string[] = Array.isArray(t.genres) ? t.genres.slice(0, 2) : [];
  return (
    <a href={`/music/${t.id}`} className="group relative block">
      <div className="relative aspect-square rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 group-hover:border-violet-500/40 transition-colors">
        {t.image_url
          ? <img src={t.image_url} alt={t.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          : <div className="w-full h-full flex items-center justify-center text-4xl">🎵</div>
        }
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3">
          {genres.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-1.5">
              {genres.map(g => <span key={g} className="text-xs bg-violet-500/30 text-violet-200 border border-violet-500/30 rounded-full px-2 py-0.5">{g}</span>)}
            </div>
          )}
          <p className="text-zinc-300 text-xs font-medium truncate">{t.artist}</p>
          {t.listeners > 0 && <p className="text-zinc-500 text-xs">{t.listeners >= 1_000_000 ? `${(t.listeners/1_000_000).toFixed(1)}M` : `${Math.round(t.listeners/1000)}K`} listeners</p>}
        </div>
        {/* Unlike button */}
        <button
          onClick={e => { e.preventDefault(); e.stopPropagation(); onUnlike(t.id); }}
          className="absolute top-2 right-2 z-10 p-1.5 rounded-full border border-zinc-700 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:border-violet-400"
        >
          <Heart size={16} className="text-violet-400" fill="currentColor" />
        </button>
      </div>
      <p className="mt-2 text-sm font-medium text-white truncate group-hover:text-violet-200 transition-colors">{t.name}</p>
      <p className="text-xs text-zinc-500 truncate">{t.artist}</p>
    </a>
  );
}

function MovieCard({ m, onUnlike }: { m: any; onUnlike: (id: number) => void }) {
  const genres: string[] = Array.isArray(m.genres) ? m.genres.slice(0, 2) : [];
  return (
    <a href={`/movies/${m.id}`} className="group relative block">
      <div className="relative aspect-square rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 group-hover:border-rose-500/40 transition-colors">
        {m.poster_url
          ? <img src={m.poster_url} alt={m.title} className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-300" />
          : <div className="w-full h-full flex items-center justify-center text-4xl">🎬</div>
        }
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3">
          {genres.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-1.5">
              {genres.map(g => <span key={g} className="text-xs bg-rose-500/30 text-rose-200 border border-rose-500/30 rounded-full px-2 py-0.5">{g}</span>)}
            </div>
          )}
          {m.director && <p className="text-zinc-300 text-xs font-medium truncate">{m.director}</p>}
          {m.rating > 0 && <p className="text-zinc-500 text-xs">★ {m.rating.toFixed(1)}</p>}
        </div>
        {m.rating > 0 && (
          <div className="absolute top-2 left-2 bg-black/75 rounded-md px-1.5 py-0.5 flex items-center gap-1">
            <span className="text-yellow-400 text-xs">★</span>
            <span className="text-white text-xs font-semibold">{m.rating.toFixed(1)}</span>
          </div>
        )}
        {/* Unlike button */}
        <button
          onClick={e => { e.preventDefault(); e.stopPropagation(); onUnlike(m.id); }}
          className="absolute top-2 right-2 z-10 p-1.5 rounded-full border border-zinc-700 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:border-rose-400"
        >
          <Heart size={16} className="text-rose-400" fill="currentColor" />
        </button>
      </div>
      <p className="mt-2 text-sm font-medium text-white truncate group-hover:text-rose-200 transition-colors">{m.title}</p>
      <p className="text-xs text-zinc-500">{m.release_year || ''}</p>
    </a>
  );
}

function GameCard({ g, onUnlike }: { g: any; onUnlike: (id: number) => void }) {
  const genres: string[] = Array.isArray(g.genres) ? g.genres.slice(0, 2) : [];
  return (
    <a href={`/games/${g.id}`} className="group relative block">
      <div className="relative aspect-square rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 group-hover:border-emerald-500/40 transition-colors">
        {g.poster_url
          ? <img src={g.poster_url} alt={g.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          : <div className="w-full h-full flex items-center justify-center text-4xl">🎮</div>
        }
        {/* Hover overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3">
          {genres.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-1.5">
              {genres.map(genre => <span key={genre} className="text-xs bg-emerald-500/30 text-emerald-200 border border-emerald-500/30 rounded-full px-2 py-0.5">{genre}</span>)}
            </div>
          )}
          <div className="flex items-center gap-2">
            {g.rating > 0 && <p className="text-zinc-300 text-xs">★ {g.rating.toFixed(1)}</p>}
            {g.metacritic > 0 && <p className="text-zinc-500 text-xs">MC {g.metacritic}</p>}
          </div>
        </div>
        {/* Unlike button — bottom-right inside image */}
        <button
          onClick={e => { e.preventDefault(); e.stopPropagation(); onUnlike(g.id); }}
          className="absolute bottom-2 right-2 z-10 p-1.5 rounded-full border border-zinc-700 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:border-emerald-400"
        >
          <Heart size={16} className="text-emerald-400" fill="currentColor" />
        </button>
      </div>
      <p className="mt-2 text-sm font-medium text-white truncate group-hover:text-emerald-200 transition-colors">{g.title}</p>
      <p className="text-xs text-zinc-500">{g.release_year || ''}</p>
    </a>
  );
}

export default function ProfilePage() {
  const { user, loading: authLoading } = useAuth();
  const [likes, setLikes]             = useState<Likes>({ tracks: [], movies: [], games: [] });
  const [likesLoading, setLikesLoading] = useState(false);
  const [tab, setTab]                 = useState<Tab>('music');
  const [friends, setFriends]         = useState<FriendUser[]>([]);
  const [requests, setRequests]       = useState<FriendUser[]>([]);
  const [search, setSearch]           = useState('');
  const [searchResults, setSearchRes] = useState<FriendUser[]>([]);

  useEffect(() => {
    if (authLoading || !user) return;
    setLikesLoading(true);
    fetch(`${API_BASE}/likes/${user.uid}`)
      .then(r => r.json())
      .then((data: Likes) => {
        setLikes(data);
        if (data.tracks.length)      setTab('music');
        else if (data.movies.length) setTab('movies');
        else if (data.games.length)  setTab('games');
      })
      .catch(() => {})
      .finally(() => setLikesLoading(false));
    Promise.all([
      fetch(`${API_BASE}/friends/${user.uid}`).then(r => r.json()),
      fetch(`${API_BASE}/friends/${user.uid}/requests`).then(r => r.json()),
    ]).then(([f, rq]) => { setFriends(f ?? []); setRequests(rq ?? []); }).catch(() => {});
  }, [authLoading, user?.uid]);

  if (authLoading) return (
    <div className="py-20 text-center text-zinc-600">Loading...</div>
  );

  if (!user) return (
    <div className="py-24 text-center">
      <div className="text-zinc-700 text-5xl mb-5">♡</div>
      <h1 className="text-2xl font-bold text-white mb-2">Your Profile</h1>
      <p className="text-zinc-500 mb-8">Sign in to save and view your liked items</p>
      <button
        onClick={() => signInWithPopup(auth, googleProvider)}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-zinc-700 hover:border-zinc-500 text-sm text-zinc-200 transition-all"
      >
        <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        Sign in with Google
      </button>
    </div>
  );

  async function unlike(itemType: 'track' | 'movie' | 'game', itemId: number) {
    setLikes(prev => ({
      tracks: itemType === 'track' ? prev.tracks.filter(t => t.id !== itemId) : prev.tracks,
      movies: itemType === 'movie' ? prev.movies.filter(m => m.id !== itemId) : prev.movies,
      games:  itemType === 'game'  ? prev.games.filter(g => g.id !== itemId)  : prev.games,
    }));
    if (user) {
      fetch(`${API_BASE}/likes/${user.uid}/${itemType}/${itemId}`, { method: 'POST' }).catch(() => {});
    }
  }

  const counts = { music: likes.tracks.length, movies: likes.movies.length, games: likes.games.length };
  const total  = counts.music + counts.movies + counts.games;

  async function doSearch(q: string) {
    setSearch(q);
    if (q.length < 2) { setSearchRes([]); return; }
    try {
      const r = await fetch(`${API_BASE}/users/search?q=${encodeURIComponent(q)}`);
      const data = await r.json();
      setSearchRes(data.filter((u: FriendUser) => u.firebase_uid !== user?.uid));
    } catch {}
  }

  async function acceptReq(fromUid: string) {
    if (!user) return;
    await fetch(`${API_BASE}/friends/${user.uid}/accept/${fromUid}`, { method: 'POST' }).catch(() => {});
    const accepted = requests.find(r => r.firebase_uid === fromUid);
    setRequests(prev => prev.filter(r => r.firebase_uid !== fromUid));
    if (accepted) setFriends(prev => [...prev, accepted]);
  }

  async function rejectReq(fromUid: string) {
    if (!user) return;
    await fetch(`${API_BASE}/friends/${user.uid}/${fromUid}`, { method: 'DELETE' }).catch(() => {});
    setRequests(prev => prev.filter(r => r.firebase_uid !== fromUid));
  }

  async function removeFriend(friendUid: string) {
    if (!user) return;
    await fetch(`${API_BASE}/friends/${user.uid}/${friendUid}`, { method: 'DELETE' }).catch(() => {});
    setFriends(prev => prev.filter(f => f.firebase_uid !== friendUid));
  }

  return (
    <div className="max-w-4xl mx-auto px-6 pt-8 pb-16">

      {/* User header — centered */}
      <div className="flex flex-col items-center text-center mb-8">
        {user.photoURL
          ? <img src={user.photoURL} alt="" referrerPolicy="no-referrer" className="w-20 h-20 rounded-full ring-2 ring-zinc-700 mb-3" />
          : <div className="w-20 h-20 rounded-full bg-zinc-800 flex items-center justify-center text-3xl font-bold text-zinc-300 mb-3">{user.displayName?.[0] ?? '?'}</div>
        }
        <h1 className="text-xl font-bold text-white">{user.displayName}</h1>
        <p className="text-zinc-500 text-sm mt-0.5">{user.email}</p>
        {!likesLoading && total > 0 && (
          <p className="text-zinc-600 text-xs mt-1">{total} liked item{total !== 1 ? 's' : ''}</p>
        )}
      </div>

      {/* Tabs — centered */}
      <div className="flex justify-center gap-2 mb-8">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`relative flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition-all duration-200 ${
              tab === t.key
                ? t.active + ' border-current'
                : 'text-zinc-500 border-transparent hover:text-zinc-300 hover:bg-zinc-800/60'
            }`}
          >
            {tab === t.key && (
              <span className={`absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full ${t.dot}`} />
            )}
            {t.label}
            {(() => {
              const n = t.key === 'friends' ? requests.length : counts[t.key as keyof typeof counts] ?? 0;
              return n > 0 ? <span className={`text-xs px-1.5 py-0.5 rounded-md ${tab === t.key ? 'bg-white/10' : 'bg-zinc-800 text-zinc-500'}`}>{n}</span> : null;
            })()}
          </button>
        ))}
      </div>

      {/* Skeleton */}
      {likesLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {[1,2,3,4,5,6,7,8].map(i => (
            <div key={i}>
              <div className="aspect-square rounded-xl bg-zinc-900 animate-pulse" />
              <div className="mt-2 h-3 bg-zinc-900 rounded animate-pulse w-3/4" />
              <div className="mt-1 h-3 bg-zinc-900 rounded animate-pulse w-1/2" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!likesLoading && total === 0 && (
        <div className="text-center py-20">
          <p className="text-zinc-700 text-5xl mb-4">♡</p>
          <p className="text-zinc-500 text-sm">
            No liked items yet — browse{' '}
            <a href="/music" className="text-violet-400 hover:underline">Music</a>,{' '}
            <a href="/movies" className="text-rose-400 hover:underline">Movies</a> or{' '}
            <a href="/games" className="text-emerald-400 hover:underline">Games</a>!
          </p>
        </div>
      )}

      {/* Grid */}
      {!likesLoading && tab === 'music' && (
        counts.music === 0
          ? <p className="text-zinc-600 text-sm py-12 text-center">No liked tracks yet</p>
          : <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {likes.tracks.map((t: any) => <TrackCard key={t.id} t={t} onUnlike={id => unlike('track', id)} />)}
            </div>
      )}

      {!likesLoading && tab === 'movies' && (
        counts.movies === 0
          ? <p className="text-zinc-600 text-sm py-12 text-center">No liked movies yet</p>
          : <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {likes.movies.map((m: any) => <MovieCard key={m.id} m={m} onUnlike={id => unlike('movie', id)} />)}
            </div>
      )}

      {!likesLoading && tab === 'games' && (
        counts.games === 0
          ? <p className="text-zinc-600 text-sm py-12 text-center">No liked games yet</p>
          : <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {likes.games.map((g: any) => <GameCard key={g.id} g={g} onUnlike={id => unlike('game', id)} />)}
            </div>
      )}

      {/* Friends tab */}
      {tab === 'friends' && (
        <div className="space-y-8">

          {/* User search */}
          <div>
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-3">Find people</p>
            <input
              type="text"
              placeholder="Search by name or email…"
              value={search}
              onChange={e => doSearch(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-sky-500 transition-colors"
            />
            {searchResults.length > 0 && (
              <div className="mt-2 space-y-1">
                {searchResults.map(u => (
                  <a key={u.firebase_uid} href={`/profile/${u.firebase_uid}`}
                    className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 hover:border-sky-500/40 hover:bg-sky-500/5 transition-all">
                    <UserAvatar u={u} size="md" />
                    <div className="min-w-0">
                      <p className="text-white text-sm font-medium truncate">{u.name}</p>
                      <p className="text-zinc-500 text-xs truncate">{u.email}</p>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>

          {/* Incoming requests */}
          {requests.length > 0 && (
            <div>
              <p className="text-zinc-500 text-xs uppercase tracking-wider mb-3">Incoming requests · {requests.length}</p>
              <div className="space-y-2">
                {requests.map(u => (
                  <div key={u.firebase_uid} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                    <a href={`/profile/${u.firebase_uid}`} className="flex items-center gap-3 flex-1 min-w-0 hover:opacity-80 transition-opacity">
                      <UserAvatar u={u} size="md" />
                      <p className="text-white text-sm font-medium truncate">{u.name}</p>
                    </a>
                    <div className="flex gap-2 flex-shrink-0">
                      <button onClick={() => acceptReq(u.firebase_uid)}
                        className="px-3 py-1.5 rounded-lg bg-sky-500/15 hover:bg-sky-500/25 border border-sky-500/30 text-sky-300 text-xs font-medium transition-all">
                        Accept
                      </button>
                      <button onClick={() => rejectReq(u.firebase_uid)}
                        className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-400 text-xs font-medium transition-all">
                        Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Friends list */}
          <div>
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-3">Friends · {friends.length}</p>
            {friends.length === 0
              ? <p className="text-zinc-600 text-sm text-center py-8">No friends yet — search for people above</p>
              : <div className="space-y-2">
                  {friends.map(u => (
                    <div key={u.firebase_uid} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 hover:border-sky-500/30 transition-colors group">
                      <a href={`/profile/${u.firebase_uid}`} className="flex items-center gap-3 flex-1 min-w-0">
                        <UserAvatar u={u} size="md" />
                        <div className="min-w-0">
                          <p className="text-white text-sm font-medium truncate group-hover:text-sky-200 transition-colors">{u.name}</p>
                          <p className="text-zinc-500 text-xs truncate">{u.email}</p>
                        </div>
                      </a>
                      <button onClick={() => removeFriend(u.firebase_uid)}
                        className="flex-shrink-0 px-3 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 bg-zinc-800 hover:bg-red-500/10 border border-zinc-700 hover:border-red-500/30 text-zinc-500 hover:text-red-400 text-xs transition-all">
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
            }
          </div>

        </div>
      )}

    </div>
  );
}
