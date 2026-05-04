import { api } from "@/lib/api";
import { WatchlistClient } from "./WatchlistClient";
import type { WatchlistItem } from "@/lib/types";

export const revalidate = 900;

export default async function WatchlistPage() {
  let items: WatchlistItem[] = [];
  try {
    items = await api.watchlist.list();
  } catch {
    // Backend not reachable — client will show empty state
  }

  return <WatchlistClient initialItems={items} />;
}
