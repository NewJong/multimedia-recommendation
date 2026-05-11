import { useEffect, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../lib/firebase';

interface Friend { firebase_uid: string; name: string; photo_url: string | null }

interface Props {
  itemType: 'track' | 'movie' | 'game';
  itemId: number;
  ringColor: string; // e.g. 'ring-violet-500/40'
}

function Avatar({ f, ring }: { f: Friend; ring: string }) {
  return f.photo_url
    ? <img src={f.photo_url} alt={f.name} referrerPolicy="no-referrer"
        title={f.name}
        className={`w-6 h-6 rounded-full object-cover ring-2 ${ring} bg-zinc-800 -ml-1.5 first:ml-0`} />
    : <div title={f.name}
        className={`w-6 h-6 rounded-full ring-2 ${ring} bg-zinc-700 flex items-center justify-center text-[10px] font-semibold text-zinc-300 -ml-1.5 first:ml-0 flex-shrink-0`}>
        {f.name?.[0] ?? '?'}
      </div>;
}

function formatNames(friends: Friend[]): string {
  if (friends.length === 1) return `${friends[0].name} liked this`;
  if (friends.length === 2) return `${friends[0].name} and ${friends[1].name} liked this`;
  return `${friends[0].name}, ${friends[1].name} and ${friends.length - 2} other${friends.length - 2 > 1 ? 's' : ''} liked this`;
}

export default function FriendsLiked({ itemType, itemId, ringColor }: Props) {
  const [friends, setFriends] = useState<Friend[]>([]);
  const [ready, setReady]     = useState(false);

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, user => {
      if (!user) { setReady(true); return; }
      fetch(`http://localhost:8000/likes/friends/${user.uid}/${itemType}/${itemId}`)
        .then(r => r.json())
        .then(d => { setFriends(d ?? []); setReady(true); })
        .catch(() => setReady(true));
    });
    return unsub;
  }, [itemType, itemId]);

  if (!ready || friends.length === 0) return null;

  return (
    <div
      className="flex items-center gap-2 mt-3"
      style={{ animation: 'fade-in 0.4s ease both' }}
    >
      <style>{`@keyframes fade-in { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }`}</style>
      <div className="flex items-center">
        {friends.slice(0, 5).map(f => <Avatar key={f.firebase_uid} f={f} ring={ringColor} />)}
      </div>
      <p className="text-zinc-500 text-xs">{formatNames(friends)}</p>
    </div>
  );
}
