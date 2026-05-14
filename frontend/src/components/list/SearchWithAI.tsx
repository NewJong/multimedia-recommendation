import { useState } from 'react';

interface Props {
  value: string;
  onChange: (v: string) => void;
  /** Tailwind class for the focus border (e.g. `focus-within:border-emerald-500`). */
  focusBorder: string;
  /** CSS box-shadow for the focus ring (e.g. `0 0 0 3px rgba(16,185,129,0.15)`). */
  focusRing: string;
  /** Tailwind classes for the AI pill when enabled (e.g. `bg-emerald-500/20 text-emerald-300`). */
  aiActiveCls: string;
  placeholder?: string;
}

/**
 * Compact search input with an inline "✦ AI" button that hands off the query
 * to /search?q=...&ai=1 — the existing AI-search page handles everything else.
 */
export default function SearchWithAI({ value, onChange, focusBorder, focusRing, aiActiveCls, placeholder = 'Search…' }: Props) {
  const [focused, setFocused] = useState(false);
  const canSubmit = value.trim().length > 0;
  const submit = () => {
    if (!canSubmit) return;
    window.location.href = `/search?q=${encodeURIComponent(value.trim())}&ai=1`;
  };
  return (
    <div
      className={`flex items-center bg-zinc-900 border border-zinc-800 rounded-xl pl-3 pr-1 ${focusBorder} transition-all duration-200`}
      style={{ boxShadow: focused ? focusRing : 'none' }}
    >
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onKeyDown={e => { if (e.key === 'Enter' && e.metaKey) submit(); }}
        className="bg-transparent py-2 text-sm text-white placeholder-zinc-600 focus:outline-none w-44"
      />
      <button
        onClick={submit}
        disabled={!canSubmit}
        title={canSubmit ? 'AI search across all domains (Cmd+Enter)' : 'Type to enable AI search'}
        className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold transition-all flex-shrink-0 ${canSubmit ? aiActiveCls : 'text-zinc-600 cursor-not-allowed'}`}
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/>
        </svg>
        AI
      </button>
    </div>
  );
}
