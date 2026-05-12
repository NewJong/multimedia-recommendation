import { useEffect, useState } from 'react';
import FriendButton from './FriendButton';
import { API_BASE } from '../lib/api';
import { VisitorSocialRow, type Socials } from './SocialLinks';

interface UserInfo {
  firebase_uid: string; name: string; email: string; photo_url: string | null;
  social_telegram?: string; social_instagram?: string;
  social_steam?: string; social_discord?: string; social_tiktok?: string;
}
interface Likes    { tracks: any[]; movies: any[]; games: any[] }
type Tab = 'music' | 'movies' | 'games';

function Avatar({ u, size = 'md' }: { u: UserInfo; size?: 'sm' | 'md' | 'lg' }) {
  const sz = size === 'lg' ? 'w-20 h-20 text-3xl' : size === 'sm' ? 'w-8 h-8 text-sm' : 'w-12 h-12 text-xl';
  return u.photo_url
    ? <img src={u.photo_url} alt={u.name} referrerPolicy="no-referrer" className={`${sz} rounded-full object-cover flex-shrink-0`} />
    : <div className={`${sz} rounded-full bg-zinc-800 flex items-center justify-center font-bold text-zinc-300 flex-shrink-0`}>{u.name?.[0] ?? '?'}</div>;
}

export default function PublicProfilePage({ uid }: { uid: string }) {
  const [user, setUser]   = useState<UserInfo | null>(null);
  const [likes, setLikes] = useState<Likes>({ tracks: [], movies: [], games: [] });
  const [loading, setLoading] = useState(true);
  const [tab, setTab]     = useState<Tab>('music');

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/users/${uid}`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/likes/${uid}`).then(r => r.json()),
    ]).then(([u, l]) => {
      setUser(u);
      if (l) {
        setLikes(l);
        if (l.tracks?.length)      setTab('music');
        else if (l.movies?.length) setTab('movies');
        else if (l.games?.length)  setTab('games');
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, [uid]);

  if (loading) return <div className="max-w-4xl mx-auto px-6 py-20 text-center text-zinc-600">Loading...</div>;
  if (!user)   return <div className="max-w-4xl mx-auto px-6 py-20 text-center text-zinc-500">User not found.</div>;

  const total = likes.tracks.length + likes.movies.length + likes.games.length;

  const tabs = [
    { key: 'music'  as Tab, label: 'Music',  count: likes.tracks.length,  color: 'text-violet-300 bg-violet-500/12 border-violet-500/30',   dot: 'bg-violet-400' },
    { key: 'movies' as Tab, label: 'Movies', count: likes.movies.length,  color: 'text-rose-300 bg-rose-500/12 border-rose-500/30',         dot: 'bg-rose-400' },
    { key: 'games'  as Tab, label: 'Games',  count: likes.games.length,   color: 'text-emerald-300 bg-emerald-500/12 border-emerald-500/30', dot: 'bg-emerald-400' },
  ];

  return (
    <div className="max-w-4xl mx-auto px-6 pt-8 pb-16">

      {/* Header — photo left, info right */}
      <div className="flex items-center gap-5 mb-8">
        <Avatar u={user} size="lg" />
        <div className="min-w-0">
          <h1 className="text-xl font-bold text-white leading-tight">{user.name}</h1>
          <p className="text-zinc-500 text-sm mt-0.5 mb-2">
            {total > 0 ? `${total} liked item${total !== 1 ? 's' : ''}` : 'No liked items yet'}
          </p>
          <VisitorSocialRow socials={{
            social_telegram:  user.social_telegram,
            social_instagram: user.social_instagram,
            social_steam:     user.social_steam,
            social_discord:   user.social_discord,
            social_tiktok:    user.social_tiktok,
          }} />
          <div className="mt-3">
            <FriendButton targetUid={uid} />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex justify-center gap-2 mb-8">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`relative flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition-all duration-200 ${
              tab === t.key ? t.color + ' border-current' : 'text-zinc-500 border-transparent hover:text-zinc-300 hover:bg-zinc-800/60'
            }`}>
            {tab === t.key && <span className={`absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full ${t.dot}`} />}
            {t.label}
            {t.count > 0 && <span className={`text-xs px-1.5 py-0.5 rounded-md ${tab === t.key ? 'bg-white/10' : 'bg-zinc-800 text-zinc-500'}`}>{t.count}</span>}
          </button>
        ))}
      </div>

      {/* Grid */}
      {total === 0 && <p className="text-zinc-600 text-sm text-center py-16">No liked items yet</p>}

      {tab === 'music' && likes.tracks.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {likes.tracks.map((t: any) => (
            <a key={t.id} href={`/music/${t.id}`} className="group block">
              <div className="aspect-square rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 group-hover:border-violet-500/40 transition-colors">
                {t.image_url ? <img src={t.image_url} alt={t.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" /> : <div className="w-full h-full flex items-center justify-center text-4xl">🎵</div>}
              </div>
              <p className="mt-2 text-sm font-medium text-white truncate group-hover:text-violet-200 transition-colors">{t.name}</p>
              <p className="text-xs text-zinc-500 truncate">{t.artist}</p>
            </a>
          ))}
        </div>
      )}

      {tab === 'movies' && likes.movies.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {likes.movies.map((m: any) => (
            <a key={m.id} href={`/movies/${m.id}`} className="group block">
              <div className="aspect-square rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 group-hover:border-rose-500/40 transition-colors">
                {m.poster_url ? <img src={m.poster_url} alt={m.title} className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-300" /> : <div className="w-full h-full flex items-center justify-center text-4xl">🎬</div>}
              </div>
              <p className="mt-2 text-sm font-medium text-white truncate group-hover:text-rose-200 transition-colors">{m.title}</p>
              <p className="text-xs text-zinc-500">{m.release_year || ''}</p>
            </a>
          ))}
        </div>
      )}

      {tab === 'games' && likes.games.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {likes.games.map((g: any) => (
            <a key={g.id} href={`/games/${g.id}`} className="group block">
              <div className="aspect-square rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 group-hover:border-emerald-500/40 transition-colors">
                {g.poster_url ? <img src={g.poster_url} alt={g.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" /> : <div className="w-full h-full flex items-center justify-center text-4xl">🎮</div>}
              </div>
              <p className="mt-2 text-sm font-medium text-white truncate group-hover:text-emerald-200 transition-colors">{g.title}</p>
              <p className="text-xs text-zinc-500">{g.release_year || ''}</p>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
