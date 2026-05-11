import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';

type Status = 'loading' | 'none' | 'pending_sent' | 'pending_received' | 'friends';

export default function FriendButton({ targetUid }: { targetUid: string }) {
  const { uid: myUid, loading } = useAuth();
  const [status, setStatus] = useState<Status>('loading');

  useEffect(() => {
    if (loading) return;
    if (!myUid) { setStatus('none'); return; }
    if (myUid === targetUid) return;
    fetch(`${API_BASE}/friends/${myUid}/status/${targetUid}`)
      .then(r => r.json())
      .then(d => setStatus(d.status))
      .catch(() => setStatus('none'));
  }, [loading, myUid, targetUid]);

  async function sendRequest() {
    if (!myUid) return;
    setStatus('pending_sent');
    await fetch(`${API_BASE}/friends/${myUid}/request/${targetUid}`, { method: 'POST' }).catch(() => {});
  }

  async function accept() {
    if (!myUid) return;
    setStatus('friends');
    await fetch(`${API_BASE}/friends/${myUid}/accept/${targetUid}`, { method: 'POST' }).catch(() => {});
  }

  async function remove() {
    if (!myUid) return;
    setStatus('none');
    await fetch(`${API_BASE}/friends/${myUid}/${targetUid}`, { method: 'DELETE' }).catch(() => {});
  }

  if (!myUid || myUid === targetUid || status === 'loading') return null;

  if (status === 'none') return (
    <button onClick={sendRequest}
      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-300 text-sm font-medium transition-all">
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM4 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 10.374 21c-2.331 0-4.512-.645-6.374-1.766Z"/>
      </svg>
      Add Friend
    </button>
  );

  if (status === 'pending_sent') return (
    <button onClick={remove}
      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-400 text-sm font-medium transition-all">
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
      </svg>
      Pending
    </button>
  );

  if (status === 'pending_received') return (
    <div className="flex gap-2">
      <button onClick={accept}
        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-sm font-medium transition-all">
        Accept
      </button>
      <button onClick={remove}
        className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-400 text-sm font-medium transition-all">
        Reject
      </button>
    </div>
  );

  return (
    <button onClick={remove}
      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-zinc-800 hover:bg-red-500/10 border border-zinc-700 hover:border-red-500/30 text-zinc-300 hover:text-red-400 text-sm font-medium transition-all group">
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z"/>
      </svg>
      <span className="group-hover:hidden">Friends</span>
      <span className="hidden group-hover:inline">Remove</span>
    </button>
  );
}
