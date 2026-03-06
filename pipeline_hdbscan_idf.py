#!/usr/bin/env python3
"""
pipeline_hdbscan_idf.py — Pipeline HDBSCAN communes Île-de-France
==================================================================
Lit les fichiers DVF CSV (par département), applique HDBSCAN par commune
× type_local, calcule l'enveloppe convexe + stats, stocke dans Supabase.

Usage:
    python pipeline_hdbscan_idf.py                          # tous les depts présents
    python pipeline_hdbscan_idf.py --download               # télécharge depts manquants
    python pipeline_hdbscan_idf.py --dept 92 77 78          # filtrer depts
    python pipeline_hdbscan_idf.py --commune 92078          # une seule commune
    python pipeline_hdbscan_idf.py --skip-upload            # calcul local seulement

Dépendances:
    pip install pandas numpy hdbscan scipy httpx python-dotenv requests tqdm
"""

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import hdbscan
from dotenv import load_dotenv
from scipy.spatial import ConvexHull

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR = Path("/home/user")
ENV_FILE = DATA_DIR / "foncier-idf" / ".env.local"

IDF_DEPTS = ["75", "77", "78", "91", "92", "93", "94", "95"]

# Colonnes nécessaires depuis les CSV
COLS_KEEP = {
    "annee", "id_mutation", "id_parcelle", "date_mutation", "nature_mutation",
    "valeur_fonciere", "adresse_numero", "adresse_nom_voie",
    "code_commune", "nom_commune", "code_departement",
    "type_local", "surface_reelle_bati", "nombre_pieces_principales",
    "latitude", "longitude",
}

# Seuils prix/m² (filtre outliers)
PRIX_M2_MAX = {
    "Appartement": 20000,
    "Maison": 15000,
    "Local industriel. commercial ou assimilé": 15000,
}
PRIX_M2_MIN = 500  # plancher global

# URLs DVF géocodées par année/département (geo-dvf.etalab.gouv.fr)
DVF_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/{dept}.csv.gz"
DVF_YEARS = [2020, 2021, 2022, 2023, 2024]  # 2025 partiel selon disponibilité


# ── Utilitaires ───────────────────────────────────────────────────────────────

def load_env():
    load_dotenv(ENV_FILE)
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(f"Variables Supabase manquantes dans {ENV_FILE}")
    return url, key


def download_dept(dept: str, dest: Path, years: list[int] = DVF_YEARS) -> bool:
    """
    Télécharge et fusionne les fichiers DVF annuels pour un département.
    Retourne True si le fichier a été créé/mis à jour.
    """
    frames = []
    for year in years:
        url = DVF_URL.format(year=year, dept=dept)
        print(f"  Téléchargement {url}...")
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=120)
            resp.raise_for_status()
            with gzip.open(io.BytesIO(resp.content)) as f:
                df = pd.read_csv(f, low_memory=False)
                df["annee"] = year
                frames.append(df)
                print(f"    → {len(df):,} lignes")
        except Exception as e:
            print(f"    ⚠ Erreur {year}: {e}")

    if not frames:
        return False

    merged = pd.concat(frames, ignore_index=True)
    merged.to_csv(dest, index=False)
    print(f"  ✅ Sauvegardé: {dest} ({len(merged):,} lignes)")
    return True


def load_csv_dept(dept: str, csv_path: Path) -> pd.DataFrame:
    """Charge et nettoie un fichier CSV DVF départemental."""
    print(f"  Lecture {csv_path.name} ({csv_path.stat().st_size // 1_000_000} MB)...")

    df = pd.read_csv(csv_path, low_memory=False, usecols=lambda c: c in COLS_KEEP)

    # Nettoyage de base
    df = df.dropna(subset=["latitude", "longitude", "valeur_fonciere"])
    df = df[pd.to_numeric(df["valeur_fonciere"], errors="coerce") > 0]
    df = df.drop_duplicates(subset=["id_mutation", "id_parcelle"])

    # Exclusion VEFA Maisons (prix promoteur gonflé)
    if "nature_mutation" in df.columns:
        mask_vefa_maison = (
            (df.get("nature_mutation", "") == "Vente en l'état futur d'achèvement")
            & (df.get("type_local", "") == "Maison")
        )
        df = df[~mask_vefa_maison]

    # Types numériques
    df["valeur_fonciere"] = pd.to_numeric(df["valeur_fonciere"], errors="coerce")
    df["surface_reelle_bati"] = pd.to_numeric(df["surface_reelle_bati"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Prix au m²
    df["prix_m2"] = np.where(
        df["surface_reelle_bati"] > 0,
        df["valeur_fonciere"] / df["surface_reelle_bati"],
        np.nan,
    )

    # Filtre outliers prix/m²
    df = df[df["prix_m2"].isna() | (df["prix_m2"] >= PRIX_M2_MIN)]
    for type_local, max_val in PRIX_M2_MAX.items():
        mask = (df["type_local"] == type_local) & (df["prix_m2"] > max_val)
        df = df[~mask]

    # Code département depuis code_commune si absent
    if "code_departement" not in df.columns or df["code_departement"].isna().all():
        df["code_departement"] = df["code_commune"].astype(str).str[:2]

    # Filtrer sur IDF uniquement
    df = df[df["code_departement"].astype(str).isin(IDF_DEPTS)]

    print(f"    → {len(df):,} transactions IDF valides (dept {dept})")
    return df


# ── HDBSCAN par commune × type ─────────────────────────────────────────────

def hdbscan_params(n: int, type_local: str = "") -> dict | None:
    """
    Paramètres adaptatifs par type de bien.

    MAISONS — cluster_selection_method="leaf"
      Préserve les micro-zones géographiquement proches à prix distincts
      (ex: quartiers pavillonnaires mitoyens à 150m d'écart).
      min_cluster_size petit car le stock de maisons est rare.

    APPARTEMENTS / COMMERCES — cluster_selection_method="eom"
      min_cluster_size = max(type_min, round(n * 0.08))
      Règle empirique : ~8% des transactions par zone → nombre de zones
      proportionnel à la densité du marché.
      Exemple: 386 apparts → mcs=30 → 6 zones (Bongarde, Sorbiers, Ponant…)
               45 commerces → mcs=5  → 4 zones (ZI Nord, 8-Mai-45…)
    """
    if n < 12:
        return None

    is_maison = type_local == "Maison"

    if is_maison:
        # Maisons : leaf, min_cluster_size fixe selon volume
        if n < 40:
            mcs = 4
        elif n < 150:
            mcs = 6
        else:
            mcs = 8
        return {
            "min_cluster_size": mcs,
            "min_samples": 2,
            "cluster_selection_method": "leaf",
        }
    else:
        # Appartements & Commerces : eom, mcs proportionnel (≈8%)
        type_min = 5 if "Local" in type_local else 8
        mcs = max(type_min, round(n * 0.08))
        ms = 3 if n > 100 else 2
        return {
            "min_cluster_size": mcs,
            "min_samples": ms,
            "cluster_selection_method": "eom",
        }


def process_commune_type(
    code_commune: str,
    nom_commune: str,
    dept: str,
    type_local: str,
    sub: pd.DataFrame,
) -> list[dict]:
    """
    Applique HDBSCAN sur un sous-ensemble commune × type_local.
    Retourne la liste des zones (clusters) à insérer dans dvf_hdbscan_zones.
    """
    params = hdbscan_params(len(sub), type_local)
    if params is None:
        return []

    coords = np.radians(sub[["latitude", "longitude"]].values)

    try:
        clusterer = hdbscan.HDBSCAN(
            metric="haversine",
            **params,
        )
        labels = clusterer.fit_predict(coords)
    except Exception as e:
        print(f"    HDBSCAN erreur {code_commune}/{type_local}: {e}")
        return []

    sub = sub.copy()
    sub["cluster"] = labels

    zones = []
    for cid in sorted(set(labels)):
        if cid < 0:  # bruit
            continue

        grp = sub[sub["cluster"] == cid]
        pts = grp[["latitude", "longitude"]].values

        # Polygone convexe (besoin d'au moins 3 points distincts)
        hull_coords = None
        if len(pts) >= 3:
            try:
                hull = ConvexHull(pts)
                hull_pts = pts[hull.vertices].tolist()
                hull_pts.append(hull_pts[0])  # fermer le polygone
                hull_coords = hull_pts  # [[lat, lon], ...]
            except Exception:
                pass

        prix_m2_vals = grp["prix_m2"].dropna().values
        centroid = pts.mean(axis=0)

        # Nettoyage du nom de type pour ID
        type_slug = (
            type_local.replace(" ", "_").replace(".", "").replace(",", "")[:30]
        )
        zone_id = f"{code_commune}_{type_slug}_{cid}"

        zones.append({
            "id": zone_id,
            "code_commune": code_commune,
            "nom_commune": nom_commune,
            "dept": dept,
            "type_local": type_local,
            "cluster_id": int(cid),
            "count": int(len(grp)),
            "prix_m2_median": int(np.median(prix_m2_vals)) if len(prix_m2_vals) > 0 else None,
            "prix_m2_p25": int(np.percentile(prix_m2_vals, 25)) if len(prix_m2_vals) > 0 else None,
            "prix_m2_p75": int(np.percentile(prix_m2_vals, 75)) if len(prix_m2_vals) > 0 else None,
            "prix_median": int(grp["valeur_fonciere"].median()) if grp["valeur_fonciere"].notna().any() else None,
            "hull_coords": hull_coords,
            "centroid_lat": float(centroid[0]),
            "centroid_lon": float(centroid[1]),
            "annee_min": int(grp["annee"].min()) if "annee" in grp.columns else None,
            "annee_max": int(grp["annee"].max()) if "annee" in grp.columns else None,
        })

    return zones


def run_hdbscan_all(df: pd.DataFrame, commune_filter: str | None = None) -> list[dict]:
    """
    Applique HDBSCAN pour toutes les communes × types dans le DataFrame.
    Retourne la liste complète des zones.
    """
    all_zones = []
    types_cibles = [
        "Appartement",
        "Maison",
        "Local industriel. commercial ou assimilé",
    ]

    communes = df["code_commune"].dropna().unique()
    if commune_filter:
        communes = [c for c in communes if c == commune_filter]

    total = len(communes)
    print(f"\n  {total} communes à traiter...")

    for i, code_commune in enumerate(sorted(communes), 1):
        comm_df = df[df["code_commune"] == code_commune]
        nom_commune = comm_df["nom_commune"].iloc[0] if "nom_commune" in comm_df.columns else code_commune
        dept = str(comm_df["code_departement"].iloc[0]) if "code_departement" in comm_df.columns else code_commune[:2]

        commune_zones = []
        for type_local in types_cibles:
            sub = comm_df[comm_df["type_local"] == type_local].copy()
            if len(sub) < 5:
                continue
            zones = process_commune_type(code_commune, nom_commune, dept, type_local, sub)
            commune_zones.extend(zones)

        all_zones.extend(commune_zones)

        if i % 50 == 0 or i == total:
            n_zones = len(all_zones)
            print(f"  [{i}/{total}] {code_commune} — {len(commune_zones)} zones | total: {n_zones}", end="\r")

    print()
    return all_zones


# ── Upload Supabase ──────────────────────────────────────────────────────────

def upsert_zones(zones: list[dict], supabase_url: str, supabase_key: str, batch_size: int = 200):
    """Upsert les zones HDBSCAN dans Supabase par lots."""
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    url = f"{supabase_url}/rest/v1/dvf_hdbscan_zones?on_conflict=id"
    total = len(zones)

    def clean(v):
        if v is None:
            return None
        if hasattr(v, "item"):
            v = v.item()
        if isinstance(v, float) and (v != v or abs(v) == float("inf")):
            return None
        return v

    print(f"\n  Upload {total} zones → Supabase...")

    with httpx.Client(timeout=90) as client:
        for i in range(0, total, batch_size):
            batch = zones[i : i + batch_size]
            batch_clean = [{k: clean(val) for k, val in row.items()} for row in batch]
            # hull_coords est déjà une liste Python, pas besoin de sérialisation
            resp = client.post(url, headers=headers, json=batch_clean)
            if resp.status_code not in (200, 201):
                print(f"\n  ERREUR {resp.status_code}: {resp.text[:400]}")
                return False
            print(f"  {min(i + batch_size, total)}/{total} zones uploadées", end="\r")
            time.sleep(0.05)  # éviter rate limiting

    print(f"\n  ✅ {total} zones uploadées")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pipeline HDBSCAN communes IDF")
    parser.add_argument("--dept", nargs="+", default=IDF_DEPTS, help="Départements à traiter")
    parser.add_argument("--commune", help="Traiter une seule commune (code INSEE)")
    parser.add_argument("--download", action="store_true", help="Télécharger depts manquants")
    parser.add_argument("--skip-upload", action="store_true", help="Calcul sans upload Supabase")
    parser.add_argument("--csv-dir", default=str(DATA_DIR), help="Dossier des fichiers CSV")
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir)

    print("=" * 60)
    print("Pipeline HDBSCAN — Communes Île-de-France")
    print("=" * 60)

    # ── 1. Téléchargement depts manquants ─────────────────────────────────────
    if args.download:
        print("\n[1] Téléchargement des depts manquants...")
        for dept in args.dept:
            dest = csv_dir / f"dvf_{dept}.csv"
            if dest.exists():
                print(f"  dept {dept}: déjà présent ({dest.stat().st_size // 1_000_000} MB), skip")
                continue
            print(f"  dept {dept}: téléchargement en cours...")
            download_dept(dept, dest)
    else:
        print("\n[1] (Téléchargement ignoré — utiliser --download si nécessaire)")

    # ── 2. Chargement CSV ─────────────────────────────────────────────────────
    print("\n[2] Chargement des fichiers CSV...")
    all_frames = []
    loaded_depts = []

    for dept in args.dept:
        csv_path = csv_dir / f"dvf_{dept}.csv"
        if not csv_path.exists():
            print(f"  dept {dept}: fichier manquant ({csv_path}), skip")
            print(f"    → Relancer avec --download pour télécharger")
            continue
        try:
            df = load_csv_dept(dept, csv_path)
            all_frames.append(df)
            loaded_depts.append(dept)
        except Exception as e:
            print(f"  dept {dept}: erreur de lecture — {e}")

    if not all_frames:
        print("Aucune donnée chargée. Vérifier les fichiers CSV.")
        sys.exit(1)

    data = pd.concat(all_frames, ignore_index=True)
    print(f"\n  Total: {len(data):,} transactions | {len(loaded_depts)} depts: {', '.join(loaded_depts)}")
    print(f"  Communes: {data['code_commune'].nunique():,}")
    print(f"  Types: {data['type_local'].value_counts().to_dict()}")

    # ── 3. HDBSCAN ────────────────────────────────────────────────────────────
    print("\n[3] Calcul HDBSCAN par commune × type...")
    t0 = time.time()
    all_zones = run_hdbscan_all(data, commune_filter=args.commune)
    elapsed = time.time() - t0
    print(f"\n  {len(all_zones)} zones calculées en {elapsed:.0f}s")

    if not all_zones:
        print("Aucune zone produite.")
        sys.exit(0)

    # Stats résumé
    types_count = {}
    for z in all_zones:
        t = z["type_local"]
        types_count[t] = types_count.get(t, 0) + 1
    for t, n in sorted(types_count.items(), key=lambda x: -x[1]):
        print(f"  {t[:40]:<40} {n:>5} zones")

    # ── 4. Upload Supabase ────────────────────────────────────────────────────
    if args.skip_upload:
        print("\n[4] Upload ignoré (--skip-upload)")
        # Sauvegarde locale pour inspection
        out = csv_dir / "hdbscan_zones_idf.json"
        with open(out, "w") as f:
            json.dump(all_zones, f, ensure_ascii=False, indent=2)
        print(f"  Zones sauvegardées localement: {out}")
        return

    print("\n[4] Upload vers Supabase...")
    try:
        supabase_url, supabase_key = load_env()
    except RuntimeError as e:
        print(f"  ERREUR: {e}")
        sys.exit(1)

    success = upsert_zones(all_zones, supabase_url, supabase_key)

    if success:
        print(f"\n✅ Pipeline terminé — {len(all_zones)} zones HDBSCAN dans Supabase")
        print(f"   Communes traitées: {len(set(z['code_commune'] for z in all_zones))}")
        print(f"   Depts: {', '.join(sorted(set(z['dept'] for z in all_zones)))}")
    else:
        print("\n❌ Erreur lors de l'upload")
        sys.exit(1)


if __name__ == "__main__":
    main()
