export function DriverList({ drivers, title }: { drivers: string[]; title: string }) {
  if (!drivers.length) return null;
  return (
    <details open>
      <summary className="cursor-pointer text-sm font-semibold text-gray-700 mb-2 select-none">
        {title}
      </summary>
      <ul className="space-y-1 mt-2">
        {drivers.map((d, i) => (
          <li key={i} className="text-sm text-gray-600 flex gap-2">
            <span className="text-gray-300 mt-0.5">•</span>
            <span>{d}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
