import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stock Dashboard",
  description: "Technical, fundamental, and sentiment analysis for equities",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <nav className="border-b border-gray-200 bg-white px-6 py-3 flex items-center gap-8">
          <span className="font-semibold text-gray-900 text-lg">📈 StockDash</span>
          <a href="/watchlist" className="text-sm text-gray-600 hover:text-gray-900">Watchlist</a>
          <a href="/screener" className="text-sm text-gray-600 hover:text-gray-900">Screener</a>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
