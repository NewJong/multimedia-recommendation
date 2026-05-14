interface Tab<K extends string> { key: K; label: string }

interface Props<K extends string> {
  tabs: Tab<K>[];
  current: K;
  onChange: (k: K) => void;
  activeText: string;
  activeBar: string;
}

export default function SortTabs<K extends string>({ tabs, current, onChange, activeText, activeBar }: Props<K>) {
  return (
    <div className="flex items-center gap-1 mb-5 border-b border-zinc-800/60 pb-1">
      {tabs.map(tab => (
        <button key={tab.key} onClick={() => onChange(tab.key)}
          className={`relative px-3 py-1.5 rounded-t-lg text-sm font-medium transition-all duration-200 ${current === tab.key ? activeText : 'text-zinc-500 hover:text-zinc-300'}`}>
          {tab.label}
          {current === tab.key && <span className={`absolute bottom-0 left-0 right-0 h-0.5 ${activeBar} rounded-full`} />}
        </button>
      ))}
    </div>
  );
}
