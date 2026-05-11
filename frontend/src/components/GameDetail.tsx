import { useEffect, useState } from 'react';
import LikeButton from './LikeButton';
import FriendsLiked from './FriendsLiked';
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
function shortP(p: string) { return PLATFORM_SHORT[p] ?? p.replace('PlayStation', 'PS').replace('Xbox', 'XB'); }

export default function GameDetail({ id }: { id: number }) {
  const [game, setGame]       = useState<Game | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(false);

  useEffect(() => {
    const gid = id || Number(window.location.pathname.split('/').pop());
    fetch(`${API_BASE}/games/${gid}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setGame)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="max-w-5xl mx-auto px-6 pt-8 animate-pulse">
      <div className="flex gap-8">
        <div className="w-52 rounded-xl bg-zinc-900 flex-shrink-0" style={{ aspectRatio: '16/9' }} />
        <div className="flex-1 space-y-3 pt-2">
          <div className="h-8 bg-zinc-900 rounded w-1/2" />
          <div className="h-5 bg-zinc-900 rounded w-1/3" />
        </div>
      </div>
    </div>
  );

  if (error || !game) return (
    <div className="max-w-5xl mx-auto px-6 py-20 text-center text-zinc-500">Game not found.</div>
  );

  const mcColor = game.metacritic >= 75 ? 'text-green-400'
    : game.metacritic >= 50 ? 'text-yellow-400' : 'text-red-400';

  const genres = Array.isArray(game.genres) ? game.genres : [];
  const tags   = (Array.isArray(game.tags) ? game.tags : []).filter(t => !genres.includes(t));

  return (
    <div className="min-h-[calc(100vh-3.5rem)] relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div style={{ position:'absolute', width:'75%', height:'70%', top:'-25%', left:'-15%', background:'radial-gradient(ellipse at center, rgba(16,185,129,0.28) 0%, transparent 68%)', animation:'gorb1 11s ease-in-out infinite' }} />
        <div style={{ position:'absolute', width:'60%', height:'60%', top:'-18%', right:'-8%', background:'radial-gradient(ellipse at center, rgba(5,150,105,0.20) 0%, transparent 68%)', animation:'gorb2 15s ease-in-out infinite' }} />
        <div style={{ position:'absolute', width:'55%', height:'45%', bottom:'5%', right:'15%', background:'radial-gradient(ellipse at center, rgba(6,95,70,0.15) 0%, transparent 68%)', animation:'gorb3 20s ease-in-out infinite' }} />
      </div>
      <style>{`
        @keyframes gorb1 { 0%,100% { transform:translate(0,0) scale(1); } 33% { transform:translate(9%,13%) scale(1.09); } 66% { transform:translate(-6%,8%) scale(0.95); } }
        @keyframes gorb2 { 0%,100% { transform:translate(0,0) scale(1); } 33% { transform:translate(-11%,6%) scale(0.93); } 66% { transform:translate(6%,11%) scale(1.07); } }
        @keyframes gorb3 { 0%,100% { transform:translate(0,0) scale(1); } 50% { transform:translate(-14%,-9%) scale(1.12); } }
      `}</style>
      <div className="max-w-5xl mx-auto px-6 pt-8 pb-16">

        <a href="/games" className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-200 text-sm mb-8 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
          Games
        </a>

        {/* Hero */}
        <div className="flex flex-col sm:flex-row gap-8 mb-8">
          {game.poster_url
            ? <img src={game.poster_url} alt={game.title}
                className="w-60 rounded-xl object-cover shadow-2xl shadow-black/60 flex-shrink-0"
                style={{ aspectRatio: '16/9' }} />
            : <div className="w-60 h-36 rounded-xl bg-zinc-900 flex items-center justify-center text-5xl flex-shrink-0">🎮</div>
          }

          <div className="flex-1 min-w-0 flex flex-col justify-center">
            <p className="text-emerald-400 text-xs font-semibold uppercase tracking-widest mb-2">Game</p>
            <h1 className="text-4xl font-bold text-white leading-tight mb-1">{game.title}</h1>
            <p className="text-zinc-500 text-sm mb-5">{game.release_year || '—'}</p>

            <div className="flex flex-wrap items-center gap-6">
              {game.rating > 0 && (
                <div><p className="text-yellow-400 font-bold text-2xl leading-none">★ {game.rating.toFixed(1)}</p><p className="text-zinc-500 text-xs mt-0.5">rating</p></div>
              )}
              {game.metacritic > 0 && (
                <div><p className={`font-bold text-2xl leading-none ${mcColor}`}>{game.metacritic}</p><p className="text-zinc-500 text-xs mt-0.5">Metacritic</p></div>
              )}
              {game.esrb_rating && (
                <div><p className="text-zinc-300 font-semibold text-lg leading-none">{game.esrb_rating}</p><p className="text-zinc-500 text-xs mt-0.5">ESRB</p></div>
              )}
              <LikeButton itemType="game" itemId={game.id} likedClass="text-emerald-400" />
              <FriendsLiked itemType="game" itemId={game.id} ringColor="ring-emerald-500/50" />
            </div>
          </div>
        </div>

        {/* Dev / publisher */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
          {game.developers?.length > 0 && (
            <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-4">
              <p className="text-zinc-500 text-xs uppercase tracking-wider mb-1">Developer</p>
              <p className="text-zinc-200 text-sm font-medium">{game.developers.join(', ')}</p>
            </div>
          )}
          {game.publishers?.length > 0 && (
            <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-4">
              <p className="text-zinc-500 text-xs uppercase tracking-wider mb-1">Publisher</p>
              <p className="text-zinc-200 text-sm font-medium">{game.publishers.join(', ')}</p>
            </div>
          )}
        </div>

        {/* Platforms */}
        {game.platforms?.length > 0 && (
          <div className="mb-5">
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Platforms</p>
            <div className="flex flex-wrap gap-2">
              {game.platforms.map(p => (
                <span key={p} className="px-3 py-1 rounded-lg text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">{shortP(p)}</span>
              ))}
            </div>
          </div>
        )}

        {/* Genres */}
        {genres.length > 0 && (
          <div className="mb-2">
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Genres</p>
            <div className="flex flex-wrap gap-2">
              {genres.map(g => <span key={g} className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">{g}</span>)}
            </div>
          </div>
        )}

        {/* Tags */}
        {tags.length > 0 && (
          <div className="mb-8 mt-2">
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Tags</p>
            <div className="flex flex-wrap gap-2">
              {tags.map(t => <span key={t} className="px-2.5 py-0.5 rounded-full text-xs bg-zinc-800 text-zinc-400 border border-zinc-700">{t}</span>)}
            </div>
          </div>
        )}

        {game.description && (
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6">
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-3">Description</p>
            <p className="text-zinc-300 text-sm leading-relaxed">{game.description}</p>
          </div>
        )}
      </div>
    </div>
  );
}
