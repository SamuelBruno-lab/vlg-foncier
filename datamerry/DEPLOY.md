# Déploiement datamerry.fr

## 1. Créer les comptes (gratuits)

| Service | URL | Rôle |
|---------|-----|------|
| Mapbox | mapbox.com | Fond de carte |
| Supabase | supabase.com | Base de données PostgreSQL+PostGIS |
| Vercel | vercel.com | Hébergement Next.js |
| OVH | ovh.com | Nom de domaine datamerry.fr (~10€/an) |

---

## 2. Supabase — Setup base de données

1. Créer projet sur supabase.com
2. SQL Editor → coller et exécuter `sql/01_schema.sql`
3. Settings → API → copier :
   - Project URL → `NEXT_PUBLIC_SUPABASE_URL`
   - anon public key → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - service_role key → pour l'import Python uniquement (ne pas committer)

### Importer les données DVF

```bash
cd datamerry
pip install pandas supabase python-dotenv
# Importer IDF (75, 92, 93, 94, 95, 77)
python sql/02_import_dvf.py --dept 75 92 93 94 95 77 --csv-dir /home/user
```

> Pour la France entière : `--dept 01 02 03 ... 95`

---

## 3. Mapbox

1. Créer compte sur mapbox.com → gratuit (50k map loads/mois)
2. Dashboard → Tokens → copier le Public Token
3. Coller dans `.env.local` : `NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1...`

---

## 4. Vercel — Déploiement

```bash
npm install -g vercel
cd datamerry
vercel deploy
```

Ou connecter le repo GitHub → Vercel auto-deploy sur push.

Dans Vercel Dashboard → Settings → Environment Variables :
```
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1...
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

---

## 5. Domaine datamerry.fr

1. OVH → acheter datamerry.fr (~10€/an)
2. Vercel Dashboard → Settings → Domains → Add `datamerry.fr`
3. OVH DNS → ajouter les CNAME Vercel fournis
4. SSL automatique via Vercel (Let's Encrypt)

---

## Architecture technique

```
datamerry.fr (Vercel)
├── Next.js 14 (App Router)
│   ├── /app/page.tsx          → Page principale (carte plein écran)
│   ├── /app/api/dvf/clusters  → API dynamique selon zoom
│   └── /components/
│       ├── DvfMap.tsx         → Deck.gl + Mapbox (WebGL, millions de pts)
│       └── FilterPanel.tsx    → Filtres dept/type/année
└── Supabase (PostgreSQL + PostGIS)
    ├── dvf_points             → ~3M transactions France
    ├── dvf_clusters_commune   → ~35k communes × types
    ├── dvf_clusters_dept      → ~100 depts × types
    └── dvf_clusters_region    → ~13 régions × types
```

## Scalabilité France entière

| Niveau zoom | Table utilisée | Nb points affichés |
|-------------|---------------|-------------------|
| < 7 (France) | dvf_clusters_region | ~52 bulles |
| 7-9 (région) | dvf_clusters_dept | ~400 bulles |
| 10-12 (ville) | dvf_clusters_commune | ~35k bulles |
| ≥ 13 (rue) | dvf_points (limite 2000) | points individuels |

→ La carte reste fluide sur **toutes les données France** grâce au zoom-based clustering.
