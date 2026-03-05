import pandas as pd
import numpy as np
import folium
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import LabelEncoder
import json

# ── 1. Chargement des données ───────────────────────────────────────────────
years = [2020, 2021, 2022, 2023, 2024, 2025]
frames = []
for y in years:
    path = f"/home/user/dvf_92078_{y}.csv"
    try:
        df = pd.read_csv(path, low_memory=False)
        df["annee"] = y
        frames.append(df)
    except Exception as e:
        print(f"Erreur {y}: {e}")

data = pd.concat(frames, ignore_index=True)
print(f"Total brut : {len(data)} lignes")

# ── 2. Nettoyage ────────────────────────────────────────────────────────────
data = data.dropna(subset=["latitude", "longitude", "valeur_fonciere"])
data = data[data["valeur_fonciere"] > 0]
data["valeur_fonciere"] = pd.to_numeric(data["valeur_fonciere"], errors="coerce")
data["surface_reelle_bati"] = pd.to_numeric(data["surface_reelle_bati"], errors="coerce")
data["date_mutation"] = pd.to_datetime(data["date_mutation"], errors="coerce")

# Dédoublonnage : même mutation, même adresse
data = data.drop_duplicates(subset=["id_mutation", "id_parcelle"])
print(f"Après nettoyage : {len(data)} transactions")

# ── 3. DBSCAN clustering ─────────────────────────────────────────────────────
# epsilon en radians pour haversine (100 m)
coords = np.radians(data[["latitude", "longitude"]].values)
eps_rad = 100 / 6_371_000  # 100 mètres

db = DBSCAN(eps=eps_rad, min_samples=3, algorithm="ball_tree", metric="haversine")
data["cluster"] = db.fit_predict(coords)

n_clusters = data[data["cluster"] >= 0]["cluster"].nunique()
n_noise = (data["cluster"] == -1).sum()
print(f"Clusters DBSCAN : {n_clusters} zones, {n_noise} points isolés")

# ── 4. Palette de couleurs ───────────────────────────────────────────────────
PALETTE = [
    "#e6194b","#3cb44b","#ffe119","#4363d8","#f58231",
    "#911eb4","#42d4f4","#f032e6","#bfef45","#fabebe",
    "#469990","#e6beff","#9A6324","#800000","#aaffc3",
    "#808000","#ffd8b1","#000075","#a9a9a9","#ff4500",
]

def cluster_color(cid):
    if cid == -1:
        return "#888888"
    return PALETTE[cid % len(PALETTE)]

# ── 5. Création de la carte Folium ───────────────────────────────────────────
center_lat = data["latitude"].mean()
center_lon = data["longitude"].mean()

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=14,
    tiles="CartoDB positron",
)

# Titre
title_html = """
<div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
     z-index: 1000; background: white; padding: 10px 20px; border-radius: 8px;
     box-shadow: 0 2px 8px rgba(0,0,0,0.3); font-family: Arial; text-align:center;">
  <b style="font-size:16px;">Transactions immobilières — Villeneuve-la-Garenne</b><br>
  <span style="font-size:12px; color:#555;">2020–2025 · Clustering DBSCAN (rayon 100 m, min 3 points)</span>
</div>
"""
m.get_root().html.add_child(folium.Element(title_html))

# ── 6. Tracé des points ───────────────────────────────────────────────────────
for _, row in data.iterrows():
    cid = int(row["cluster"])
    color = cluster_color(cid)
    label = f"Zone {cid}" if cid >= 0 else "Isolé"

    # Prix/m²
    if pd.notna(row["surface_reelle_bati"]) and row["surface_reelle_bati"] > 0:
        prix_m2 = f"{row['valeur_fonciere']/row['surface_reelle_bati']:,.0f} €/m²"
        surface = f"{row['surface_reelle_bati']:.0f} m²"
    else:
        prix_m2 = "N/A"
        surface = "N/A"

    adresse = " ".join(filter(pd.notna, [
        str(row.get("adresse_numero", "") or ""),
        str(row.get("adresse_nom_voie", "") or ""),
    ])).strip() or "Adresse inconnue"

    date_str = row["date_mutation"].strftime("%d/%m/%Y") if pd.notna(row["date_mutation"]) else "Date inconnue"
    type_local = row.get("type_local", "Inconnu") or "Inconnu"

    popup_html = f"""
    <div style="font-family:Arial; min-width:200px;">
      <b style="color:{color};">{label}</b><br>
      <hr style="margin:4px 0;">
      <b>{adresse}</b><br>
      <i>{type_local}</i><br>
      <br>
      <table style="font-size:12px; width:100%;">
        <tr><td>Prix</td><td><b>{row['valeur_fonciere']:,.0f} €</b></td></tr>
        <tr><td>Surface</td><td>{surface}</td></tr>
        <tr><td>Prix/m²</td><td>{prix_m2}</td></tr>
        <tr><td>Date</td><td>{date_str}</td></tr>
        <tr><td>Année</td><td>{int(row['annee'])}</td></tr>
      </table>
    </div>
    """

    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=5,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.75,
        weight=1,
        popup=folium.Popup(popup_html, max_width=280),
        tooltip=f"{label} · {row['valeur_fonciere']:,.0f} € · {date_str}",
    ).add_to(m)

# ── 7. Polygones convexes par cluster ─────────────────────────────────────────
from scipy.spatial import ConvexHull

cluster_ids = [c for c in data["cluster"].unique() if c >= 0]
for cid in cluster_ids:
    pts = data[data["cluster"] == cid][["latitude", "longitude"]].values
    if len(pts) < 3:
        continue
    try:
        hull = ConvexHull(pts)
        hull_pts = pts[hull.vertices].tolist()
        hull_pts.append(hull_pts[0])  # fermer le polygone
        color = cluster_color(cid)
        cluster_data = data[data["cluster"] == cid]
        n = len(cluster_data)
        med_prix = cluster_data["valeur_fonciere"].median()
        med_m2 = (
            cluster_data["valeur_fonciere"] / cluster_data["surface_reelle_bati"]
        ).replace([np.inf, -np.inf], np.nan).median()
        med_m2_str = f"{med_m2:,.0f} €/m²" if pd.notna(med_m2) else "N/A"

        zone_popup = f"""
        <div style="font-family:Arial;">
          <b style="color:{color};">Zone {cid}</b><br>
          <hr style="margin:4px 0;">
          {n} transactions<br>
          Prix médian : <b>{med_prix:,.0f} €</b><br>
          Médiane prix/m² : <b>{med_m2_str}</b>
        </div>
        """
        folium.Polygon(
            locations=hull_pts,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.08,
            weight=1.5,
            popup=folium.Popup(zone_popup, max_width=220),
            tooltip=f"Zone {cid} · {n} transactions",
        ).add_to(m)
    except Exception:
        pass

# ── 8. Légende ────────────────────────────────────────────────────────────────
stats = data.groupby("annee").size().to_dict()
stats_html = "".join(f"<tr><td>{y}</td><td>{n}</td></tr>" for y, n in sorted(stats.items()))

legend_html = f"""
<div style="position: fixed; bottom: 20px; right: 10px; z-index: 1000;
     background: white; padding: 12px; border-radius: 8px; font-family: Arial;
     font-size: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); min-width:180px;">
  <b>Résumé</b><br>
  <hr style="margin:4px 0;">
  Total : <b>{len(data)} transactions</b><br>
  Clusters : <b>{n_clusters} zones</b><br>
  Points isolés : <b>{n_noise}</b><br>
  <br>
  <b>Par année</b>
  <table style="width:100%;">{stats_html}</table>
  <br>
  <div style="display:flex; align-items:center; gap:6px;">
    <div style="width:12px;height:12px;border-radius:50%;background:#888;"></div>
    <span>Point isolé</span>
  </div>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# ── 9. Sauvegarde ────────────────────────────────────────────────────────────
output = "/home/user/carte_vlg.html"
m.save(output)
print(f"\nCarte sauvegardée : {output}")
print(f"Ouvrir avec : xdg-open {output}")
