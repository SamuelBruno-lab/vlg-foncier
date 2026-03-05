export interface DvfCluster {
  cluster_id: number;
  lat: number;
  lon: number;
  count: number;
  prix_median: number;
  prix_m2_median: number;
  dept: string;
  type_local: string | null;
}

export interface DvfPoint {
  id: string;
  lat: number;
  lon: number;
  valeur_fonciere: number;
  prix_m2: number | null;
  surface: number | null;
  type_local: string | null;
  date_mutation: string;
  adresse: string | null;
  commune: string | null;
  dept: string;
  annee: number;
}

export interface DvfFilters {
  dept?: string[];
  annee?: number[];
  type_local?: string[];
  prix_min?: number;
  prix_max?: number;
  zoom?: number;
}
