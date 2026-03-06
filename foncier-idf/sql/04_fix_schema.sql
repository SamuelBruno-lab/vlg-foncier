-- Fix 1: surface SMALLINT → INTEGER (SMALLINT max = 32767, certains biens dépassent)
ALTER TABLE dvf_points ALTER COLUMN surface TYPE INTEGER;

-- Fix 2: contraintes UNIQUE sur cluster_id pour l'upsert ON CONFLICT
ALTER TABLE dvf_clusters_commune ADD CONSTRAINT uq_dvf_clusters_commune_cluster_id UNIQUE (cluster_id);
ALTER TABLE dvf_clusters_dept    ADD CONSTRAINT uq_dvf_clusters_dept_cluster_id    UNIQUE (cluster_id);
ALTER TABLE dvf_clusters_region  ADD CONSTRAINT uq_dvf_clusters_region_cluster_id  UNIQUE (cluster_id);
