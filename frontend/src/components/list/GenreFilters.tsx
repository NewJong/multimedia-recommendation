interface Props {
  genres: string[];
  selected: string[];
  onToggle: (g: string) => void;
  color: { active: string; pill: string };
}

export default function GenreFilters({ genres, selected, onToggle, color }: Props) {
  return (
    <div className="flex flex-wrap gap-2 mb-6">
      <button onClick={() => selected.forEach(g => onToggle(g))}
        className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-150 ${selected.length === 0 ? color.active : 'border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'}`}>
        All
      </button>
      {genres.map(g => (
        <button key={g} onClick={() => onToggle(g)}
          className={`px-3 py-1 rounded-full text-xs font-medium border transition-all duration-150 ${selected.includes(g) ? color.active : color.pill}`}>
          {g}
        </button>
      ))}
    </div>
  );
}
