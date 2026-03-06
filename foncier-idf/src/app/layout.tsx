import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "datamerry — 1,2M de transactions immobilières cartographiées par IA",
  description:
    "Carte interactive de toutes les ventes immobilières IDF + Oise 2020–2025. Zones de marché calculées par machine learning (HDBSCAN). Données DVF open data. 100% gratuit.",
  metadataBase: new URL("https://datamerry.com"),
  openGraph: {
    title: "datamerry — 1,2M de transactions immobilières cartographiées par IA",
    description:
      "Carte interactive de toutes les ventes immobilières IDF + Oise 2020–2025. Zones de marché calculées par machine learning (HDBSCAN). Données DVF open data. 100% gratuit.",
    url: "https://datamerry.com",
    siteName: "datamerry",
    locale: "fr_FR",
    type: "website",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Carte datamerry — Marché immobilier Île-de-France 2020-2025",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "datamerry — 1,2M de transactions immobilières cartographiées par IA",
    description: "Carte interactive IDF + Oise 2020–2025 · Machine learning · DVF open data",
    images: ["/og-image.png"],
  },
  keywords: [
    "immobilier", "Île-de-France", "DVF", "prix immobilier", "carte immobilière",
    "transactions immobilières", "datamerry", "machine learning", "HDBSCAN",
    "foncier", "Villeneuve-la-Garenne", "Oise",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
