function scoreColour(score: number): string {
  if (score >= 75) return "bg-green-500";
  if (score >= 60) return "bg-green-400";
  if (score >= 45) return "bg-amber-400";
  if (score >= 30) return "bg-red-400";
  return "bg-red-600";
}

export function ScoreBar({ score, label }: { score: number | null; label: string }) {
  if (score === null) {
    return (
      <div className="text-center">
        <div className="text-2xl font-bold text-gray-400">N/A</div>
        <div className="text-xs text-gray-400 mt-1">{label}</div>
      </div>
    );
  }
  return (
    <div>
      <div className="flex justify-between items-baseline mb-1">
        <span className="text-xs text-gray-500">{label}</span>
        <span className="text-2xl font-bold text-gray-900">{score}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${scoreColour(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
