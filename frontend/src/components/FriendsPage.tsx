import { useEffect, useState } from 'react';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider } from '../lib/firebase';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';

interface FriendUser {
  firebase_uid: string; name: string; email: string; photo_url: string | null;
}

function Avatar({ u, size = 'md' }: { u: FriendUser; size?: 'sm' | 'md' }) {
  const sz = size === 'md' ? 'w-10 h-10 text-base' : 'w-8 h-8 text-sm';
  return u.photo_url
    ? <img src={u.photo_url} alt={u.name} referrerPolicy="no-referrer" className={`${sz} rounded-full object-cover flex-shrink-0`} />
    : <div className={`${sz} rounded-full bg-zinc-700 flex items-center justify-center font-semibold text-zinc-300 flex-shrink-0`}>{u.name?.[0] ?? '?'}</div>;
}

export default function FriendsPage() {
  const { user, loading: authLoading } = useAuth();
  const [friends, setFriends]   = useState<FriendUser[]>([]);
  const [requests, setRequests] = useState<FriendUser[]>([]);
  const [search, setSearch]     = useState('');
  const [searchResults, setSearchRes] = useState<FriendUser[]>([]);
  const [loaded, setLoaded]     = useState(false);

  useEffect(() => {
    if (authLoading || !user) return;
    Promise.all([
      fetch(`${API_BASE}/friends/${user.uid}`).then(r => r.json()),
      fetch(`${API_BASE}/friends/${user.uid}/requests`).then(r => r.json()),
    ]).then(([f, rq]) => {
      setFriends(f ?? []);
      setRequests(rq ?? []);
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, [authLoading, user?.uid]);

  if (authLoading) return <div className="py-20 text-center text-zinc-600">Loading…</div>;

  if (!user) return (
    <div className="py-24 text-center">
      <div className="text-zinc-700 text-5xl mb-5">👥</div>
      <h1 className="text-2xl font-bold text-white mb-2">Friends</h1>
      <p className="text-zinc-500 mb-8">Sign in to find and connect with people</p>
      <button onClick={() => signInWithPopup(auth, googleProvider)}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-zinc-700 hover:border-zinc-500 text-sm text-zinc-200 transition-all">
        <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        Sign in with Google
      </button>
    </div>
  );

  async function doSearch(q: string) {
    setSearch(q);
    if (q.length < 2) { setSearchRes([]); return; }
    try {
      const r = await fetch(`${API_BASE}/users/search?q=${encodeURIComponent(q)}`);
      setSearchRes((await r.json()).filter((u: FriendUser) => u.firebase_uid !== user?.uid));
    } catch {}
  }

  async function acceptReq(fromUid: string) {
    await fetch(`${API_BASE}/friends/${user.uid}/accept/${fromUid}`, { method: 'POST' }).catch(() => {});
    const accepted = requests.find(r => r.firebase_uid === fromUid);
    setRequests(prev => prev.filter(r => r.firebase_uid !== fromUid));
    if (accepted) setFriends(prev => [...prev, accepted]);
  }

  async function rejectReq(fromUid: string) {
    await fetch(`${API_BASE}/friends/${user.uid}/${fromUid}`, { method: 'DELETE' }).catch(() => {});
    setRequests(prev => prev.filter(r => r.firebase_uid !== fromUid));
  }

  async function removeFriend(friendUid: string) {
    await fetch(`${API_BASE}/friends/${user.uid}/${friendUid}`, { method: 'DELETE' }).catch(() => {});
    setFriends(prev => prev.filter(f => f.firebase_uid !== friendUid));
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">

      {/* Search */}
      <div>
        <p className="text-zinc-500 text-xs uppercase tracking-wider mb-3">Find people</p>
        <input type="text" placeholder="Search by name or email…" value={search}
          onChange={e => doSearch(e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-sky-500 transition-colors"
        />
        {searchResults.length > 0 && (
          <div className="mt-2 space-y-1">
            {searchResults.map(u => (
              <a key={u.firebase_uid} href={`/profile/${u.firebase_uid}`}
                className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 hover:border-sky-500/40 hover:bg-sky-500/5 transition-all">
                <Avatar u={u} />
                <div className="min-w-0">
                  <p className="text-white text-sm font-medium truncate">{u.name}</p>
                  <p className="text-zinc-500 text-xs truncate">{u.email}</p>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Incoming requests */}
      {requests.length > 0 && (
        <div>
          <p className="text-zinc-500 text-xs uppercase tracking-wider mb-3">
            Incoming requests · <span className="text-sky-400">{requests.length}</span>
          </p>
          <div className="space-y-2">
            {requests.map(u => (
              <div key={u.firebase_uid} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800">
                <a href={`/profile/${u.firebase_uid}`} className="flex items-center gap-3 flex-1 min-w-0 hover:opacity-80 transition-opacity">
                  <Avatar u={u} />
                  <p className="text-white text-sm font-medium truncate">{u.name}</p>
                </a>
                <div className="flex gap-2 flex-shrink-0">
                  <button onClick={() => acceptReq(u.firebase_uid)}
                    className="px-3 py-1.5 rounded-lg bg-sky-500/15 hover:bg-sky-500/25 border border-sky-500/30 text-sky-300 text-xs font-medium transition-all">
                    Accept
                  </button>
                  <button onClick={() => rejectReq(u.firebase_uid)}
                    className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-400 text-xs font-medium transition-all">
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Friends list */}
      {loaded && (
        <div>
          <p className="text-zinc-500 text-xs uppercase tracking-wider mb-3">
            Friends · <span className="text-white">{friends.length}</span>
          </p>
          {friends.length === 0
            ? <p className="text-zinc-600 text-sm text-center py-12 border border-zinc-800/60 rounded-xl">
                No friends yet — search for people above
              </p>
            : <div className="space-y-2">
                {friends.map(u => (
                  <div key={u.firebase_uid} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 hover:border-sky-500/30 transition-colors group">
                    <a href={`/profile/${u.firebase_uid}`} className="flex items-center gap-3 flex-1 min-w-0">
                      <Avatar u={u} />
                      <div className="min-w-0">
                        <p className="text-white text-sm font-medium truncate group-hover:text-sky-200 transition-colors">{u.name}</p>
                        <p className="text-zinc-500 text-xs truncate">{u.email}</p>
                      </div>
                    </a>
                    <button onClick={() => removeFriend(u.firebase_uid)}
                      className="flex-shrink-0 px-3 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 bg-zinc-800 hover:bg-red-500/10 border border-zinc-700 hover:border-red-500/30 text-zinc-500 hover:text-red-400 text-xs transition-all">
                      Remove
                    </button>
                  </div>
                ))}
              </div>
          }
        </div>
      )}
    </div>
  );
}
