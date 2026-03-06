-- ============================================================
-- Migration : enrichissement table leads
-- À exécuter dans Supabase SQL Editor
-- ============================================================

ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS prenom      TEXT,
  ADD COLUMN IF NOT EXISTS societe     TEXT,
  ADD COLUMN IF NOT EXISTS telephone   TEXT,
  ADD COLUMN IF NOT EXISTS consentement BOOLEAN NOT NULL DEFAULT false;

-- Renommer nom → nom_complet pour clarté (optionnel, non bloquant)
-- ALTER TABLE leads RENAME COLUMN nom TO nom_complet;

COMMENT ON COLUMN leads.consentement IS 'Consentement RGPD explicite au moment de l''inscription';
COMMENT ON COLUMN leads.telephone   IS 'Téléphone optionnel (non obligatoire)';
COMMENT ON COLUMN leads.societe     IS 'Nom de la société / agence';
