import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { createHash } from "crypto";

// Instanciation lazy pour éviter l'erreur au build
function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const email: string = (body.email ?? "").trim().toLowerCase();
  const nom: string = (body.nom ?? "").trim().slice(0, 80);

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: "Email invalide" }, { status: 400 });
  }

  // Hash IP pour déduplication sans stocker de PII
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0] ?? "unknown";
  const ip_hash = createHash("sha256").update(ip).digest("hex").slice(0, 16);

  const { error } = await getSupabase().from("leads").upsert(
    { email, nom: nom || null, ip_hash, source: "carte_idf" },
    { onConflict: "email", ignoreDuplicates: true }
  );

  if (error) {
    console.error("leads insert error:", error);
    return NextResponse.json({ error: "Erreur serveur" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
