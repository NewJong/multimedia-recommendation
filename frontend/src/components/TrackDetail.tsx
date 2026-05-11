import { useEffect, useState } from 'react';
import LikeButton from './LikeButton';

interface Track {
  id: number; name: string; artist: string; album: string;
  genre: string; genres: string[]; tags: string[];
  duration_ms: number; listeners: number; playcount: number;
  summary: string; image_url: string; url: string;
}

function fmt(n: number) {
  if (!n) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000)     return `${Math.round(n / 1_000)}K`;
  return n.toLocaleString();
}
function fmtDur(ms: number) {
  if (!ms) return null;
  const s = Math.floor(ms / 1000), m = Math.floor(s / 60);
  return `${m}:${(s % 60).toString().padStart(2, '0')}`;
}

export default function TrackDetail({ id }: { id: number }) {
  const [track, setTrack]     = useState<Track | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(false);

  useEffect(() => {
    const tid = id || Number(window.location.pathname.split('/').pop());
    fetch(`http://localhost:8000/tracks/${tid}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setTrack)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="max-w-4xl mx-auto px-6 pt-8 animate-pulse">
      <div className="flex gap-7">
        <div className="w-44 h-44 rounded-2xl bg-zinc-900 flex-shrink-0" />
        <div className="flex-1 space-y-3 pt-2">
          <div className="h-8 bg-zinc-900 rounded w-2/3" />
          <div className="h-5 bg-zinc-900 rounded w-1/3" />
        </div>
      </div>
    </div>
  );

  if (error || !track) return (
    <div className="max-w-4xl mx-auto px-6 py-20 text-center text-zinc-500">Track not found.</div>
  );

  const genres = Array.isArray(track.genres) ? track.genres : [];
  const tags   = (Array.isArray(track.tags) ? track.tags : []).filter(t => !genres.includes(t));

  return (
    <div className="min-h-[calc(100vh-3.5rem)] relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div style={{ position:'absolute', width:'75%', height:'70%', top:'-25%', left:'-15%', background:'radial-gradient(ellipse at center, rgba(139,92,246,0.32) 0%, transparent 68%)', animation:'vorb1 11s ease-in-out infinite' }} />
        <div style={{ position:'absolute', width:'60%', height:'60%', top:'-18%', right:'-8%', background:'radial-gradient(ellipse at center, rgba(109,40,217,0.24) 0%, transparent 68%)', animation:'vorb2 15s ease-in-out infinite' }} />
        <div style={{ position:'absolute', width:'55%', height:'45%', bottom:'5%', right:'15%', background:'radial-gradient(ellipse at center, rgba(124,58,237,0.14) 0%, transparent 68%)', animation:'vorb3 20s ease-in-out infinite' }} />
      </div>
      <style>{`
        @keyframes vorb1 { 0%,100% { transform:translate(0,0) scale(1); } 33% { transform:translate(9%,13%) scale(1.09); } 66% { transform:translate(-6%,8%) scale(0.95); } }
        @keyframes vorb2 { 0%,100% { transform:translate(0,0) scale(1); } 33% { transform:translate(-11%,6%) scale(0.93); } 66% { transform:translate(6%,11%) scale(1.07); } }
        @keyframes vorb3 { 0%,100% { transform:translate(0,0) scale(1); } 50% { transform:translate(-14%,-9%) scale(1.12); } }
      `}</style>
      <div className="max-w-4xl mx-auto px-6 pt-8 pb-16">

        <a href="/music" className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-200 text-sm mb-8 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
          Music
        </a>

        {/* Hero */}
        <div className="flex flex-col sm:flex-row gap-7 mb-8">
          {track.image_url
            ? <img src={track.image_url} alt={track.name} className="w-44 h-44 rounded-2xl object-cover shadow-2xl shadow-violet-950/50 flex-shrink-0"/>
            : <div className="w-44 h-44 rounded-2xl bg-zinc-900 flex items-center justify-center text-6xl flex-shrink-0">🎵</div>
          }
          <div className="flex flex-col justify-center min-w-0">
            <p className="text-violet-400 text-xs font-semibold uppercase tracking-widest mb-2">Track</p>
            <h1 className="text-4xl font-bold text-white leading-tight mb-1">{track.name}</h1>
            <p className="text-violet-300 text-xl font-medium mb-0.5">{track.artist}</p>
            {track.album && <p className="text-zinc-500 text-sm mb-5">{track.album}</p>}
            <div className="flex flex-wrap items-center gap-6">
              {fmt(track.listeners) && <div><p className="text-white font-bold text-lg leading-none">{fmt(track.listeners)}</p><p className="text-zinc-500 text-xs mt-0.5">listeners</p></div>}
              {fmt(track.playcount) && <div><p className="text-white font-bold text-lg leading-none">{fmt(track.playcount)}</p><p className="text-zinc-500 text-xs mt-0.5">scrobbles</p></div>}
              {fmtDur(track.duration_ms) && <div><p className="text-white font-bold text-lg leading-none">{fmtDur(track.duration_ms)}</p><p className="text-zinc-500 text-xs mt-0.5">duration</p></div>}
              <LikeButton itemType="track" itemId={track.id} likedClass="text-violet-400" />
            </div>
          </div>
        </div>

        {/* Genres */}
        {genres.length > 0 && (
          <div className="mb-2">
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-2">Genres</p>
            <div className="flex flex-wrap gap-2">
              {genres.map(g => <span key={g} className="px-3 py-1 rounded-full text-xs font-semibold bg-violet-500/20 text-violet-300 border border-violet-500/30">{g}</span>)}
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

        {track.summary && (
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 mb-6">
            <p className="text-zinc-500 text-xs uppercase tracking-wider mb-3">Summary</p>
            <p className="text-zinc-300 text-sm leading-relaxed">{track.summary}</p>
          </div>
        )}

      </div>
    </div>
  );
}
