import { useEffect, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../lib/firebase';

interface Friend { firebase_uid: string; name: string; photo_url: string | null }

interface Props {
  itemType: 'track' | 'movie' | 'game';
  itemId: number;
  ringColor: string;
}

export default function FriendsLiked({ itemType, itemId, ringColor }: Props) {
  const [friends, setFriends] = useState<Friend[]>([]);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, user => {
      if (!user) return;
      fetch(`http://localhost:8000/likes/friends/${user.uid}/${itemType}/${itemId}`)
        .then(r => r.json())
        .then(d => setFriends(d ?? []))
        .catch(() => {});
    });
    return unsub;
  }, [itemType, itemId]);

  if (friends.length === 0) return null;

  return (
    <div className="flex items-center -space-x-1.5">
      {friends.slice(0, 5).map(f => (
        <a
          key={f.firebase_uid}
          href={`/profile/${f.firebase_uid}`}
          className="relative group/tip block"
        >
          {f.photo_url
            ? <img
                src={f.photo_url}
                alt={f.name}
                referrerPolicy="no-referrer"
                className={`w-7 h-7 rounded-full object-cover ring-2 ${ringColor} ring-offset-1 ring-offset-black transition-transform duration-150 hover:scale-110 hover:z-10`}
              />
            : <div className={`w-7 h-7 rounded-full ring-2 ${ringColor} ring-offset-1 ring-offset-black bg-zinc-700 flex items-center justify-center text-[11px] font-semibold text-zinc-300 transition-transform duration-150 hover:scale-110 hover:z-10`}>
                {f.name?.[0] ?? '?'}
              </div>
          }
          {/* Tooltip */}
          <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-white text-xs whitespace-nowrap opacity-0 group-hover/tip:opacity-100 transition-opacity duration-150 z-50 shadow-lg">
            {f.name}
          </span>
        </a>
      ))}
    </div>
  );
}
