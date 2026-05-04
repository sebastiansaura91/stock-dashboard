"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function AddTicker({ onAdd }: { onAdd: (ticker: string) => void }) {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const ticker = value.trim().toUpperCase();
    if (!ticker) return;
    setLoading(true);
    try {
      await api.watchlist.add(ticker);
      setValue("");
      onAdd(ticker);
    } catch {
      alert(`Failed to add ${ticker}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleAdd} className="flex gap-2">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value.toUpperCase())}
        placeholder="Add ticker (e.g. TSLA)"
        className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !value.trim()}
        className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
      >
        {loading ? "Adding…" : "Add"}
      </button>
    </form>
  );
}
