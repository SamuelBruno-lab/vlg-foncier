"""
datamerry — Import CSV DVF → Supabase
Usage: python sql/02_import_dvf.py --dept 75 93 94 95 77 92

Prérequis:
  pip install pandas supabase python-dotenv
  Fichiers CSV: dvf_75.csv, dvf_93.csv, etc. dans /home/user/
"""

import argparse
import os
import hashlib
import pandas as pd
import numpy as np
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(".env.local")

SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
SUPABASE_KEY = os.environ["NEXT_PUBLIC_SUPABASE_ANON_KEY"]  # utiliser service role key en prod

DEPT_COORDS = {
    "75": (48.8566, 2.3522, "Île-de-France"),
    "77": (48.6, 2.8, "Île-de-France"),
    "78": (48.8, 1.97, "Île-de-France"),
    "91": (48.6, 2.25, "Île-de-France"),
    "92": (48.85, 2.25, "Île-de-France"),
    "93": (48.91, 2.47, "Île-de-France"),
    "94": (48.79, 2.47, "Île-de-France"),
    "95": (49.0, 2.1, "Île-de-France"),
}

COLS_KEEP = [
    "id_mutation", "id_parcelle", "date_mutation", "valeur_fonciere",
    "adresse_numero", "adresse_nom_voie", "code_commune", "nom_commune",
    "code_departement", "latitude", "longitude",
    "type_local", "surface_reelle_bati", "nombre_pieces_principales",
]


def make_id(row):
    key = f"{row.get('id_mutation','')}-{row.get('id_parcelle','')}-{row.get('latitude','')}-{row.get('longitude','')}"
    return hashlib.md5(key.encode()).hexdigest()[:20]


def load_dept(dept: str, csv_path: str) -> pd.DataFrame:
    print(f"  Lecture {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False, usecols=lambda c: c in COLS_KEEP)
    df = df.dropna(subset=["latitude", "longitude", "valeur_fonciere"])
    df = df[df["valeur_fonciere"] > 0]
    df = df.drop_duplicates(subset=["id_mutation", "id_parcelle"])

    df["valeur_fonciere"] = pd.to_numeric(df["valeur_fonciere"], errors="coerce").astype("Int64")
    df["surface_reelle_bati"] = pd.to_numeric(df["surface_reelle_bati"], errors="coerce").astype("Int64")
    df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")
    df["annee"] = df["date_mutation"].dt.year.astype("Int64")
    df["prix_m2"] = np.where(
        df["surface_reelle_bati"] > 0,
        (df["valeur_fonciere"] / df["surface_reelle_bati"]).round().astype("Int64"),
        pd.NA,
    )

    df["adresse"] = (
        df["adresse_numero"].fillna("").astype(str).str.strip()
        + " "
        + df["adresse_nom_voie"].fillna("").astype(str).str.strip()
    ).str.strip()
    df["adresse"] = df["adresse"].replace("", None)

    dept_lat, dept_lon, region = DEPT_COORDS.get(dept, (None, None, None))

    records = []
    for _, row in df.iterrows():
        records.append({
            "id": make_id(row),
            "lat": float(row["latitude"]),
            "lon": float(row["longitude"]),
            "valeur_fonciere": int(row["valeur_fonciere"]) if pd.notna(row["valeur_fonciere"]) else None,
            "prix_m2": int(row["prix_m2"]) if pd.notna(row.get("prix_m2")) else None,
            "surface": int(row["surface_reelle_bati"]) if pd.notna(row.get("surface_reelle_bati")) else None,
            "type_local": str(row["type_local"]) if pd.notna(row.get("type_local")) else None,
            "date_mutation": row["date_mutation"].strftime("%Y-%m-%d") if pd.notna(row["date_mutation"]) else None,
            "adresse": row.get("adresse"),
            "commune": str(row["nom_commune"]) if pd.notna(row.get("nom_commune")) else None,
            "code_commune": str(row["code_commune"]) if pd.notna(row.get("code_commune")) else None,
            "dept": dept,
            "region": region,
            "annee": int(row["annee"]) if pd.notna(row["annee"]) else None,
        })

    return records


def compute_clusters(records: list[dict]) -> tuple[list, list, list]:
    """Calcule les agrégats commune / dept / region."""
    df = pd.DataFrame(records)
    communes, depts, regions = [], [], []

    # Par commune × type_local
    for (code_commune, type_local), g in df.groupby(["code_commune", "type_local"], dropna=False):
        communes.append({
            "cluster_id": f"{code_commune}_{type_local}",
            "nom": g["commune"].iloc[0] if "commune" in g else None,
            "lat": g["lat"].median(),
            "lon": g["lon"].median(),
            "dept": g["dept"].iloc[0],
            "type_local": type_local if pd.notna(type_local) else None,
            "count": len(g),
            "prix_median": int(g["valeur_fonciere"].median()) if g["valeur_fonciere"].notna().any() else None,
            "prix_m2_median": int(g["prix_m2"].median()) if g["prix_m2"].notna().any() else None,
        })

    # Par dept × type_local
    for (dept, type_local), g in df.groupby(["dept", "type_local"], dropna=False):
        depts.append({
            "cluster_id": f"{dept}_{type_local}",
            "nom": f"Dept {dept}",
            "lat": g["lat"].median(),
            "lon": g["lon"].median(),
            "dept": dept,
            "type_local": type_local if pd.notna(type_local) else None,
            "count": len(g),
            "prix_median": int(g["valeur_fonciere"].median()) if g["valeur_fonciere"].notna().any() else None,
            "prix_m2_median": int(g["prix_m2"].median()) if g["prix_m2"].notna().any() else None,
        })

    # Par region × type_local
    for (region, type_local), g in df.groupby(["region", "type_local"], dropna=False):
        regions.append({
            "cluster_id": f"{region}_{type_local}",
            "nom": region,
            "lat": g["lat"].median(),
            "lon": g["lon"].median(),
            "dept": None,
            "type_local": type_local if pd.notna(type_local) else None,
            "count": len(g),
            "prix_median": int(g["valeur_fonciere"].median()) if g["valeur_fonciere"].notna().any() else None,
            "prix_m2_median": int(g["prix_m2"].median()) if g["prix_m2"].notna().any() else None,
        })

    return communes, depts, regions


def upsert_batch(supabase, table: str, records: list[dict], batch_size=500):
    total = len(records)
    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]
        supabase.table(table).upsert(batch, on_conflict="id" if table == "dvf_points" else "cluster_id").execute()
        print(f"  {table}: {min(i + batch_size, total)}/{total}", end="\r")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dept", nargs="+", default=["75", "93", "95"], help="Départements à importer")
    parser.add_argument("--csv-dir", default="/home/user", help="Dossier des CSV DVF")
    args = parser.parse_args()

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    all_records = []
    for dept in args.dept:
        csv_path = os.path.join(args.csv_dir, f"dvf_{dept}.csv")
        if not os.path.exists(csv_path):
            print(f"  Fichier manquant: {csv_path} — skipped")
            continue
        records = load_dept(dept, csv_path)
        print(f"  Dept {dept}: {len(records):,} transactions")
        all_records.extend(records)

    print(f"\nTotal: {len(all_records):,} transactions → Supabase...")
    upsert_batch(sb, "dvf_points", all_records)

    print("\nCalcul des clusters...")
    communes, depts, regions = compute_clusters(all_records)
    print(f"  {len(communes)} clusters commune, {len(depts)} clusters dept, {len(regions)} clusters region")

    upsert_batch(sb, "dvf_clusters_commune", communes, batch_size=1000)
    upsert_batch(sb, "dvf_clusters_dept", depts, batch_size=1000)
    upsert_batch(sb, "dvf_clusters_region", regions, batch_size=1000)

    print("\n✅ Import terminé!")


if __name__ == "__main__":
    main()
