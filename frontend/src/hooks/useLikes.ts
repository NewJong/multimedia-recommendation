import { useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';

export type ItemType = 'track' | 'movie' | 'game';
type Domain = 'tracks' | 'movies' | 'games';

const DOMAIN: Record<ItemType, Domain> = { track: 'tracks', movie: 'movies', game: 'games' };

export function useLikes(itemType: ItemType, uid: string | null) {
  const [likedIds, setLikedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!uid) { setLikedIds(new Set()); return; }
    let cancelled = false;
    const refetch = () => {
      fetch(`${API_BASE}/likes/${uid}`)
        .then(r => r.json())
        .then(d => {
          if (cancelled) return;
          const list: { id: number }[] = d[DOMAIN[itemType]] ?? [];
          setLikedIds(new Set(list.map(x => x.id)));
        })
        .catch(() => {});
    };
    refetch();
    const onChange = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (!detail || detail.itemType === itemType) refetch();
    };
    window.addEventListener('like-changed', onChange);
    return () => { cancelled = true; window.removeEventListener('like-changed', onChange); };
  }, [uid, itemType]);

  async function toggleLike(itemId: number) {
    if (!uid) return;
    const was = likedIds.has(itemId);
    setLikedIds(prev => {
      const n = new Set(prev);
      if (was) n.delete(itemId); else n.add(itemId);
      return n;
    });
    try {
      await fetch(`${API_BASE}/likes/${uid}/${itemType}/${itemId}`, { method: 'POST' });
      window.dispatchEvent(new CustomEvent('like-changed', { detail: { itemType, itemId } }));
    } catch {
      setLikedIds(prev => {
        const n = new Set(prev);
        if (was) n.add(itemId); else n.delete(itemId);
        return n;
      });
    }
  }

  return { likedIds, toggleLike };
}
