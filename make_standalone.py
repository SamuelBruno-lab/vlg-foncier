"""
Rend les cartes HTML autonomes :
  - Télécharge et embarque toutes les ressources externes (JS, CSS)
  - Génère un index.html de présentation
  - Prépare le dossier prêt pour GitHub Pages
"""
import os, re, base64, shutil
import requests
from pathlib import Path

OUT_DIR = Path("/home/user/vlg_pages")
OUT_DIR.mkdir(exist_ok=True)

MAPS = [
    ("carte_vlg_appartements.html", "🏢 Appartements",    "390 transactions · 15 zones HDBSCAN"),
    ("carte_vlg_maisons.html",      "🏠 Maisons / Pavillons", "69 transactions · 6 zones HDBSCAN"),
    ("carte_vlg_commerces.html",    "🏭 Commerces & Locaux", "51 transactions · 5 zones HDBSCAN"),
]

CACHE = {}

def fetch(url):
    if url in CACHE:
        return CACHE[url]
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        CACHE[url] = r
        print(f"  ✓ {url[:80]}")
        return r
    except Exception as e:
        print(f"  ✗ {url[:80]} → {e}")
        return None

def inline_resources(html: str) -> str:
    # Inline CSS <link>
    def replace_css(m):
        href = m.group(1)
        if href.startswith("http"):
            r = fetch(href)
            if r:
                return f"<style>{r.text}</style>"
        return m.group(0)

    # Inline JS <script src>
    def replace_js(m):
        src = m.group(1)
        if src.startswith("http"):
            r = fetch(src)
            if r:
                return f"<script>{r.text}</script>"
        return m.group(0)

    html = re.sub(
        r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\'][^>]*/?>',
        replace_css, html
    )
    html = re.sub(
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']stylesheet["\'][^>]*/?>',
        replace_css, html
    )
    html = re.sub(
        r'<script[^>]+src=["\']([^"\']+)["\'][^>]*></script>',
        replace_js, html
    )
    return html

# ── Traitement des cartes ──────────────────────────────────────────────────────
print("Inlining resources...")
for filename, _, _ in MAPS:
    src = Path(f"/home/user/{filename}")
    if not src.exists():
        print(f"  SKIP (not found): {filename}")
        continue
    print(f"\n→ {filename}")
    html = src.read_text(encoding="utf-8")
    html = inline_resources(html)
    (OUT_DIR / filename).write_text(html, encoding="utf-8")
    size_mb = (OUT_DIR / filename).stat().st_size / 1024 / 1024
    print(f"  → {size_mb:.1f} MB standalone")

# ── index.html ────────────────────────────────────────────────────────────────
cards_html = ""
for filename, title, desc in MAPS:
    cards_html += f"""
    <a href="{filename}" class="card">
      <div class="card-icon">{title.split()[0]}</div>
      <div class="card-body">
        <div class="card-title">{' '.join(title.split()[1:])}</div>
        <div class="card-desc">{desc}</div>
      </div>
      <div class="card-arrow">→</div>
    </a>"""

index_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Analyse Foncière · Villeneuve-la-Garenne</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: linear-gradient(135deg, #0a0a1e 0%, #0d1b2a 50%, #0a0a1e 100%);
      min-height: 100vh; color: #e8e8f0;
      display: flex; flex-direction: column; align-items: center;
      padding: 60px 20px;
    }}
    .header {{ text-align: center; margin-bottom: 60px; }}
    .header .tag {{
      display: inline-block; background: rgba(0,212,255,0.15);
      color: #00d4ff; border: 1px solid rgba(0,212,255,0.3);
      border-radius: 20px; padding: 4px 16px; font-size: 12px;
      letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px;
    }}
    .header h1 {{
      font-size: clamp(28px, 5vw, 48px); font-weight: 800;
      background: linear-gradient(90deg, #00d4ff, #ffffff, #ff6600);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      background-clip: text; line-height: 1.2; margin-bottom: 16px;
    }}
    .header p {{
      font-size: 16px; color: rgba(255,255,255,0.5); max-width: 520px; margin: 0 auto;
      line-height: 1.6;
    }}
    .stats-bar {{
      display: flex; gap: 40px; justify-content: center;
      margin-bottom: 50px; flex-wrap: wrap;
    }}
    .stat {{ text-align: center; }}
    .stat .val {{ font-size: 32px; font-weight: 800; color: #00d4ff; }}
    .stat .lbl {{ font-size: 11px; color: rgba(255,255,255,.4);
      text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }}
    .cards {{ display: flex; flex-direction: column; gap: 16px; width: 100%; max-width: 600px; }}
    .card {{
      display: flex; align-items: center; gap: 20px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px; padding: 22px 24px;
      text-decoration: none; color: inherit;
      transition: all 0.2s ease; cursor: pointer;
    }}
    .card:hover {{
      background: rgba(0,212,255,0.08);
      border-color: rgba(0,212,255,0.3);
      transform: translateY(-2px);
      box-shadow: 0 8px 32px rgba(0,212,255,0.15);
    }}
    .card-icon {{ font-size: 32px; flex-shrink: 0; }}
    .card-body {{ flex: 1; }}
    .card-title {{ font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 4px; }}
    .card-desc {{ font-size: 13px; color: rgba(255,255,255,0.45); }}
    .card-arrow {{ font-size: 20px; color: rgba(0,212,255,0.5); flex-shrink: 0; }}
    .card:hover .card-arrow {{ color: #00d4ff; }}
    .footer {{
      margin-top: 60px; text-align: center;
      font-size: 11px; color: rgba(255,255,255,0.2); line-height: 1.8;
    }}
    .method-badge {{
      display: inline-flex; align-items: center; gap: 8px;
      background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 8px; padding: 10px 18px; margin-top: 30px; font-size: 13px;
      color: rgba(255,255,255,0.5);
    }}
    .method-badge span {{ color: #00d4ff; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="header">
    <div class="tag">Service Foncier · 92078</div>
    <h1>Analyse Foncière<br>Villeneuve-la-Garenne</h1>
    <p>Cartographie interactive des transactions immobilières<br>
       2020 – 2025 · Source : Demandes de Valeurs Foncières</p>
  </div>

  <div class="stats-bar">
    <div class="stat"><div class="val">510</div><div class="lbl">Transactions</div></div>
    <div class="stat"><div class="val">2020–25</div><div class="lbl">Période</div></div>
    <div class="stat"><div class="val">26</div><div class="lbl">Zones HDBSCAN</div></div>
    <div class="stat"><div class="val">3</div><div class="lbl">Typologies</div></div>
  </div>

  <div class="cards">
    {cards_html}
  </div>

  <div class="method-badge">
    Algorithme de clustering · <span>HDBSCAN</span> · Python · Données DVF open data
  </div>

  <div class="footer">
    © 2026 Samuel Bruno · Service Foncier · Villeneuve-la-Garenne<br>
    Source : data.gouv.fr · Demandes de Valeurs Foncières (DVF)
  </div>
</body>
</html>"""

(OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
print(f"\n✅ index.html créé")

# ── .nojekyll pour GitHub Pages ───────────────────────────────────────────────
(OUT_DIR / ".nojekyll").write_text("")
print("✅ .nojekyll créé")
print(f"\n📁 Dossier prêt : {OUT_DIR}")
print(f"   {list(OUT_DIR.iterdir())}")
