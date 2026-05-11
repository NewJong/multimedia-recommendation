import { useEffect, useState } from 'react';
import LikeButton from './LikeButton';
import FriendsLiked from './FriendsLiked';

interface Movie {
  id: number; title: string; genre: string; genres: string[]; keywords: string[];
  overview: string; tagline: string; release_year: number; runtime: number;
  rating: number; vote_count: number; popularity: number; language: string;
  status: string; director: string; actors: string[];
  poster_url: string; backdrop_url: string;
  budget: number; revenue: number; collection: string; tmdb_id: number;
}

function fmtRuntime(min: number) {
  if (!min) return null;
  const h = Math.floor(min / 60), m = min % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}
function fmtMoney(n: number) {
  if (!n || n === 0) return null;
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000)     return `$${(n / 1_000_000).toFixed(0)}M`;
  return `$${n.toLocaleString()}`;
}

export default function MovieDetail({ id }: { id: number }) {
  const [movie, setMovie]     = useState<Movie | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(false);

  useEffect(() => {
    fetch(`http://localhost:8000/movies/${id}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setMovie).catch(() => setError(true)).finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="max-w-5xl mx-auto px-6 pt-8 animate-pulse">
      <div className="flex gap-8">
        <div className="w-40 h-60 rounded-xl bg-zinc-900 flex-shrink-0" />
        <div className="flex-1 space-y-3 pt-4">
          <div className="h-8 bg-zinc-800 rounded w-1/2" />
          <div className="h-4 bg-zinc-800 rounded w-1/3" />
        </div>
      </div>
    </div>
  );

  if (error || !movie) return (
    <div className="max-w-5xl mx-auto px-6 py-20 text-center text-zinc-500">Movie not found.</div>
  );

  const metacolor = movie.rating >= 7 ? 'text-green-400' : movie.rating >= 5 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="min-h-[calc(100vh-3.5rem)] relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div style={{ position:'absolute', width:'75%', height:'70%', top:'-25%', left:'-15%', background:'radial-gradient(ellipse at center, rgba(244,63,94,0.28) 0%, transparent 68%)', animation:'rorb1 11s ease-in-out infinite' }} />
        <div style={{ position:'absolute', width:'60%', height:'60%', top:'-18%', right:'-8%', background:'radial-gradient(ellipse at center, rgba(225,29,72,0.20) 0%, transparent 68%)', animation:'rorb2 15s ease-in-out infinite' }} />
        <div style={{ position:'absolute', width:'55%', height:'45%', bottom:'5%', right:'15%', background:'radial-gradient(ellipse at center, rgba(190,24,93,0.13) 0%, transparent 68%)', animation:'rorb3 20s ease-in-out infinite' }} />
      </div>
      <style>{`
        @keyframes rorb1 { 0%,100% { transform:translate(0,0) scale(1); } 33% { transform:translate(9%,13%) scale(1.09); } 66% { transform:translate(-6%,8%) scale(0.95); } }
        @keyframes rorb2 { 0%,100% { transform:translate(0,0) scale(1); } 33% { transform:translate(-11%,6%) scale(0.93); } 66% { transform:translate(6%,11%) scale(1.07); } }
        @keyframes rorb3 { 0%,100% { transform:translate(0,0) scale(1); } 50% { transform:translate(-14%,-9%) scale(1.12); } }
      `}</style>
      <div className="max-w-5xl mx-auto px-6 pt-8 pb-16">
        {/* Back */}
        <a href="/movies" className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-200 text-sm mb-8 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Movies
        </a>

        {/* Poster + info */}
        <div className="flex flex-col sm:flex-row gap-8 mb-8">
          {movie.poster_url
            ? <img src={movie.poster_url} alt={movie.title} className="w-44 rounded-xl object-cover shadow-2xl shadow-black/70 flex-shrink-0 self-start" />
            : <div className="w-40 h-60 rounded-xl bg-zinc-900 flex items-center justify-center text-5xl flex-shrink-0">🎬</div>
          }

          <div className="flex-1 min-w-0">
            <p className="text-rose-400 text-xs font-semibold uppercase tracking-widest mb-2">Film</p>
            <h1 className="text-4xl font-bold text-white leading-tight mb-1">{movie.title}</h1>
            {movie.tagline && <p className="text-zinc-400 italic mb-4">"{movie.tagline}"</p>}

            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-zinc-400 mb-5">
              {movie.release_year > 0 && <span>{movie.release_year}</span>}
              {fmtRuntime(movie.runtime) && <span>{fmtRuntime(movie.runtime)}</span>}
              {movie.language && <span className="uppercase">{movie.language}</span>}
              {movie.status && movie.status !== 'Released' && <span className="text-yellow-500">{movie.status}</span>}
            </div>

            {/* Ratings */}
            <div className="flex flex-wrap items-center gap-5 mb-6">
              {movie.rating > 0 && (
                <div>
                  <p className={`font-bold text-2xl ${metacolor}`}>★ {movie.rating.toFixed(1)}</p>
                  <p className="text-zinc-500 text-xs">{movie.vote_count?.toLocaleString()} votes</p>
                </div>
              )}
              {movie.popularity > 0 && (
                <div>
                  <p className="text-white font-bold text-2xl">{Math.round(movie.popularity)}</p>
                  <p className="text-zinc-500 text-xs">popularity</p>
                </div>
              )}
              <LikeButton itemType="movie" itemId={movie.id} likedClass="text-rose-400" />
              <FriendsLiked itemType="movie" itemId={movie.id} ringColor="ring-rose-500/50" />
            </div>

            {/* Crew */}
            {movie.director && (
              <div className="mb-2">
                <span className="text-zinc-500 text-xs uppercase tracking-wider">Director </span>
                <span className="text-zinc-200 text-sm">{movie.director}</span>
              </div>
            )}
            {movie.actors?.length > 0 && (
              <div className="mb-4">
                <span className="text-zinc-500 text-xs uppercase tracking-wider">Cast </span>
                <span className="text-zinc-200 text-sm">{movie.actors.slice(0, 5).join(', ')}</span>
              </div>
            )}

            {/* Collection */}
            {movie.collection && (
              <div className="mb-4">
                <span className="text-zinc-500 text-xs uppercase tracking-wider">Collection </span>
                <span className="text-rose-300 text-sm">{movie.collection}</span>
              </div>
            )}
          </div>
        </div>

        {/* Overview */}
        {movie.overview && (
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 mt-8">
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-3">Overview</p>
            <p className="text-zinc-300 text-sm leading-relaxed">{movie.overview}</p>
          </div>
        )}

        {/* Genres */}
        {movie.genres?.length > 0 && (
          <div className="mt-6">
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Genres</p>
            <div className="flex flex-wrap gap-2">
              {movie.genres.map(g => (
                <span key={g} className="px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/25">{g}</span>
              ))}
            </div>
          </div>
        )}

        {/* Keywords */}
        {movie.keywords?.length > 0 && (
          <div className="mt-4">
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Keywords</p>
            <div className="flex flex-wrap gap-2">
              {movie.keywords.slice(0, 15).map(k => (
                <span key={k} className="px-2.5 py-0.5 rounded-full text-xs bg-zinc-800/80 text-zinc-500 border border-zinc-700/60">{k}</span>
              ))}
            </div>
          </div>
        )}

        {/* Budget / revenue */}
        {(fmtMoney(movie.budget) || fmtMoney(movie.revenue)) && (
          <div className="flex flex-wrap gap-8 mt-8 border-t border-zinc-800 pt-6">
            {fmtMoney(movie.budget) && (
              <div><p className="text-white font-bold text-lg">{fmtMoney(movie.budget)}</p><p className="text-zinc-500 text-xs">Budget</p></div>
            )}
            {fmtMoney(movie.revenue) && (
              <div><p className="text-white font-bold text-lg">{fmtMoney(movie.revenue)}</p><p className="text-zinc-500 text-xs">Revenue</p></div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
