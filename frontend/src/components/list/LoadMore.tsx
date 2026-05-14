interface Props {
  visible: number;
  total: number;
  onMore: () => void;
  hoverColor: string;
}

export default function LoadMore({ visible, total, onMore, hoverColor }: Props) {
  if (visible >= total) return null;
  return (
    <div className="mt-8 flex flex-col items-center gap-2">
      <p className="text-zinc-600 text-xs">{visible} of {total}</p>
      <button onClick={onMore}
        className={`px-6 py-2.5 rounded-xl border border-zinc-700 text-zinc-300 text-sm font-medium ${hoverColor} transition-all duration-200`}>
        Load more
      </button>
    </div>
  );
}
