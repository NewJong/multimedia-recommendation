import { useState, useRef, useEffect, useCallback } from 'react';
import { Pencil, ExternalLink, Copy, Check } from 'lucide-react';
import { API_BASE } from '../lib/api';

export interface Socials {
  social_telegram?:  string;
  social_instagram?: string;
  social_steam?:     string;
  social_discord?:   string;
  social_tiktok?:    string;
}

interface Platform {
  key:   keyof Socials;
  label: string;
  color: string;
  hoverBg: string;
  getUrl:     (v: string) => string | null;
  getDisplay: (v: string) => string;
  placeholder: string;
  icon: React.ReactNode;
}

const PLATFORMS: Platform[] = [
  {
    key: 'social_telegram',
    label: 'Telegram',
    color: '#2AABEE',
    hoverBg: 'hover:bg-[#2AABEE]/15',
    getUrl: v => `https://t.me/${v.replace(/^@/, '')}`,
    getDisplay: v => v.startsWith('@') ? v : `@${v}`,
    placeholder: '@username',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
      </svg>
    ),
  },
  {
    key: 'social_instagram',
    label: 'Instagram',
    color: '#E1306C',
    hoverBg: 'hover:bg-[#E1306C]/15',
    getUrl: v => v.startsWith('http') ? v : `https://instagram.com/${v.replace(/^@/, '')}`,
    getDisplay: v => {
      if (!v.startsWith('http')) return v.startsWith('@') ? v : `@${v}`;
      try { const m = new URL(v).pathname.replace(/\//g, ''); return `@${m}`; } catch { return v; }
    },
    placeholder: '@username or URL',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
      </svg>
    ),
  },
  {
    key: 'social_steam',
    label: 'Steam',
    color: '#b8c7dc',
    hoverBg: 'hover:bg-white/10',
    getUrl: v => v.startsWith('http') ? v : `https://steamcommunity.com/id/${v}`,
    getDisplay: v => {
      if (!v.startsWith('http')) return v;
      try { return new URL(v).pathname.replace(/\//g, '') || 'Steam'; } catch { return 'Steam'; }
    },
    placeholder: 'profile URL or username',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M11.979 0C5.678 0 .511 4.86.022 11.037l6.432 2.658c.545-.371 1.203-.59 1.912-.59.063 0 .125.004.188.006l2.861-4.142V8.91c0-2.495 2.028-4.524 4.524-4.524 2.494 0 4.524 2.031 4.524 4.527s-2.03 4.525-4.524 4.525h-.105l-4.076 2.911c0 .052.004.105.004.159 0 1.875-1.515 3.396-3.39 3.396-1.635 0-3.016-1.173-3.331-2.727L.436 15.27C1.862 20.307 6.486 24 11.979 24c6.627 0 11.999-5.373 11.999-12S18.606 0 11.979 0zM7.54 18.21l-1.473-.61c.262.543.714.999 1.314 1.25 1.297.539 2.793-.076 3.332-1.375.263-.63.264-1.319.005-1.949s-.75-1.121-1.377-1.383c-.624-.26-1.29-.249-1.878-.03l1.523.63c.956.4 1.409 1.5 1.009 2.455-.397.957-1.497 1.41-2.455 1.012H7.54zm11.415-9.303c0-1.662-1.353-3.015-3.015-3.015-1.665 0-3.015 1.353-3.015 3.015 0 1.665 1.35 3.015 3.015 3.015 1.663 0 3.015-1.35 3.015-3.015zm-5.273-.005c0-1.252 1.013-2.266 2.265-2.266 1.249 0 2.266 1.014 2.266 2.266 0 1.251-1.017 2.265-2.266 2.265-1.252 0-2.265-1.014-2.265-2.265z"/>
      </svg>
    ),
  },
  {
    key: 'social_discord',
    label: 'Discord',
    color: '#5865F2',
    hoverBg: 'hover:bg-[#5865F2]/15',
    getUrl: () => null, // no universal profile URL
    getDisplay: v => v,
    placeholder: 'username',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057.1 18.079.112 18.1.13 18.113a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
      </svg>
    ),
  },
  {
    key: 'social_tiktok',
    label: 'TikTok',
    color: '#ffffff',
    hoverBg: 'hover:bg-white/10',
    getUrl: v => `https://tiktok.com/@${v.replace(/^@/, '')}`,
    getDisplay: v => v.startsWith('@') ? v : `@${v}`,
    placeholder: '@username',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.75a8.16 8.16 0 0 0 4.77 1.52V6.82a4.85 4.85 0 0 1-1-.13z"/>
      </svg>
    ),
  },
];


interface EditModalProps {
  uid: string;
  socials: Socials;
  onClose: () => void;
  onSaved: (s: Socials) => void;
}

export function SocialEditModal({ uid, socials, onClose, onSaved }: EditModalProps) {
  const [form, setForm] = useState({
    telegram:  socials.social_telegram  ?? '',
    instagram: socials.social_instagram ?? '',
    steam:     socials.social_steam     ?? '',
    discord:   socials.social_discord   ?? '',
    tiktok:    socials.social_tiktok    ?? '',
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await fetch(`${API_BASE}/users/${uid}/socials`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      onSaved({
        social_telegram:  form.telegram,
        social_instagram: form.instagram,
        social_steam:     form.steam,
        social_discord:   form.discord,
        social_tiktok:    form.tiktok,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-zinc-900 border border-zinc-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
        <h2 className="text-white font-semibold text-lg mb-5">Social Links</h2>
        <div className="space-y-3">
          {PLATFORMS.map(p => (
            <div key={p.key} className="flex items-center gap-3">
              <span style={{ color: p.color }} className="flex-shrink-0 w-5">{p.icon}</span>
              <div className="flex-1">
                <input
                  type="text"
                  value={form[p.key.replace('social_', '') as keyof typeof form]}
                  onChange={e => setForm(prev => ({ ...prev, [p.key.replace('social_', '')]: e.target.value }))}
                  placeholder={p.placeholder}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-500 transition-colors"
                />
              </div>
            </div>
          ))}
        </div>
        <div className="flex gap-3 mt-6">
          <button onClick={onClose}
            className="flex-1 px-4 py-2 rounded-xl border border-zinc-700 text-zinc-400 hover:text-zinc-200 text-sm transition-colors">
            Cancel
          </button>
          <button onClick={save} disabled={saving}
            className="flex-1 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 border border-zinc-600 text-white text-sm font-medium transition-colors disabled:opacity-50">
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}


interface OwnSocialRowProps {
  uid: string;
  socials: Socials;
  onUpdate: (s: Socials) => void;
}

export function OwnSocialRow({ uid, socials, onUpdate }: OwnSocialRowProps) {
  const [editing, setEditing] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [openKey, setOpenKey] = useState<string | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback((key: string) => {
    if (hideTimer.current) clearTimeout(hideTimer.current);
    setOpenKey(key);
  }, []);

  const hide = useCallback(() => {
    hideTimer.current = setTimeout(() => setOpenKey(null), 120);
  }, []);

  async function copy(text: string, key: string) {
    await navigator.clipboard.writeText(text).catch(() => {});
    setCopied(key);
    setTimeout(() => setCopied(null), 1500);
  }

  return (
    <>
      <div className="flex items-center gap-1.5 flex-wrap">
        {PLATFORMS.map(p => {
          const val = socials[p.key] ?? '';
          const hasVal = val.trim().length > 0;
          const url = hasVal ? p.getUrl(val) : null;
          const display = hasVal ? p.getDisplay(val) : '';
          const isOpen = openKey === p.key;

          return (
            <div key={p.key} className="relative"
              onMouseEnter={() => hasVal && show(p.key)}
              onMouseLeave={hide}>
              <button
                onClick={() => setEditing(true)}
                className={`w-8 h-8 rounded-lg flex items-center justify-center border transition-all duration-150 ${
                  hasVal
                    ? 'border-zinc-700 hover:border-zinc-500'
                    : 'border-dashed border-zinc-700 hover:border-zinc-500'
                }`}
                style={hasVal ? { color: p.color } : { color: '#52525b' }}
                title={hasVal ? display : `Add ${p.label}`}
              >
                {hasVal ? p.icon : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                )}
              </button>

              {hasVal && isOpen && (
                <div
                  className="absolute left-full top-1/2 -translate-y-1/2 z-[60] flex items-center pl-2"
                  onMouseEnter={() => show(p.key)}
                  onMouseLeave={hide}>
                  <div className="w-2 h-2 bg-zinc-800 border-l border-b border-zinc-700 rotate-45 -mr-1 flex-shrink-0" />
                  <div className="bg-zinc-800 border border-zinc-700 rounded-xl px-3 py-2 shadow-xl text-xs whitespace-nowrap flex flex-col gap-1.5 min-w-max">
                    <p className="font-medium" style={{ color: p.color }}>{p.label}</p>
                    <p className="text-zinc-300">{display}</p>
                    <div className="flex gap-1.5 mt-0.5">
                      {url && (
                        <a href={url} target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-1 text-zinc-400 hover:text-white bg-zinc-700 hover:bg-zinc-600 rounded-lg px-2 py-1 transition-colors">
                          <ExternalLink size={11} />
                          <span>Open</span>
                        </a>
                      )}
                      {!url && (
                        <button onClick={() => copy(val, p.key)}
                          className="flex items-center gap-1 text-zinc-400 hover:text-white bg-zinc-700 hover:bg-zinc-600 rounded-lg px-2 py-1 transition-colors">
                          {copied === p.key ? <Check size={11} /> : <Copy size={11} />}
                          <span>{copied === p.key ? 'Copied' : 'Copy'}</span>
                        </button>
                      )}
                      <button onClick={() => setEditing(true)}
                        className="flex items-center gap-1 text-zinc-400 hover:text-white bg-zinc-700 hover:bg-zinc-600 rounded-lg px-2 py-1 transition-colors">
                        <Pencil size={11} />
                        <span>Edit</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        <button onClick={() => setEditing(true)}
          className="w-8 h-8 rounded-lg flex items-center justify-center border border-zinc-700 hover:border-zinc-500 text-zinc-600 hover:text-zinc-300 transition-all duration-150"
          title="Edit social links">
          <Pencil size={14} />
        </button>
      </div>

      {editing && (
        <SocialEditModal
          uid={uid}
          socials={socials}
          onClose={() => setEditing(false)}
          onSaved={onUpdate}
        />
      )}
    </>
  );
}

// ── Visitor social row (read-only, clickable) ───────────────────────────────

interface VisitorSocialRowProps {
  socials: Socials;
}

export function VisitorSocialRow({ socials }: VisitorSocialRowProps) {
  const [copied, setCopied] = useState<string | null>(null);

  const filled = PLATFORMS.filter(p => (socials[p.key] ?? '').trim().length > 0);
  if (filled.length === 0) return null;

  async function copy(text: string, key: string) {
    await navigator.clipboard.writeText(text).catch(() => {});
    setCopied(key);
    setTimeout(() => setCopied(null), 1500);
  }

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {filled.map(p => {
        const val = socials[p.key]!;
        const url = p.getUrl(val);
        const display = p.getDisplay(val);

        if (url) {
          return (
            <a key={p.key} href={url} target="_blank" rel="noopener noreferrer"
              title={`${p.label}: ${display}`}
              className={`w-8 h-8 rounded-lg flex items-center justify-center border border-zinc-700 hover:border-zinc-500 transition-all duration-150 ${p.hoverBg}`}
              style={{ color: p.color }}>
              {p.icon}
            </a>
          );
        }

        // Discord — copy to clipboard
        return (
          <button key={p.key}
            onClick={() => copy(val, p.key)}
            title={`${p.label}: ${display} — click to copy`}
            className={`w-8 h-8 rounded-lg flex items-center justify-center border border-zinc-700 hover:border-zinc-500 transition-all duration-150 ${p.hoverBg} relative group/copy`}
            style={{ color: p.color }}>
            {copied === p.key
              ? <Check size={14} className="text-green-400" />
              : p.icon
            }
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/copy:block bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1 text-xs text-zinc-300 whitespace-nowrap z-10">
              {display}
            </span>
          </button>
        );
      })}
    </div>
  );
}
