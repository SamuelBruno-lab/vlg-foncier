-- ============================================================
-- datamerry — Zones HDBSCAN par commune × type_local
-- À exécuter dans Supabase SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS dvf_hdbscan_zones (
  id              TEXT PRIMARY KEY,         -- "{code_commune}_{type_local}_{cluster_id}"
  code_commune    TEXT NOT NULL,            -- ex: "92078"
  nom_commune     TEXT,
  dept            TEXT NOT NULL,
  type_local      TEXT NOT NULL,            -- "Appartement", "Maison", "Local..."
  cluster_id      INTEGER NOT NULL,         -- numéro HDBSCAN (0, 1, 2, ...)
  count           INTEGER NOT NULL,
  prix_m2_median  INTEGER,
  prix_m2_p25     INTEGER,
  prix_m2_p75     INTEGER,
  prix_median     BIGINT,
  hull_coords     JSONB,                    -- [[lat, lon], ...] polygone convexe
  centroid_lat    DOUBLE PRECISION,
  centroid_lon    DOUBLE PRECISION,
  annee_min       SMALLINT,
  annee_max       SMALLINT,
  computed_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hdbscan_commune ON dvf_hdbscan_zones (code_commune);
CREATE INDEX IF NOT EXISTS idx_hdbscan_dept    ON dvf_hdbscan_zones (dept);
CREATE INDEX IF NOT EXISTS idx_hdbscan_type    ON dvf_hdbscan_zones (type_local);

ALTER TABLE dvf_hdbscan_zones ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public read dvf_hdbscan_zones"
  ON dvf_hdbscan_zones FOR SELECT USING (true);
