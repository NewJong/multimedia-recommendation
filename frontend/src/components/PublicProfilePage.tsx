import { useEffect, useState } from 'react';
import FriendButton from './FriendButton';
import { API_BASE } from '../lib/api';
import { thumbUrl } from '../lib/format';
import { VisitorSocialRow } from './SocialLinks';
import { useAuth } from '../hooks/useAuth';

interface UserInfo {
  firebase_uid: string; name: string; email: string; photo_url: string | null;
  social_telegram?: string; social_instagram?: string;
  social_steam?: string; social_discord?: string; social_tiktok?: string;
}
interface Likes    { tracks: any[]; movies: any[]; games: any[] }
type Tab = 'music' | 'movies' | 'games';

interface CompareItem { id: number; title: string }
interface PickItem {
  id: number;
  title: string;
  poster_url?: string;
  image_url?: string;
  artist?: string;
  release_year?: number;
  score: number;
  matched_tags: string[];
}
interface CompareResult {
  insight: string;
  compatibility: number;
  name1: string;
  name2: string;
  common: { games: CompareItem[]; movies: CompareItem[]; tracks: CompareItem[] };
  picks:  { games: PickItem[];   movies: PickItem[];   tracks: PickItem[] };
  tags1: string[];
  tags2: string[];
}

function Avatar({ u, size = 'md' }: { u: UserInfo; size?: 'sm' | 'md' | 'lg' }) {
  const sz = size === 'lg' ? 'w-20 h-20 text-3xl' : size === 'sm' ? 'w-8 h-8 text-sm' : 'w-12 h-12 text-xl';
  return u.photo_url
    ? <img src={u.photo_url} alt={u.name} referrerPolicy="no-referrer" className={`${sz} rounded-full object-cover flex-shrink-0`} />
    : <div className={`${sz} rounded-full bg-zinc-800 flex items-center justify-center font-bold text-zinc-300 flex-shrink-0`}>{u.name?.[0] ?? '?'}</div>;
}

export default function PublicProfilePage({ uid }: { uid: string }) {
  const { uid: myUid } = useAuth();
  const [user, setUser]   = useState<UserInfo | null>(null);
  const [likes, setLikes] = useState<Likes>({ tracks: [], movies: [], games: [] });
  const [loading, setLoading] = useState(true);
  const [tab, setTab]     = useState<Tab>('music');
  const [compare, setCompare]         = useState<CompareResult | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError]     = useState(false);

  async function loadComparison() {
    if (!myUid || compareLoading || compare) return;
    setCompareLoading(true);
    setCompareError(false);
    try {
      const r = await fetch(`${API_BASE}/compare/${myUid}/${uid}/insight`);
      if (!r.ok) throw new Error();
      setCompare(await r.json());
    } catch {
      setCompareError(true);
    } finally {
      setCompareLoading(false);
    }
  }

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

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 mb-8 overflow-hidden">

        <div className="flex items-center gap-5 px-6 py-5">
          <Avatar u={user} size="lg" />
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-bold text-white leading-tight">{user.name}</h1>
            <p className="text-zinc-500 text-xs mt-0.5 mb-2.5">
              {total > 0 ? `${total} liked item${total !== 1 ? 's' : ''}` : 'No liked items yet'}
            </p>
            <VisitorSocialRow socials={{
              social_telegram:  user.social_telegram,
              social_instagram: user.social_instagram,
              social_steam:     user.social_steam,
              social_discord:   user.social_discord,
              social_tiktok:    user.social_tiktok,
            }} />
          </div>
          <div className="flex-shrink-0">
            <FriendButton targetUid={uid} />
          </div>
        </div>

        {myUid && myUid !== uid && (
          <>
            <div className="border-t border-zinc-800" />

            {!compare && !compareLoading && !compareError && (
              <button onClick={loadComparison}
                className="w-full group px-6 py-4 text-left hover:bg-zinc-800/40 transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-zinc-400 group-hover:text-zinc-200 transition-colors">
                      ✦ Compare tastes
                    </span>
                    <span className="text-xs text-zinc-600 ml-2">powered by AI · click to reveal</span>
                  </div>
                  <div className="flex items-center gap-2 select-none pointer-events-none">
                    <div className="text-lg font-bold text-zinc-700 blur-[3px]">87%</div>
                    <div className="w-24 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                      <div className="h-full w-3/4 rounded-full bg-zinc-700 blur-[2px]" />
                    </div>
                  </div>
                </div>
              </button>
            )}

            {compareLoading && (
              <div className="px-6 py-4 animate-pulse flex items-center gap-4">
                <span className="text-xs text-zinc-600">Analysing tastes…</span>
                <div className="flex-1 space-y-1.5">
                  <div className="h-2 bg-zinc-800 rounded w-full" />
                  <div className="h-2 bg-zinc-800 rounded w-4/5" />
                </div>
              </div>
            )}

            {compareError && !compareLoading && (
              <div className="px-6 py-4 flex items-center gap-3">
                <span className="text-xs text-zinc-500">Couldn't load comparison.</span>
                <button onClick={loadComparison} className="text-xs text-zinc-400 hover:text-white underline">Retry</button>
              </div>
            )}

            {compare && (
              <div className="px-6 py-4 space-y-2.5">
                <div className="flex items-center gap-3">
                  <span className={`text-2xl font-bold ${compare.compatibility >= 70 ? 'text-emerald-400' : compare.compatibility >= 40 ? 'text-yellow-400' : 'text-zinc-400'}`}>
                    {compare.compatibility}%
                  </span>
                  <div className="flex-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${compare.compatibility >= 70 ? 'bg-emerald-500' : compare.compatibility >= 40 ? 'bg-yellow-500' : 'bg-zinc-600'}`}
                      style={{ width: `${compare.compatibility}%` }}
                    />
                  </div>
                  <span className="text-xs text-zinc-600 flex-shrink-0">compatibility</span>
                </div>
                <p className="text-sm text-zinc-300 leading-relaxed">{compare.insight}</p>

                {(compare.common.games.length + compare.common.movies.length + compare.common.tracks.length) > 0 && (
                  <div className="flex flex-col sm:flex-row gap-x-4 gap-y-3 pt-1">
                    {compare.common.tracks.length > 0 && (
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5 flex items-center gap-1">
                          <span>🎵</span><span>Music</span>
                        </p>
                        <div className="flex flex-col items-start gap-1">
                          {compare.common.tracks.map(item => (
                            <a key={item.id} href={`/music/${item.id}`}
                              className="max-w-full text-xs px-2 py-0.5 rounded-md bg-violet-500/10 border border-violet-500/20 text-violet-300 hover:bg-violet-500/25 transition-colors truncate">
                              {item.title}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                    {compare.common.movies.length > 0 && (
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5 flex items-center gap-1">
                          <span>🎬</span><span>Films</span>
                        </p>
                        <div className="flex flex-col items-start gap-1">
                          {compare.common.movies.map(item => (
                            <a key={item.id} href={`/movies/${item.id}`}
                              className="max-w-full text-xs px-2 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-300 hover:bg-rose-500/25 transition-colors truncate">
                              {item.title}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                    {compare.common.games.length > 0 && (
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1.5 flex items-center gap-1">
                          <span>🎮</span><span>Games</span>
                        </p>
                        <div className="flex flex-col items-start gap-1">
                          {compare.common.games.map(item => (
                            <a key={item.id} href={`/games/${item.id}`}
                              className="max-w-full text-xs px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/25 transition-colors truncate">
                              {item.title}
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {(compare.tags1.length > 0 || compare.tags2.length > 0) && (
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-zinc-800">
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1">Your vibe</p>
                      <div className="flex flex-wrap gap-1">
                        {compare.tags1.map(t => (
                          <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300">{t}</span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-1">{compare.name2}'s vibe</p>
                      <div className="flex flex-wrap gap-1">
                        {compare.tags2.map(t => (
                          <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-300">{t}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {(compare.picks.games.length + compare.picks.movies.length + compare.picks.tracks.length) > 0 && (
                  <div className="pt-2 border-t border-zinc-800">
                    <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">✦ What {compare.name2} brings — broaden your taste</p>
                    <div className="space-y-2">
                      {compare.picks.tracks.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                          {compare.picks.tracks.map(p => (
                            <a key={p.id} href={`/music/${p.id}`}
                              className="flex items-center gap-2.5 p-2 rounded-lg bg-violet-500/8 border border-violet-500/20 hover:bg-violet-500/15 transition-colors group">
                              {p.image_url
                                ? <img src={p.image_url} alt="" className="w-11 h-11 rounded object-cover flex-shrink-0" />
                                : <div className="w-11 h-11 rounded bg-zinc-800 flex items-center justify-center text-base flex-shrink-0">🎵</div>}
                              <div className="min-w-0 flex-1">
                                <p className="text-sm text-violet-200 font-medium truncate group-hover:text-white leading-tight">{p.title}</p>
                                <p className="text-xs text-zinc-500 truncate leading-tight mt-0.5">{p.artist} · {p.score}%</p>
                              </div>
                            </a>
                          ))}
                        </div>
                      )}
                      {compare.picks.movies.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                          {compare.picks.movies.map(p => (
                            <a key={p.id} href={`/movies/${p.id}`}
                              className="flex items-center gap-2.5 p-2 rounded-lg bg-rose-500/8 border border-rose-500/20 hover:bg-rose-500/15 transition-colors group">
                              {p.poster_url
                                ? <img src={p.poster_url} alt="" className="w-11 h-11 rounded object-cover object-top flex-shrink-0" />
                                : <div className="w-11 h-11 rounded bg-zinc-800 flex items-center justify-center text-base flex-shrink-0">🎬</div>}
                              <div className="min-w-0 flex-1">
                                <p className="text-sm text-rose-200 font-medium truncate group-hover:text-white leading-tight">{p.title}</p>
                                <p className="text-xs text-zinc-500 truncate leading-tight mt-0.5">{p.release_year || '—'} · {p.score}%</p>
                              </div>
                            </a>
                          ))}
                        </div>
                      )}
                      {compare.picks.games.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                          {compare.picks.games.map(p => (
                            <a key={p.id} href={`/games/${p.id}`}
                              className="flex items-center gap-2.5 p-2 rounded-lg bg-emerald-500/8 border border-emerald-500/20 hover:bg-emerald-500/15 transition-colors group">
                              {p.poster_url
                                ? <img src={thumbUrl(p.poster_url, 200) ?? ''} alt="" loading="lazy" className="w-11 h-11 rounded object-cover flex-shrink-0" />
                                : <div className="w-11 h-11 rounded bg-zinc-800 flex items-center justify-center text-base flex-shrink-0">🎮</div>}
                              <div className="min-w-0 flex-1">
                                <p className="text-sm text-emerald-200 font-medium truncate group-hover:text-white leading-tight">{p.title}</p>
                                <p className="text-xs text-zinc-500 truncate leading-tight mt-0.5">{p.release_year || '—'} · {p.score}%</p>
                              </div>
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

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
                {g.poster_url ? <img src={thumbUrl(g.poster_url, 420) ?? ''} alt={g.title} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" /> : <div className="w-full h-full flex items-center justify-center text-4xl">🎮</div>}
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
