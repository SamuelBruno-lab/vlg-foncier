import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

function median(arr: number[]): number {
  if (arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? Math.round((sorted[mid - 1] + sorted[mid]) / 2)
    : sorted[mid];
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ code: string }> }
) {
  const { code } = await params;

  // Stats par type depuis les clusters pré-calculés
  const { data: clusters, error: err1 } = await supabase
    .from("dvf_clusters_commune")
    .select("cluster_id,nom,dept,type_local,count,prix_median,prix_m2_median,lat,lon")
    .like("cluster_id", `${code}_%`);

  if (err1) return NextResponse.json({ error: err1.message }, { status: 500 });
  if (!clusters || clusters.length === 0)
    return NextResponse.json({ error: "Commune introuvable" }, { status: 404 });

  // Points bruts pour évolution année par année (5 000 max)
  const { data: points, error: err2 } = await supabase
    .from("dvf_points")
    .select("annee,prix_m2,type_local")
    .eq("code_commune", code)
    .limit(5000);

  if (err2) return NextResponse.json({ error: err2.message }, { status: 500 });

  // Zones HDBSCAN pré-calculées
  const { data: hdbscanZones } = await supabase
    .from("dvf_hdbscan_zones")
    .select(
      "id,type_local,cluster_id,count,prix_m2_median,prix_m2_p25,prix_m2_p75,prix_median,hull_coords,centroid_lat,centroid_lon,annee_min,annee_max"
    )
    .eq("code_commune", code)
    .order("type_local")
    .order("cluster_id");

  // Agrégation année × type en mémoire
  const byYear: Record<number, { prices: number[]; count: number }> = {};
  for (const p of points ?? []) {
    if (!p.annee) continue;
    if (!byYear[p.annee]) byYear[p.annee] = { prices: [], count: 0 };
    byYear[p.annee].count++;
    if (p.prix_m2) byYear[p.annee].prices.push(p.prix_m2);
  }

  const evolution = Object.entries(byYear)
    .map(([annee, { prices, count }]) => ({
      annee: parseInt(annee),
      count,
      prix_m2_median: median(prices),
    }))
    .sort((a, b) => a.annee - b.annee);

  // Infos commune (premier cluster)
  const nom = clusters[0].nom;
  const dept = clusters[0].dept;
  const lat = clusters[0].lat;
  const lon = clusters[0].lon;

  const totalCount = clusters.reduce((s, c) => s + c.count, 0);
  const allPrixM2 = clusters
    .map((c) => c.prix_m2_median)
    .filter(Boolean) as number[];

  return NextResponse.json({
    code,
    nom,
    dept,
    lat,
    lon,
    totalCount,
    prix_m2_median: median(allPrixM2),
    byType: clusters.map((c) => ({
      type: c.type_local,
      count: c.count,
      prix_median: c.prix_median,
      prix_m2_median: c.prix_m2_median,
    })),
    evolution,
    hdbscanZones: hdbscanZones ?? [],
  });
}
