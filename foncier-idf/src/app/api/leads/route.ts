import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { createHash } from "crypto";

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));

  const email: string = (body.email ?? "").trim().toLowerCase();
  const prenom: string = (body.prenom ?? "").trim().slice(0, 80);
  const nom_famille: string = (body.nom_famille ?? "").trim().slice(0, 80);
  const nom: string = (body.nom ?? `${prenom} ${nom_famille}`.trim()).slice(0, 160);
  const societe: string = (body.societe ?? "").trim().slice(0, 120);
  const telephone: string = (body.telephone ?? "").trim().slice(0, 30);
  const consentement: boolean = body.consentement === true;

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: "Email invalide" }, { status: 400 });
  }
  if (!consentement) {
    return NextResponse.json({ error: "Consentement requis" }, { status: 400 });
  }

  const ip = req.headers.get("x-forwarded-for")?.split(",")[0] ?? "unknown";
  const ip_hash = createHash("sha256").update(ip).digest("hex").slice(0, 16);

  const { error } = await getSupabase().from("leads").upsert(
    {
      email,
      nom: nom || null,
      prenom: prenom || null,
      societe: societe || null,
      telephone: telephone || null,
      consentement,
      ip_hash,
      source: "carte_idf",
    },
    { onConflict: "email", ignoreDuplicates: true }
  );

  if (error) {
    console.error("leads insert error:", error);
    return NextResponse.json({ error: "Erreur serveur" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
