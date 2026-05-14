import { useEffect, useRef, useState } from 'react';
import { API_BASE } from '../lib/api';
import { cachedFetch } from '../lib/cache';

const CW = 158;   // card width
const CH = 62;    // card height
const SPEED = 0.85;

type Domain = 'music' | 'movie' | 'game';

interface Dot {
  i: number;
  domain: Domain;
  title: string;
  sub: string;
  img: string;
  href: string;
  x: number; y: number;
  vx: number; vy: number;
}


function randVel(): [number, number] {
  const a = Math.random() * Math.PI * 2;
  const s = SPEED * (0.65 + Math.random() * 0.7);
  return [Math.cos(a) * s, Math.sin(a) * s];
}

const CARD_STYLE: Record<Domain, string> = {
  music: 'border-violet-500/30 bg-violet-500/8 hover:border-violet-400/60 hover:bg-violet-500/15',
  movie: 'border-rose-500/30   bg-rose-500/8   hover:border-rose-400/60   hover:bg-rose-500/15',
  game:  'border-emerald-500/30 bg-emerald-500/8 hover:border-emerald-400/60 hover:bg-emerald-500/15',
};

export default function BounceScene() {
  const boxRef    = useRef<HTMLDivElement>(null);
  const centerRef = useRef<HTMLDivElement>(null);
  const rafRef    = useRef<number>(0);
  const dots      = useRef<Dot[]>([]);
  const elRefs    = useRef<(HTMLDivElement | null)[]>([]);
  const [ready, setReady]   = useState(false);
  const [q, setQ]           = useState('');
  const [aiMode, setAiMode] = useState(false);

  // Fetch all three domains (cached in sessionStorage for instant repeat visits)
  useEffect(() => {
    Promise.all([
      cachedFetch<any[]>('catalog:tracks', `${API_BASE}/tracks`).catch(() => []),
      cachedFetch<any[]>('catalog:movies', `${API_BASE}/movies`).catch(() => []),
      cachedFetch<any[]>('catalog:games',  `${API_BASE}/games`).catch(() => []),
    ]).then(([tracks, movies, games]) => {
      const W  = boxRef.current?.clientWidth  ?? 1200;
      const H  = boxRef.current?.clientHeight ?? 650;
      const cx = W / 2;
      const cy = H / 2;

      function place(domain: Domain, title: string, sub: string, img: string, href: string, idx: number): Dot {
        let x: number, y: number;
        // avoid center
        do {
          x = 8 + Math.random() * (W - CW - 16);
          y = 8 + Math.random() * (H - CH - 16);
        } while (Math.abs(x + CW / 2 - cx) < 260 && Math.abs(y + CH / 2 - cy) < 160);
        const [vx, vy] = randVel();
        return { i: idx, domain, title, sub, img, href, x, y, vx, vy };
      }

      const topTracks = [...(tracks as any[])].sort((a, b) => (b.listeners ?? 0) - (a.listeners ?? 0)).slice(0, 10);
      const topMovies = [...(movies as any[])].sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0)).slice(0, 10);
      const topGames  = [...(games  as any[])].sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0)).slice(0, 10);

      const list: Dot[] = [];
      const pickGenre = (gens: string[] | undefined) =>
        (gens && gens[0] === 'Action' && gens[1]) ? gens[1] : (gens?.[0] ?? '');
      topTracks.forEach(t => list.push(place('music', t.name,  pickGenre(t.genres), t.image_url,  `/music/${t.id}`,  list.length)));
      topMovies.forEach(m => list.push(place('movie', m.title, pickGenre(m.genres), m.poster_url, `/movies/${m.id}`, list.length)));
      topGames .forEach(g => list.push(place('game',  g.title, pickGenre(g.genres), g.poster_url, `/games/${g.id}`,  list.length)));

      dots.current   = list;
      elRefs.current = new Array(list.length).fill(null);
      setReady(true);
    });
  }, []);

  // Animation loop
  useEffect(() => {
    if (!ready) return;

    const tick = () => {
      const box = boxRef.current;
      const cen = centerRef.current;
      if (!box) { rafRef.current = requestAnimationFrame(tick); return; }

      const W = box.clientWidth;
      const H = box.clientHeight;
      const PAD = 18;

      let cx = 0, cy = 0, cw = 0, ch = 0;
      if (cen) {
        const br = box.getBoundingClientRect();
        const cr = cen.getBoundingClientRect();
        cx = cr.left - br.left - PAD;
        cy = cr.top  - br.top  - PAD;
        cw = cr.width  + PAD * 2;
        ch = cr.height + PAD * 2;
      }

      dots.current.forEach((d, i) => {
        d.x += d.vx;
        d.y += d.vy;

        // walls
        if (d.x <= 0)          { d.x = 0;         d.vx =  Math.abs(d.vx); }
        if (d.x + CW >= W)     { d.x = W - CW;    d.vx = -Math.abs(d.vx); }
        if (d.y <= 0)          { d.y = 0;         d.vy =  Math.abs(d.vy); }
        if (d.y + CH >= H)     { d.y = H - CH;    d.vy = -Math.abs(d.vy); }

        // center block
        if (cw > 0 &&
            d.x < cx + cw && d.x + CW > cx &&
            d.y < cy + ch && d.y + CH > cy) {
          const dL = d.x + CW  - cx;
          const dR = cx + cw   - d.x;
          const dT = d.y + CH  - cy;
          const dB = cy + ch   - d.y;
          const mn = Math.min(dL, dR, dT, dB);
          if      (mn === dL) { d.x = cx - CW;    d.vx = -Math.abs(d.vx); }
          else if (mn === dR) { d.x = cx + cw;    d.vx =  Math.abs(d.vx); }
          else if (mn === dT) { d.y = cy - CH;    d.vy = -Math.abs(d.vy); }
          else                { d.y = cy + ch;    d.vy =  Math.abs(d.vy); }
        }

        const el = elRefs.current[i];
        if (el) el.style.transform = `translate(${d.x}px,${d.y}px)`;
      });

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [ready]);

  const ql = q.toLowerCase();

  return (
    <div ref={boxRef} className="relative w-full h-full overflow-hidden">

      {/* Floating cards */}
      {ready && dots.current.map((d, i) => {
        const match = !q
          || d.title.toLowerCase().includes(ql)
          || d.sub.toLowerCase().includes(ql);
        return (
          <a
            key={d.i}
            href={d.href}
            ref={el => { elRefs.current[i] = el as HTMLDivElement | null; }}
            className={`absolute top-0 left-0 ${match ? 'opacity-100' : 'opacity-[0.06]'}`}
            style={{
              width: CW, height: CH, willChange: 'transform', textDecoration: 'none',
              animation: 'card-fade-in 0.5s ease-out both',
              animationDelay: `${i * 25}ms`,
              transition: 'opacity 0.3s ease',
            }}
          >
            <div className={`w-full h-full rounded-xl border flex items-center gap-2.5 px-2.5 cursor-pointer transition-colors ${CARD_STYLE[d.domain]}`}>
              <img
                src={d.img}
                alt=""
                loading="eager"
                decoding="async"
                className="w-10 h-10 rounded-lg object-cover flex-shrink-0 bg-zinc-800 transition-opacity duration-300"
                onLoad={e => { (e.currentTarget as HTMLImageElement).style.opacity = '1'; }}
                style={{ opacity: 0.4 }}
              />
              <div className="min-w-0 flex-1">
                <div className="text-white text-[11px] font-semibold leading-tight truncate">
                  {d.title}
                </div>
                <div className="text-zinc-500 text-[10px] truncate mt-0.5">
                  {d.sub}
                </div>
              </div>
            </div>
          </a>
        );
      })}
      <style>{`@keyframes card-fade-in { from { opacity: 0; } to { opacity: 1; } }`}</style>

      {/* Center search */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div
          ref={centerRef}
          className="flex flex-col items-center gap-5 pointer-events-auto"
        >
          {/* Logo */}
          <div className="text-center select-none">
            <h1 className="text-6xl font-bold text-white tracking-tight">TIOKhor</h1>
            <p className="text-zinc-500 text-sm mt-2">
              Discover what to watch, play & listen to — all in one place.
            </p>
          </div>

          {/* Search */}
          <div className="flex items-center w-96 bg-zinc-900/90 backdrop-blur border border-zinc-700 rounded-2xl shadow-2xl focus-within:border-zinc-500 transition-colors">
            <svg className="ml-3.5 text-zinc-600 w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search anything…"
              value={q}
              onChange={e => setQ(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && q) window.location.href = `/search?q=${encodeURIComponent(q)}${aiMode ? '&ai=1' : ''}`; }}
              className="flex-1 bg-transparent pl-2.5 pr-2 py-3.5 text-white placeholder-zinc-600 focus:outline-none text-sm"
            />
            <div className="w-px h-5 bg-zinc-700/80 mx-1 flex-shrink-0" />
            <button
              onClick={() => setAiMode(v => !v)}
              title="AI search"
              className={`flex items-center gap-1 px-2 py-1.5 transition-colors text-xs font-medium flex-shrink-0 rounded-lg ${aiMode ? 'text-violet-400 bg-violet-500/15' : 'text-zinc-500 hover:text-violet-400'}`}
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/>
              </svg>
              <span>AI</span>
            </button>
            <button
              onClick={() => { if (q) window.location.href = `/search?q=${encodeURIComponent(q)}${aiMode ? '&ai=1' : ''}`; }}
              className="mr-1.5 ml-1 px-3.5 py-1.5 bg-gradient-to-r from-violet-600 to-emerald-600 hover:from-violet-500 hover:to-emerald-500 text-white rounded-xl transition-all flex items-center gap-1.5 flex-shrink-0 text-xs font-semibold shadow-lg"
              title="Search"
            >
              Search
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          </div>

          {/* Domain links */}
          <div className="flex items-center gap-6 text-sm">
            <a href="/music"  className="text-violet-400  hover:text-violet-200  transition-colors font-medium">Music</a>
            <span className="text-zinc-500">·</span>
            <a href="/movies" className="text-rose-400    hover:text-rose-200    transition-colors font-medium">Movies</a>
            <span className="text-zinc-500">·</span>
            <a href="/games"  className="text-emerald-400 hover:text-emerald-200 transition-colors font-medium">Games</a>
          </div>
        </div>
      </div>

    </div>
  );
}
