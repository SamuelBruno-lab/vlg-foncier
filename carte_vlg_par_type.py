"""
Trois cartes HDBSCAN avec jitter sur les points superposés :
  1. Appartements
  2. Maisons (pavillons)
  3. Commerces / Locaux d'activités / Entrepôts
"""
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap, MiniMap, Fullscreen
import hdbscan
from scipy.spatial import ConvexHull
import branca.colormap as cm
import os

# ── 1. Chargement & nettoyage ─────────────────────────────────────────────────
years = [2020, 2021, 2022, 2023, 2024, 2025]
frames = []
for y in years:
    try:
        df = pd.read_csv(f"/home/user/dvf_92078_{y}.csv", low_memory=False)
        df["annee"] = y
        frames.append(df)
    except Exception as e:
        print(f"Skip {y}: {e}")

raw = pd.concat(frames, ignore_index=True)
raw = raw.dropna(subset=["latitude", "longitude", "valeur_fonciere"])
raw = raw[raw["valeur_fonciere"] > 0]
raw = raw.drop_duplicates(subset=["id_mutation", "id_parcelle"])
# Exclusion des VEFA maisons uniquement : prix total programme promoteur
# (ex: LIDL 11.82M€ classé Maison dans DVF). VEFA appartements/commerces conservées.
raw = raw[~((raw["nature_mutation"] == "Vente en l'état futur d'achèvement") &
            (raw["type_local"] == "Maison"))]
raw["valeur_fonciere"]     = pd.to_numeric(raw["valeur_fonciere"],     errors="coerce")
raw["surface_reelle_bati"] = pd.to_numeric(raw["surface_reelle_bati"], errors="coerce")
raw["surface_terrain"]     = pd.to_numeric(raw["surface_terrain"],     errors="coerce")
raw["date_mutation"]       = pd.to_datetime(raw["date_mutation"],       errors="coerce")
raw["prix_m2"] = np.where(raw["surface_reelle_bati"] > 0,
                          raw["valeur_fonciere"] / raw["surface_reelle_bati"], np.nan)
raw = raw.dropna(subset=["valeur_fonciere"])

# Suppression des outliers DVF aberrants par type (données manifestement erronées)
SEUIL_PRIX_M2 = {"Maison": 9000, "Appartement": 12000,
                 "Local industriel. commercial ou assimilé": 12000}
for tl, seuil in SEUIL_PRIX_M2.items():
    mask = (raw["type_local"] == tl) & (raw["prix_m2"] > seuil)
    n = mask.sum()
    if n:
        print(f"Suppression {n} outliers {tl} > {seuil} €/m²")
    raw = raw[~mask]

# ── 2. Jitter sur les coordonnées dupliquées ──────────────────────────────────
# Décale les points superposés en spirale (rayon ~12 m max)
def apply_jitter(df, radius_deg=0.0001):
    df = df.copy()
    df["lat_j"] = df["latitude"].astype(float)
    df["lon_j"] = df["longitude"].astype(float)
    groups = df.groupby(["latitude", "longitude"])
    rng = np.random.default_rng(42)
    for (lat, lon), idx in groups.groups.items():
        n = len(idx)
        if n == 1:
            continue
        # Disposition en spirale régulière
        angles = np.linspace(0, 2 * np.pi * (1 + n // 8), n, endpoint=False)
        radii  = np.linspace(radius_deg * 0.3, radius_deg, n)
        df.loc[idx, "lat_j"] = lat + radii * np.sin(angles)
        df.loc[idx, "lon_j"] = lon + radii * np.cos(angles)
    return df

# ── 3. Utilitaires ────────────────────────────────────────────────────────────
CLUSTER_COLORS = [
    "#00d4ff","#00ff88","#ff6600","#ff0055","#cc00ff",
    "#ffdd00","#00ffcc","#ff3399","#66ff00","#0099ff",
    "#ff9900","#ff00aa","#00ff44","#aa00ff","#ffcc00",
    "#00ccff","#ff4400","#44ffaa","#ff44cc","#aaff00",
]
YEAR_ICONS = {2020:"🔵",2021:"🟢",2022:"🟡",2023:"🟠",2024:"🔴",2025:"🟣"}

def c_color(cid):
    return CLUSTER_COLORS[cid % len(CLUSTER_COLORS)] if cid >= 0 else "#666666"

extra_css = """
<style>
  .leaflet-popup-content-wrapper {
    border-radius: 8px !important; padding: 0 !important;
    overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.35) !important;
  }
  .leaflet-popup-content { margin: 0 !important; }
  .leaflet-popup-tip { background: #fdfdfd !important; }
  .leaflet-control-layers {
    background: rgba(15,15,35,0.95) !important; color: #ddd !important;
    border: 1px solid rgba(255,255,255,0.15) !important; border-radius: 8px !important;
  }
  .leaflet-control-layers label { color: #ccc !important; }
  .leaflet-control-layers-separator { border-top: 1px solid rgba(255,255,255,0.1) !important; }
</style>
"""
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


# ── 4. Génération d'une carte ─────────────────────────────────────────────────
def build_map(data, title, subtitle, min_cluster_size, out_path,
              cluster_selection_method="eom", min_samples=2):
    if data.empty:
        print(f"Aucune donnée pour {title}, skip.")
        return

    # Jitter
    data = apply_jitter(data)

    # HDBSCAN sur coordonnées originales (pas jittées)
    coords = np.radians(data[["latitude", "longitude"]].values)
    cl = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="haversine",
        cluster_selection_method=cluster_selection_method,
    )
    data = data.copy()
    data["cluster"] = cl.fit_predict(coords)
    n_clusters = int(data[data["cluster"] >= 0]["cluster"].nunique())
    n_noise    = int((data["cluster"] == -1).sum())
    print(f"\n{title} → {len(data)} tx | Clusters: {n_clusters} | Isolés: {n_noise}")

    # Palette prix/m²
    valid = data["prix_m2"].dropna()
    if len(valid) > 0:
        p5, p95 = valid.quantile(0.05), valid.quantile(0.95)
    else:
        p5, p95 = 0, 1
    colormap = cm.LinearColormap(
        colors=["#00d4ff","#00ff88","#ffdd00","#ff6600","#ff0055"],
        vmin=p5, vmax=p95, caption="Prix au m² bâti (€)",
    )
    def price_color(v):
        if pd.isna(v): return "#aaaaaa"
        return colormap(max(p5, min(p95, v)))

    # Stats
    total_tx  = len(data)
    med_prix  = data["valeur_fonciere"].median()
    med_m2    = data["prix_m2"].median()
    prix_by_y = data.groupby("annee")["valeur_fonciere"].median().to_dict()
    m2_by_y   = data.groupby("annee")["prix_m2"].median().to_dict()

    year_rows = ""
    for y in sorted(prix_by_y):
        m2v = m2_by_y.get(y, float("nan"))
        m2s = f"{m2v:,.0f} €/m²" if pd.notna(m2v) and not np.isnan(m2v) else "—"
        year_rows += f"<tr><td>{y}</td><td>{prix_by_y[y]:,.0f} €</td><td>{m2s}</td></tr>"

    cluster_rows = ""
    for cid in sorted(data[data["cluster"] >= 0]["cluster"].unique()):
        sub = data[data["cluster"] == cid]
        m2v = sub["prix_m2"].median()
        m2s = f"{m2v:,.0f}" if pd.notna(m2v) and not np.isnan(m2v) else "—"
        cluster_rows += f"<tr><td>Zone {cid}</td><td>{len(sub)}</td><td>{m2s} €/m²</td></tr>"

    type_counts = data["type_local"].value_counts(dropna=False)
    badge_html = ""
    BADGE_COLORS = {
        "Appartement": ("#00d4ff22","#00d4ff","#00d4ff44","🏢"),
        "Maison":      ("#ff660022","#ff8844","#ff660044","🏠"),
        "Local industriel. commercial ou assimilé": ("#ffdd0022","#ffdd00","#ffdd0044","🏭"),
    }
    for tl, cnt in type_counts.items():
        if pd.isna(tl):
            badge_html += f"<span class='badge' style='background:#ffffff11;color:#aaa;border:1px solid #ffffff22;'>📦 {cnt}</span>"
        else:
            bg, fg, border, icon = BADGE_COLORS.get(tl, ("#ffffff11","#aaa","#ffffff22","•"))
            label = tl if len(tl) < 22 else tl[:20]+"…"
            badge_html += f"<span class='badge' style='background:{bg};color:{fg};border:1px solid {border};'>{icon} {cnt} {label}</span>"

    med_m2_display = f"{med_m2:,.0f}€" if pd.notna(med_m2) else "—"

    # Carte
    center = [data["latitude"].mean(), data["longitude"].mean()]
    m = folium.Map(location=center, zoom_start=14, tiles=None, prefer_canvas=True)
    folium.TileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='&copy; OSM &copy; CARTO', name="Dark (défaut)", max_zoom=19, subdomains="abcd",
    ).add_to(m)
    folium.TileLayer(
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; OSM &copy; CARTO', name="Light", max_zoom=19, subdomains="abcd",
    ).add_to(m)
    Fullscreen(position="topright").add_to(m)
    MiniMap(position="bottomleft", tile_layer="CartoDB dark_matter", zoom_level_offset=-5).add_to(m)

    # Heatmap (intensité = prix/m², cohérent avec la coloration des marqueurs)
    heat_w = data[["latitude","longitude","prix_m2"]].dropna(subset=["prix_m2"]).copy()
    if len(heat_w) > 0:
        p75_h = valid.quantile(0.75)
        vmin_h, vmax_h = p5, p75_h
        heat_w["w"] = (heat_w["prix_m2"].clip(vmin_h, vmax_h) - vmin_h) / (vmax_h - vmin_h + 1)
        hfg = folium.FeatureGroup(name="🌡️ Heatmap (intensité prix/m²)", show=False)
        HeatMap(
            heat_w[["latitude","longitude","w"]].values.tolist(),
            radius=20, blur=15, min_opacity=0.3,
            gradient={0.2:"#00d4ff",0.5:"#ffdd00",0.8:"#ff6600",1.0:"#ff0055"},
        ).add_to(hfg)
        hfg.add_to(m)

    # Polygones HDBSCAN (sur coords originales)
    pfg = folium.FeatureGroup(name="🗺️ Micro-marchés", show=True)
    for cid in sorted(data[data["cluster"] >= 0]["cluster"].unique()):
        pts = data[data["cluster"] == cid][["latitude","longitude"]].values
        if len(pts) < 3:
            continue
        try:
            hull = ConvexHull(pts)
            hull_pts = pts[hull.vertices].tolist()
            hull_pts.append(hull_pts[0])
            color = c_color(cid)
            sub = data[data["cluster"] == cid]
            n, med = len(sub), sub["valeur_fonciere"].median()
            med_m2v = sub["prix_m2"].median()
            med_m2s = f"{med_m2v:,.0f} €/m²" if pd.notna(med_m2v) and not np.isnan(med_m2v) else "—"
            popup_html = f"""
            <div style="font-family:'Segoe UI',Arial,sans-serif;min-width:210px;color:#222;">
              <div style="background:{color};color:#000;padding:8px 12px;border-radius:6px 6px 0 0;font-weight:700;font-size:14px;">Zone {cid}</div>
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
            ).add_to(pfg)
        except Exception:
            pass
    pfg.add_to(m)

    # Points par année (positions jittées)
    for year in years:
        fg = folium.FeatureGroup(name=f"{YEAR_ICONS.get(year,'•')} {year}", show=True)
        subset = data[data["annee"] == year]
        for _, row in subset.iterrows():
            cid   = int(row["cluster"])
            color = price_color(row["prix_m2"])
            zone_label = f"Zone {cid}" if cid >= 0 else "Isolé"
            surface_s  = f"{row['surface_reelle_bati']:.0f} m²" if pd.notna(row["surface_reelle_bati"]) else "—"
            prix_m2_s  = f"{row['prix_m2']:,.0f} €/m²"         if pd.notna(row["prix_m2"])            else "—"
            adresse = " ".join(filter(lambda x: x and str(x) != "nan", [
                str(row.get("adresse_numero","") or ""),
                str(row.get("adresse_nom_voie","") or ""),
            ])).strip() or "Adresse inconnue"
            date_s  = row["date_mutation"].strftime("%d/%m/%Y") if pd.notna(row["date_mutation"]) else "—"
            type_s  = str(row.get("type_local","") or "—")
            pieces  = row.get("nombre_pieces_principales","")
            pieces_s = f"{int(pieces)} pce{'s' if pieces > 1 else ''}" if pd.notna(pieces) and pieces > 0 else ""

            # Badge jitter
            jitter_note = ""
            if abs(row["lat_j"] - row["latitude"]) > 1e-8 or abs(row["lon_j"] - row["longitude"]) > 1e-8:
                jitter_note = "<div style='font-size:10px;color:#f90;margin-top:4px;'>⚠️ Position légèrement décalée (adresse groupée)</div>"

            popup_html = f"""
            <div style="font-family:'Segoe UI',Arial,sans-serif;min-width:220px;color:#222;">
              <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:10px 14px;border-radius:6px 6px 0 0;">
                <div style="font-size:13px;font-weight:700;">{adresse}</div>
                <div style="font-size:11px;opacity:.75;margin-top:2px;">{type_s}{(' · '+pieces_s) if pieces_s else ''}</div>
              </div>
              <div style="padding:12px 14px;background:#fdfdfd;border-radius:0 0 6px 6px;">
                <div style="font-size:22px;font-weight:800;color:#1a1a2e;">{row['valeur_fonciere']:,.0f} <span style="font-size:14px;color:#555;">€</span></div>
                <div style="font-size:12px;color:#666;margin-bottom:8px;">{surface_s} · <span style="color:{color};font-weight:600;">{prix_m2_s}</span></div>
                <hr style="margin:8px 0;border:none;border-top:1px solid #eee;">
                <table style="width:100%;font-size:12px;color:#555;">
                  <tr><td>Date</td><td style="text-align:right;font-weight:600;color:#333;">{date_s}</td></tr>
                  <tr><td>Cluster</td><td style="text-align:right;font-weight:600;color:{color};">{zone_label}</td></tr>
                </table>
                {jitter_note}
              </div>
            </div>"""

            folium.CircleMarker(
                location=[row["lat_j"], row["lon_j"]],
                radius=6, color="#ffffff22", fill=True,
                fill_color=color, fill_opacity=0.85, weight=0.5,
                popup=folium.Popup(popup_html, max_width=270),
                tooltip=(
                    f"<span style='font-size:12px;'>"
                    f"<b>{row['valeur_fonciere']:,.0f} €</b> · {prix_m2_s} · {date_s}"
                    f"</span>"
                ),
            ).add_to(fg)
        fg.add_to(m)

    colormap.add_to(m)
    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    # Dashboard
    dashboard = f"""
<style>
  #vlg-dashboard {{
    position:fixed;top:10px;left:10px;z-index:9999;
    background:linear-gradient(135deg,rgba(10,10,30,0.97),rgba(20,20,50,0.97));
    color:#e8e8f0;font-family:'Segoe UI',Arial,sans-serif;
    border-radius:12px;padding:0;width:300px;
    box-shadow:0 8px 32px rgba(0,0,0,0.6);
    border:1px solid rgba(255,255,255,0.1);overflow:hidden;
  }}
  #vlg-header {{
    background:linear-gradient(90deg,#00d4ff22,#ff005522);
    padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.1);
  }}
  #vlg-header h2 {{margin:0;font-size:15px;font-weight:700;color:#fff;letter-spacing:.5px;}}
  #vlg-header p  {{margin:4px 0 0;font-size:11px;color:rgba(255,255,255,.55);}}
  #vlg-body {{padding:14px 18px;}}
  .kpi-grid {{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;}}
  .kpi {{background:rgba(255,255,255,0.06);border-radius:8px;padding:10px;text-align:center;border:1px solid rgba(255,255,255,0.08);}}
  .kpi .val {{font-size:18px;font-weight:800;color:#00d4ff;line-height:1.1;}}
  .kpi .lbl {{font-size:10px;color:rgba(255,255,255,.5);margin-top:3px;text-transform:uppercase;letter-spacing:.5px;}}
  .section-title {{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,.4);margin:12px 0 6px;}}
  .year-table {{width:100%;border-collapse:collapse;font-size:12px;}}
  .year-table th {{color:rgba(255,255,255,.4);font-weight:600;text-align:left;padding:3px 0;font-size:10px;text-transform:uppercase;}}
  .year-table td {{padding:4px 0;border-bottom:1px solid rgba(255,255,255,.05);color:#ccc;}}
  .year-table td:not(:first-child) {{text-align:right;color:#fff;}}
  .badge {{display:inline-block;border-radius:4px;padding:2px 7px;font-size:11px;font-weight:700;margin:2px;}}
  #vlg-toggle {{position:absolute;top:8px;right:12px;cursor:pointer;color:rgba(255,255,255,.5);font-size:18px;user-select:none;}}
  #vlg-toggle:hover {{color:#fff;}}
</style>
<div id="vlg-dashboard">
  <div id="vlg-header">
    <span id="vlg-toggle" onclick="
      var b=document.getElementById('vlg-body');
      var t=document.getElementById('vlg-toggle');
      if(b.style.display==='none'){{b.style.display='block';t.textContent='▲'}}
      else{{b.style.display='none';t.textContent='▼'}}
    ">▲</span>
    <h2>{title}</h2>
    <p>{subtitle}</p>
  </div>
  <div id="vlg-body">
    <div class="kpi-grid">
      <div class="kpi"><div class="val">{total_tx:,}</div><div class="lbl">Transactions</div></div>
      <div class="kpi"><div class="val">{n_clusters}</div><div class="lbl">Micro-marchés</div></div>
      <div class="kpi"><div class="val">{med_prix/1000:.0f}k€</div><div class="lbl">Prix médian</div></div>
      <div class="kpi"><div class="val">{med_m2_display}</div><div class="lbl">Médiane/m²</div></div>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">{badge_html}</div>
    <div class="section-title">Évolution annuelle</div>
    <table class="year-table">
      <tr><th>Année</th><th>Prix médian</th><th>€/m² médian</th></tr>
      {year_rows}
    </table>
    <div class="section-title" style="margin-top:14px;">Top zones</div>
    <table class="year-table">
      <tr><th>Zone</th><th>Tx</th><th>€/m²</th></tr>
      {cluster_rows if cluster_rows else '<tr><td colspan="3" style="color:#888;text-align:center;">Aucun cluster</td></tr>'}
    </table>
    <div style="margin-top:14px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08);
      font-size:10px;color:rgba(255,255,255,.3);text-align:center;">
      Source : DVF · data.gouv.fr · micro-marchés min_cluster_size={min_cluster_size}
    </div>
  </div>
</div>
"""
    m.get_root().html.add_child(folium.Element(dashboard))
    m.save(out_path)

    with open(out_path) as f:
        html = f.read()
    html = html.replace("</head>", extra_css + copyright_css + "</head>")
    html = html.replace("</body>", copyright_div + "\n</body>")
    with open(out_path, "w") as f:
        f.write(html)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"✅ {out_path} ({size_mb:.1f} MB)")


# ── 5. Génération des trois cartes ────────────────────────────────────────────
build_map(
    data=raw[raw["type_local"] == "Appartement"].copy(),
    title="Appartements",
    subtitle="Villeneuve-la-Garenne · 2020–2025",
    min_cluster_size=31,   # ≈8% × 386 tx → 6 zones
    min_samples=3,
    cluster_selection_method="eom",
    out_path="/home/user/carte_vlg_appartements.html",
)

build_map(
    data=raw[raw["type_local"] == "Maison"].copy(),
    title="Maisons / Pavillons",
    subtitle="Villeneuve-la-Garenne · 2020–2025",
    min_cluster_size=6,    # leaf : distingue Sorbiers vs Bouleaux Blancs (~150m)
    min_samples=2,
    cluster_selection_method="leaf",
    out_path="/home/user/carte_vlg_maisons.html",
)

build_map(
    data=raw[raw["type_local"] == "Local industriel. commercial ou assimilé"].copy(),
    title="Commerces / Locaux d'activités / Entrepôts",
    subtitle="Villeneuve-la-Garenne · 2020–2025",
    min_cluster_size=5,    # ≈8% × 45 tx, plancher 5
    min_samples=2,
    cluster_selection_method="eom",
    out_path="/home/user/carte_vlg_commerces.html",
)
