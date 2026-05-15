import { useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';
import { cacheGet, cacheSet, cacheClear } from '../lib/cache';
import type { ItemType } from './useLikes';

const DOMAIN_PATH: Record<ItemType, string> = { track: 'tracks', movie: 'movies', game: 'games' };

const recsKey = (itemType: ItemType, uid: string) => `recs:${itemType}:${uid}`;

export interface RecItem {
  id: number;
  _score: number;
  _matched_tags?: string[];
  [k: string]: any;
}

export function useRecommendations<T extends RecItem = RecItem>(itemType: ItemType, uid: string | null) {
  const initial = uid ? cacheGet<T[]>(recsKey(itemType, uid)) : null;
  const [recs, setRecs] = useState<T[]>(initial ?? []);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(initial !== null);

  useEffect(() => {
    if (!uid) { setRecs([]); setLoaded(false); return; }
    if (loaded) return;
    let cancelled = false;
    setLoading(true);
    fetch(`${API_BASE}/recommendations/${uid}/${DOMAIN_PATH[itemType]}`)
      .then(r => r.json())
      .then(d => {
        if (cancelled) return;
        setRecs(d);
        setLoaded(true);
        cacheSet(recsKey(itemType, uid), d);
      })
      .catch(() => { if (!cancelled) setLoaded(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [uid, itemType, loaded]);

  useEffect(() => {
    const onChange = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (!detail || detail.itemType === itemType) {
        cacheClear(`recs:${itemType}:`);
        setLoaded(false);
      }
    };
    window.addEventListener('like-changed', onChange);
    return () => window.removeEventListener('like-changed', onChange);
  }, [itemType]);

  return { recs, loading, loaded };
}
