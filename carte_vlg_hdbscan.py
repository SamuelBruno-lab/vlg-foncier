"""
Carte premium : Transactions immobilières — Villeneuve-la-Garenne
Dark theme · HDBSCAN clusters · Heatmap · Filtres par année · Stats dashboard
"""
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MiniMap, Fullscreen
import hdbscan
from scipy.spatial import ConvexHull
import branca.colormap as cm

# ── 1. Données ───────────────────────────────────────────────────────────────
years = [2020, 2021, 2022, 2023, 2024, 2025]
frames = []
for y in years:
    try:
        df = pd.read_csv(f"/home/user/dvf_92078_{y}.csv", low_memory=False)
        df["annee"] = y
        frames.append(df)
    except Exception as e:
        print(f"Skip {y}: {e}")

data = pd.concat(frames, ignore_index=True)
data = data.dropna(subset=["latitude", "longitude", "valeur_fonciere"])
data = data[data["valeur_fonciere"] > 0]
data = data.drop_duplicates(subset=["id_mutation", "id_parcelle"])
data["valeur_fonciere"] = pd.to_numeric(data["valeur_fonciere"], errors="coerce")
data["surface_reelle_bati"] = pd.to_numeric(data["surface_reelle_bati"], errors="coerce")
data["date_mutation"] = pd.to_datetime(data["date_mutation"], errors="coerce")
data["prix_m2"] = np.where(
    data["surface_reelle_bati"] > 0,
    data["valeur_fonciere"] / data["surface_reelle_bati"],
    np.nan,
)
data = data.dropna(subset=["valeur_fonciere"])
print(f"Transactions : {len(data)}")

# ── 2. HDBSCAN ───────────────────────────────────────────────────────────────
# Conversion en radians pour haversine
coords = np.radians(data[["latitude", "longitude"]].values)

clusterer = hdbscan.HDBSCAN(
    min_cluster_size=10,   # taille minimale d'un cluster
    min_samples=3,         # robustesse au bruit
    metric="haversine",
    cluster_selection_method="eom",  # Excess of Mass : clusters plus compacts
)
data["cluster"] = clusterer.fit_predict(coords)

n_clusters = int(data[data["cluster"] >= 0]["cluster"].nunique())
n_noise    = int((data["cluster"] == -1).sum())
print(f"Clusters HDBSCAN: {n_clusters}, Isolés: {n_noise}")

# ── 3. Couleur par prix/m² (gradient) ───────────────────────────────────────
p5  = data["prix_m2"].quantile(0.05)
p95 = data["prix_m2"].quantile(0.95)
colormap = cm.LinearColormap(
    colors=["#00d4ff", "#00ff88", "#ffdd00", "#ff6600", "#ff0055"],
    vmin=p5, vmax=p95,
    caption="Prix au m² (€)",
)

def price_color(prix_m2):
    if pd.isna(prix_m2):
        return "#aaaaaa"
    clamped = max(p5, min(p95, prix_m2))
    return colormap(clamped)

# ── 4. Stats globales ────────────────────────────────────────────────────────
total_tx     = len(data)
total_vol    = data["valeur_fonciere"].sum()
med_prix     = data["valeur_fonciere"].median()
med_m2       = data["prix_m2"].median()
n_apparts    = (data["type_local"] == "Appartement").sum()
n_maisons    = (data["type_local"] == "Maison").sum()
prix_by_year = data.groupby("annee")["valeur_fonciere"].median().to_dict()
m2_by_year   = data.groupby("annee")["prix_m2"].median().to_dict()

year_rows = ""
for y in sorted(prix_by_year):
    m2v = m2_by_year.get(y, float("nan"))
    m2s = f"{m2v:,.0f} €/m²" if not np.isnan(m2v) else "—"
    year_rows += f"<tr><td>{y}</td><td>{prix_by_year[y]:,.0f} €</td><td>{m2s}</td></tr>"

cluster_rows = ""
for cid in sorted(data[data["cluster"] >= 0]["cluster"].unique()):
    sub = data[data["cluster"] == cid]
    m2v = sub["prix_m2"].median()
    m2s = f"{m2v:,.0f}" if not np.isnan(m2v) else "—"
    cluster_rows += f"<tr><td>Zone {cid}</td><td>{len(sub)}</td><td>{m2s} €/m²</td></tr>"

# ── 5. Carte ─────────────────────────────────────────────────────────────────
center = [data["latitude"].mean(), data["longitude"].mean()]
m = folium.Map(
    location=center,
    zoom_start=14,
    tiles=None,
    prefer_canvas=True,
)

# Fonds de carte
folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attr='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    name="Dark (défaut)",
    max_zoom=19,
    subdomains="abcd",
).add_to(m)
folium.TileLayer(
    tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attr='&copy; OSM &copy; CARTO',
    name="Light",
    max_zoom=19,
    subdomains="abcd",
).add_to(m)

# Plugins
Fullscreen(position="topright").add_to(m)
MiniMap(position="bottomleft", tile_layer="CartoDB dark_matter", zoom_level_offset=-5).add_to(m)

# ── 6. Heatmap layer ─────────────────────────────────────────────────────────
heat_data = data[["latitude", "longitude", "prix_m2"]].dropna(subset=["prix_m2"]).copy()
vmin_h = heat_data["prix_m2"].min()
vmax_h = heat_data["prix_m2"].max()
heat_data["w"] = (heat_data["prix_m2"] - vmin_h) / (vmax_h - vmin_h + 1)
heatmap_fg = folium.FeatureGroup(name="🌡️ Heatmap (intensité prix/m²)", show=False)
HeatMap(
    data=heat_data[["latitude", "longitude", "w"]].values.tolist(),
    radius=20, blur=15, min_opacity=0.3,
    gradient={0.2: "#00d4ff", 0.5: "#ffdd00", 0.8: "#ff6600", 1.0: "#ff0055"},
).add_to(heatmap_fg)
heatmap_fg.add_to(m)

# ── 7. Polygones HDBSCAN ─────────────────────────────────────────────────────
CLUSTER_COLORS = [
    "#00d4ff","#00ff88","#ff6600","#ff0055","#cc00ff",
    "#ffdd00","#00ffcc","#ff3399","#66ff00","#0099ff",
    "#ff9900","#ff00aa","#00ff44","#aa00ff","#ffcc00",
    "#00ccff","#ff4400","#44ffaa","#ff44cc","#aaff00",
]

def c_color(cid):
    return CLUSTER_COLORS[cid % len(CLUSTER_COLORS)] if cid >= 0 else "#666666"

poly_fg = folium.FeatureGroup(name="🗺️ Zones HDBSCAN", show=True)
for cid in sorted(data[data["cluster"] >= 0]["cluster"].unique()):
    pts = data[data["cluster"] == cid][["latitude", "longitude"]].values
    if len(pts) < 3:
        continue
    try:
        hull = ConvexHull(pts)
        hull_pts = pts[hull.vertices].tolist()
        hull_pts.append(hull_pts[0])
        color = c_color(cid)
        sub = data[data["cluster"] == cid]
        n = len(sub)
        med = sub["valeur_fonciere"].median()
        med_m2v = sub["prix_m2"].median()
        med_m2s = f"{med_m2v:,.0f} €/m²" if not np.isnan(med_m2v) else "—"
        popup_html = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif; min-width:210px; color:#222;">
          <div style="background:{color};color:#000;padding:8px 12px;border-radius:6px 6px 0 0;font-weight:700;font-size:14px;">
            Zone {cid}
          </div>
          <div style="padding:10px 12px;background:#f9f9f9;border-radius:0 0 6px 6px;">
            <table style="width:100%;font-size:13px;border-collapse:collapse;">
              <tr><td style="color:#666;padding:3px 0;">Transactions</td><td style="font-weight:600;text-align:right;">{n}</td></tr>
              <tr><td style="color:#666;padding:3px 0;">Prix médian</td><td style="font-weight:600;text-align:right;">{med:,.0f} €</td></tr>
              <tr><td style="color:#666;padding:3px 0;">Prix/m² médian</td><td style="font-weight:600;text-align:right;">{med_m2s}</td></tr>
            </table>
          </div>
        </div>"""
        folium.Polygon(
            locations=hull_pts, color=color,
            fill=True, fill_color=color, fill_opacity=0.10, weight=2,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"<b style='color:{color}'>Zone {cid}</b> · {n} tx · {med:,.0f} €",
        ).add_to(poly_fg)
    except Exception:
        pass
poly_fg.add_to(m)

# ── 8. Points par année ───────────────────────────────────────────────────────
YEAR_ICONS = {2020:"🔵",2021:"🟢",2022:"🟡",2023:"🟠",2024:"🔴",2025:"🟣"}

for year in years:
    fg = folium.FeatureGroup(name=f"{YEAR_ICONS.get(year,'•')} {year}", show=True)
    sub_year = data[data["annee"] == year]
    for _, row in sub_year.iterrows():
        cid = int(row["cluster"])
        color = price_color(row["prix_m2"])
        zone_label = f"Zone {cid}" if cid >= 0 else "Isolé"

        surface_s = f"{row['surface_reelle_bati']:.0f} m²" if pd.notna(row["surface_reelle_bati"]) else "—"
        prix_m2_s = f"{row['prix_m2']:,.0f} €/m²" if pd.notna(row["prix_m2"]) else "—"
        adresse = " ".join(filter(lambda x: x and str(x) != "nan", [
            str(row.get("adresse_numero","") or ""),
            str(row.get("adresse_nom_voie","") or ""),
        ])).strip() or "Adresse inconnue"
        date_s = row["date_mutation"].strftime("%d/%m/%Y") if pd.notna(row["date_mutation"]) else "—"
        type_s = str(row.get("type_local","") or "—")
        pieces = row.get("nombre_pieces_principales","")
        pieces_s = f"{int(pieces)} pce{'s' if pieces > 1 else ''}" if pd.notna(pieces) and pieces > 0 else ""

        popup_html = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif; min-width:220px; color:#222;">
          <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:10px 14px;border-radius:6px 6px 0 0;">
            <div style="font-size:13px;font-weight:700;">{adresse}</div>
            <div style="font-size:11px;opacity:.75;margin-top:2px;">{type_s} {('· '+pieces_s) if pieces_s else ''}</div>
          </div>
          <div style="padding:12px 14px;background:#fdfdfd;border-radius:0 0 6px 6px;">
            <div style="font-size:22px;font-weight:800;color:#1a1a2e;">{row['valeur_fonciere']:,.0f} <span style="font-size:14px;color:#555;">€</span></div>
            <div style="font-size:12px;color:#666;margin-bottom:8px;">{surface_s} · <span style="color:{color};font-weight:600;">{prix_m2_s}</span></div>
            <hr style="margin:8px 0;border:none;border-top:1px solid #eee;">
            <table style="width:100%;font-size:12px;color:#555;">
              <tr><td>Date</td><td style="text-align:right;font-weight:600;color:#333;">{date_s}</td></tr>
              <tr><td>Cluster</td><td style="text-align:right;font-weight:600;color:{color};">{zone_label}</td></tr>
            </table>
          </div>
        </div>"""

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=6,
            color="#ffffff22",
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=0.5,
            popup=folium.Popup(popup_html, max_width=270),
            tooltip=(
                f"<span style='font-size:12px;'>"
                f"<b>{row['valeur_fonciere']:,.0f} €</b> · {prix_m2_s} · {date_s}"
                f"</span>"
            ),
        ).add_to(fg)
    fg.add_to(m)

# ── 9. Colormap legend ────────────────────────────────────────────────────────
colormap.caption = "Prix au m² (€)"
colormap.add_to(m)

# ── 10. Contrôle des couches ──────────────────────────────────────────────────
folium.LayerControl(collapsed=False, position="topright").add_to(m)

# ── 11. Dashboard HTML ────────────────────────────────────────────────────────
dashboard = f"""
<style>
  #vlg-dashboard {{
    position: fixed; top: 10px; left: 10px; z-index: 9999;
    background: linear-gradient(135deg, rgba(10,10,30,0.97), rgba(20,20,50,0.97));
    color: #e8e8f0; font-family: 'Segoe UI', Arial, sans-serif;
    border-radius: 12px; padding: 0; width: 300px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    border: 1px solid rgba(255,255,255,0.1);
    overflow: hidden;
  }}
  #vlg-header {{
    background: linear-gradient(90deg, #00d4ff22, #ff005522);
    padding: 14px 18px; border-bottom: 1px solid rgba(255,255,255,0.1);
  }}
  #vlg-header h2 {{
    margin: 0; font-size: 15px; font-weight: 700; color: #fff; letter-spacing: .5px;
  }}
  #vlg-header p {{
    margin: 4px 0 0; font-size: 11px; color: rgba(255,255,255,.55);
  }}
  #vlg-body {{ padding: 14px 18px; }}
  .kpi-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px;
  }}
  .kpi {{
    background: rgba(255,255,255,0.06); border-radius: 8px;
    padding: 10px; text-align: center;
    border: 1px solid rgba(255,255,255,0.08);
  }}
  .kpi .val {{
    font-size: 18px; font-weight: 800; color: #00d4ff; line-height: 1.1;
  }}
  .kpi .lbl {{
    font-size: 10px; color: rgba(255,255,255,.5); margin-top: 3px; text-transform:uppercase; letter-spacing:.5px;
  }}
  .section-title {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
    color: rgba(255,255,255,.4); margin: 12px 0 6px;
  }}
  .year-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .year-table th {{ color: rgba(255,255,255,.4); font-weight:600; text-align:left; padding: 3px 0; font-size:10px; text-transform:uppercase; }}
  .year-table td {{ padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,.05); color: #ccc; }}
  .year-table td:not(:first-child) {{ text-align: right; color: #fff; }}
  .badge {{
    display: inline-block; border-radius: 4px; padding: 2px 7px;
    font-size: 11px; font-weight: 700; margin: 2px;
  }}
  #vlg-toggle {{
    position: absolute; top: 8px; right: 12px; cursor: pointer;
    color: rgba(255,255,255,.5); font-size: 18px; user-select:none;
  }}
  #vlg-toggle:hover {{ color: #fff; }}
</style>

<div id="vlg-dashboard">
  <div id="vlg-header">
    <span id="vlg-toggle" onclick="
      var b=document.getElementById('vlg-body');
      var t=document.getElementById('vlg-toggle');
      if(b.style.display==='none'){{b.style.display='block';t.textContent='▲'}}
      else{{b.style.display='none';t.textContent='▼'}}
    ">▲</span>
    <h2>Marché Immobilier</h2>
    <p>Villeneuve-la-Garenne · 2020–2025</p>
  </div>
  <div id="vlg-body">
    <div class="kpi-grid">
      <div class="kpi">
        <div class="val">{total_tx:,}</div>
        <div class="lbl">Transactions</div>
      </div>
      <div class="kpi">
        <div class="val">{n_clusters}</div>
        <div class="lbl">Zones HDBSCAN</div>
      </div>
      <div class="kpi">
        <div class="val">{med_prix/1000:.0f}k€</div>
        <div class="lbl">Prix médian</div>
      </div>
      <div class="kpi">
        <div class="val">{med_m2:,.0f}€</div>
        <div class="lbl">Médiane/m²</div>
      </div>
    </div>

    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">
      <span class="badge" style="background:#00d4ff22;color:#00d4ff;border:1px solid #00d4ff44;">🏢 {n_apparts} appts</span>
      <span class="badge" style="background:#ff660022;color:#ff8844;border:1px solid #ff660044;">🏠 {n_maisons} maisons</span>
    </div>

    <div class="section-title">Évolution annuelle</div>
    <table class="year-table">
      <tr>
        <th>Année</th><th>Prix médian</th><th>€/m² médian</th>
      </tr>
      {year_rows}
    </table>

    <div class="section-title" style="margin-top:14px;">Top zones</div>
    <table class="year-table">
      <tr><th>Zone</th><th>Tx</th><th>€/m²</th></tr>
      {cluster_rows}
    </table>

    <div style="margin-top:14px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08);
      font-size:10px;color:rgba(255,255,255,.3);text-align:center;">
      Source : DVF · data.gouv.fr · HDBSCAN min_cluster_size=10
    </div>
  </div>
</div>
"""

m.get_root().html.add_child(folium.Element(dashboard))

# ── 12. Save ──────────────────────────────────────────────────────────────────
out = "/home/user/carte_vlg_hdbscan.html"
m.save(out)

with open(out, "r") as f:
    html = f.read()

extra_css = """
<style>
  .leaflet-popup-content-wrapper {
    border-radius: 8px !important;
    padding: 0 !important;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35) !important;
  }
  .leaflet-popup-content { margin: 0 !important; }
  .leaflet-popup-tip { background: #fdfdfd !important; }
  .leaflet-control-layers {
    background: rgba(15,15,35,0.95) !important;
    color: #ddd !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 8px !important;
  }
  .leaflet-control-layers label { color: #ccc !important; }
  .leaflet-control-layers-separator { border-top: 1px solid rgba(255,255,255,0.1) !important; }
</style>
"""
html = html.replace("</head>", extra_css + "</head>")

# Copyright
copyright_css = """
<style>
#copyright-banner {
    position: fixed; bottom: 8px; left: 50%; transform: translateX(-50%);
    z-index: 9999; background: rgba(10,10,20,0.75); color: rgba(255,255,255,0.7);
    font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px;
    padding: 4px 12px; border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(4px);
    pointer-events: none; letter-spacing: 0.3px;
}
</style>
"""
copyright_div = '<div id="copyright-banner">© 2026 Samuel Bruno — Tous droits réservés</div>'
html = html.replace("</head>", copyright_css + "</head>")
html = html.replace("</body>", copyright_div + "\n</body>")

with open(out, "w") as f:
    f.write(html)

print(f"\n✅ Carte HDBSCAN : {out}")
import os
size_mb = os.path.getsize(out) / 1024 / 1024
print(f"   Taille : {size_mb:.1f} MB")
