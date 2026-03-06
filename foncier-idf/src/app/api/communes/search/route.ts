import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q")?.trim() ?? "";
  if (q.length < 2) return NextResponse.json([]);

  const { data, error } = await supabase
    .from("dvf_hdbscan_zones")
    .select("code_commune, nom_commune")
    .ilike("nom_commune", `%${q}%`)
    .order("nom_commune")
    .limit(200); // on déduplique côté serveur

  if (error) return NextResponse.json([], { status: 500 });

  // Dédupliquer par code_commune
  const seen = new Set<string>();
  const results: { code: string; nom: string }[] = [];
  for (const row of data ?? []) {
    if (!seen.has(row.code_commune)) {
      seen.add(row.code_commune);
      results.push({ code: row.code_commune, nom: row.nom_commune });
    }
    if (results.length >= 10) break;
  }

  return NextResponse.json(results);
}
