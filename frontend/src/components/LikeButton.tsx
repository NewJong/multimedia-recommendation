import { useEffect, useState } from 'react';
import { Heart } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';

interface Props {
  itemType: 'track' | 'movie' | 'game';
  itemId: number;
  likedClass: string;
}

export default function LikeButton({ itemType, itemId, likedClass }: Props) {
  const { user, uid, loading } = useAuth();
  const [liked, setLiked]     = useState(false);
  const [authDone, setAuthDone] = useState(false);
  const [bounce, setBounce]   = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) { setAuthDone(true); return; }
    fetch(`${API_BASE}/likes/${uid}/${itemType}/${itemId}`)
      .then(r => r.json())
      .then(d => setLiked(d.liked))
      .catch(() => {})
      .finally(() => setAuthDone(true));
  }, [loading, uid, itemType, itemId]);

  async function toggle() {
    if (!uid) return;
    const prev = liked;
    setLiked(!prev);
    if (!prev) { setBounce(true); setTimeout(() => setBounce(false), 300); }
    try {
      const r = await fetch(`${API_BASE}/likes/${uid}/${itemType}/${itemId}`, { method: 'POST' });
      const d = await r.json();
      setLiked(d.liked);
      window.dispatchEvent(new CustomEvent('like-changed', { detail: { itemType, itemId } }));
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
      <Heart
        size={20}
        className={liked ? likedClass : 'text-zinc-500'}
        fill={liked ? 'currentColor' : 'none'}
      />
    </button>
  );
}
