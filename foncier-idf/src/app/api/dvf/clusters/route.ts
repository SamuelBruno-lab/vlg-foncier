import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const dept = searchParams.get("dept")?.split(",").filter(Boolean) ?? [];
  const zoom = parseInt(searchParams.get("zoom") ?? "10");
  const type_local = searchParams.get("type_local");
  const annee_min = parseInt(searchParams.get("annee_min") ?? "2020");
  const annee_max = parseInt(searchParams.get("annee_max") ?? "2025");

  // Zoom > 13 → points bruts (max 2000), sinon clusters
  if (zoom >= 13) {
    let q = supabase
      .from("dvf_points")
      .select("id,lat,lon,valeur_fonciere,prix_m2,surface,type_local,date_mutation,adresse,commune,dept,annee")
      .gte("annee", annee_min)
      .lte("annee", annee_max)
      .limit(2000);

    if (dept.length > 0) q = q.in("dept", dept);
    if (type_local) q = q.eq("type_local", type_local);

    const { data, error } = await q;
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });
    return NextResponse.json({ mode: "points", data });
  }

  // Zoom < 13 → clusters pré-calculés
  const cluster_level = zoom >= 10 ? "commune" : zoom >= 7 ? "dept" : "region";

  let q = supabase
    .from(`dvf_clusters_${cluster_level}`)
    .select("cluster_id,lat,lon,count,prix_median,prix_m2_median,dept,type_local,nom")
    .gte("annee_min", annee_min)
    .lte("annee_max", annee_max);

  if (dept.length > 0) q = q.in("dept", dept);
  if (type_local) q = q.eq("type_local", type_local);

  const { data, error } = await q;
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ mode: cluster_level, data });
}
