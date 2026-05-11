import { useEffect, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../lib/firebase';

interface Props {
  itemType: 'track' | 'movie' | 'game';
  itemId: number;
  likedClass: string;
}

export default function LikeButton({ itemType, itemId, likedClass }: Props) {
  const [uid, setUid]         = useState<string | null>(null);
  const [liked, setLiked]     = useState(false);
  const [authDone, setAuthDone] = useState(false);
  const [bounce, setBounce]   = useState(false);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, user => {
      setUid(user?.uid ?? null);
      setAuthDone(true); // show button right after auth resolves (~50ms, cached)
      if (user) {
        fetch(`http://localhost:8000/likes/${user.uid}/${itemType}/${itemId}`)
          .then(r => r.json())
          .then(d => setLiked(d.liked))
          .catch(() => {});
      }
    });
    return unsub;
  }, [itemType, itemId]);

  async function toggle() {
    if (!uid) return;
    const prev = liked;
    setLiked(!prev);
    if (!prev) { setBounce(true); setTimeout(() => setBounce(false), 300); }
    try {
      const r = await fetch(`http://localhost:8000/likes/${uid}/${itemType}/${itemId}`, { method: 'POST' });
      const d = await r.json();
      setLiked(d.liked);
    } catch {
      setLiked(prev);
    }
  }

  return (
    <button
      onClick={toggle}
      title={!uid ? 'Sign in to like' : liked ? 'Unlike' : 'Like'}
      disabled={!uid}
      style={{
        transform: bounce ? 'scale(1.35)' : 'scale(1)',
        opacity: authDone ? 1 : 0,
        transition: 'transform 0.2s ease, opacity 0.15s ease',
      }}
      className={`p-1.5 rounded-full border border-zinc-700 bg-zinc-900/60 ${uid ? 'hover:border-zinc-500 hover:bg-zinc-800 cursor-pointer' : 'cursor-default opacity-40'}`}
    >
      {liked ? (
        <svg className={`w-5 h-5 ${likedClass}`} viewBox="0 0 24 24" fill="currentColor">
          <path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z"/>
        </svg>
      ) : (
        <svg className="w-5 h-5 text-zinc-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"/>
        </svg>
      )}
    </button>
  );
}
