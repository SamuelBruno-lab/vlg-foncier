-- ============================================================
-- datamerry — Schéma PostgreSQL + PostGIS
-- À exécuter dans Supabase SQL Editor
-- ============================================================

-- Extension PostGIS (déjà activée sur Supabase)
CREATE EXTENSION IF NOT EXISTS postgis;

-- ── Table principale des transactions DVF ───────────────────
CREATE TABLE IF NOT EXISTS dvf_points (
  id                TEXT PRIMARY KEY,
  lat               DOUBLE PRECISION NOT NULL,
  lon               DOUBLE PRECISION NOT NULL,
  geom              GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED,
  valeur_fonciere   BIGINT NOT NULL,
  prix_m2           INTEGER,
  surface           SMALLINT,
  type_local        TEXT,
  date_mutation     DATE NOT NULL,
  adresse           TEXT,
  commune           TEXT,
  code_commune      TEXT,
  dept              TEXT NOT NULL,
  region            TEXT,
  annee             SMALLINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dvf_geom  ON dvf_points USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_dvf_dept  ON dvf_points (dept);
CREATE INDEX IF NOT EXISTS idx_dvf_annee ON dvf_points (annee);
CREATE INDEX IF NOT EXISTS idx_dvf_type  ON dvf_points (type_local);

-- ── Vue clusters par commune (zoom 10-12) ───────────────────
-- Pré-calculé en Python puis inséré, ou via vue matérialisée
CREATE TABLE IF NOT EXISTS dvf_clusters_commune (
  id            SERIAL PRIMARY KEY,
  cluster_id    TEXT NOT NULL,          -- ex: "75056_Appartement"
  nom           TEXT,                   -- nom commune
  lat           DOUBLE PRECISION NOT NULL,
  lon           DOUBLE PRECISION NOT NULL,
  dept          TEXT NOT NULL,
  type_local    TEXT,
  count         INTEGER NOT NULL,
  prix_median   BIGINT,
  prix_m2_median INTEGER,
  annee_min     SMALLINT DEFAULT 2020,
  annee_max     SMALLINT DEFAULT 2025
);

-- ── Vue clusters par département (zoom 7-9) ─────────────────
CREATE TABLE IF NOT EXISTS dvf_clusters_dept (
  id            SERIAL PRIMARY KEY,
  cluster_id    TEXT NOT NULL,          -- ex: "75_Appartement"
  nom           TEXT,                   -- nom département
  lat           DOUBLE PRECISION NOT NULL,
  lon           DOUBLE PRECISION NOT NULL,
  dept          TEXT NOT NULL,
  type_local    TEXT,
  count         INTEGER NOT NULL,
  prix_median   BIGINT,
  prix_m2_median INTEGER,
  annee_min     SMALLINT DEFAULT 2020,
  annee_max     SMALLINT DEFAULT 2025
);

-- ── Vue clusters par région (zoom < 7) ─────────────────────
CREATE TABLE IF NOT EXISTS dvf_clusters_region (
  id            SERIAL PRIMARY KEY,
  cluster_id    TEXT NOT NULL,
  nom           TEXT,
  lat           DOUBLE PRECISION NOT NULL,
  lon           DOUBLE PRECISION NOT NULL,
  dept          TEXT,
  type_local    TEXT,
  count         INTEGER NOT NULL,
  prix_median   BIGINT,
  prix_m2_median INTEGER,
  annee_min     SMALLINT DEFAULT 2020,
  annee_max     SMALLINT DEFAULT 2025
);

-- ── RLS : lecture publique, écriture uniquement service role ─
ALTER TABLE dvf_points          ENABLE ROW LEVEL SECURITY;
ALTER TABLE dvf_clusters_commune ENABLE ROW LEVEL SECURITY;
ALTER TABLE dvf_clusters_dept    ENABLE ROW LEVEL SECURITY;
ALTER TABLE dvf_clusters_region  ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read dvf_points"           ON dvf_points           FOR SELECT USING (true);
CREATE POLICY "public read dvf_clusters_commune" ON dvf_clusters_commune FOR SELECT USING (true);
CREATE POLICY "public read dvf_clusters_dept"    ON dvf_clusters_dept    FOR SELECT USING (true);
CREATE POLICY "public read dvf_clusters_region"  ON dvf_clusters_region  FOR SELECT USING (true);

-- ── Table leads (ferme à emails) ────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT NOT NULL UNIQUE,
  nom         TEXT,
  source      TEXT DEFAULT 'carte_idf',   -- utm source ou page
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  ip_hash     TEXT                         -- hash IP pour déduplication (pas de PII)
);

CREATE INDEX IF NOT EXISTS idx_leads_email      ON leads (email);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads (created_at DESC);

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
-- Lecture réservée au service role (admin uniquement)
-- Insertion publique autorisée via API route (server-side avec service key)
CREATE POLICY "no public read leads" ON leads FOR SELECT USING (false);
