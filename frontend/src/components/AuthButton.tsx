import { useEffect, useRef, useState } from 'react';
import { signInWithPopup, signOut } from 'firebase/auth';
import type { User } from 'firebase/auth';
import { auth, googleProvider } from '../lib/firebase';
import { useAuth } from '../hooks/useAuth';
import { API_BASE } from '../lib/api';

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

function Avatar({ user, onClick }: { user: User; onClick: () => void }) {
  const initials = user.displayName
    ? user.displayName.split(' ').map((n: string) => n[0]).slice(0, 2).join('')
    : '?';
  return (
    <button onClick={onClick}
      className="w-8 h-8 rounded-full overflow-hidden ring-2 ring-transparent hover:ring-zinc-500 transition-all duration-200 focus:outline-none flex-shrink-0">
      {user.photoURL
        ? <img src={user.photoURL} alt={user.displayName ?? ''} referrerPolicy="no-referrer" className="w-full h-full object-cover" />
        : <div className="w-full h-full bg-zinc-700 flex items-center justify-center text-xs font-semibold text-zinc-200">{initials}</div>
      }
    </button>
  );
}

export default function AuthButton() {
  const { user, loading } = useAuth();
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Sync user to DB on login
  useEffect(() => {
    if (!user) return;
    fetch(`${API_BASE}/users/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uid: user.uid, email: user.email, name: user.displayName, photo_url: user.photoURL }),
    }).catch(() => {});
  }, [user?.uid]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  if (loading) return <div className="w-8 h-8 rounded-full bg-zinc-800 animate-pulse" />;

  if (!user) return (
    <button onClick={() => signInWithPopup(auth, googleProvider)}
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-zinc-700 hover:border-zinc-500 text-sm text-zinc-300 transition-all duration-200">
      <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
      </svg>
      Sign in
    </button>
  );

  const firstName = user.displayName?.split(' ')[0] ?? '';

  return (
    <div className="relative" ref={dropdownRef}>
      <div className="flex items-center gap-2.5">
        <a href="/profile" className="hidden sm:block text-right group">
          <p className="text-xs text-zinc-500 leading-none mb-0.5">{greeting()}</p>
          <p className="text-sm font-medium text-zinc-200 leading-none group-hover:text-white transition-colors">{firstName}</p>
        </a>
        <Avatar user={user} onClick={() => setOpen(v => !v)} />
      </div>

      {open && (
        <div className="absolute right-0 top-11 w-52 bg-zinc-900 border border-zinc-800 rounded-xl shadow-xl shadow-black/40 overflow-hidden z-50"
          style={{ animation: 'dropdown-in 0.15s ease both' }}>
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center gap-3">
            {user.photoURL
              ? <img src={user.photoURL} alt="" referrerPolicy="no-referrer" className="w-9 h-9 rounded-full object-cover flex-shrink-0" />
              : <div className="w-9 h-9 rounded-full bg-zinc-700 flex items-center justify-center text-sm font-semibold flex-shrink-0">{user.displayName?.[0] ?? '?'}</div>
            }
            <div className="min-w-0">
              <p className="text-white text-sm font-medium truncate">{user.displayName}</p>
              <p className="text-zinc-500 text-xs truncate">{user.email}</p>
            </div>
          </div>
          <a href="/profile" onClick={() => setOpen(false)}
            className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-zinc-300 hover:bg-zinc-800 hover:text-white transition-colors">
            <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
            </svg>
            My Profile
          </a>
          <button onClick={() => { signOut(auth); setOpen(false); }}
            className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors border-t border-zinc-800">
            <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 2.25 0 0 1-2.25-2.25V15m-3 0-3-3m0 0 3-3m-3 3H15" />
            </svg>
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
