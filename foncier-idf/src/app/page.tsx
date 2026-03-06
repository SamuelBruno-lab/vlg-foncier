"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import FilterPanel from "@/components/FilterPanel";
import type { DvfFilters, DvfPoint, DvfCluster } from "@/types/dvf";

// DvfMap importé dynamiquement (WebGL, no SSR)
const DvfMap = dynamic(() => import("@/components/DvfMap"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "#0a0a1e",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#00d4ff",
        fontFamily: "Segoe UI, sans-serif",
        fontSize: 14,
      }}
    >
      Initialisation de la carte...
    </div>
  ),
});

export default function HomePage() {
  const [filters, setFilters] = useState<DvfFilters>({});
  const [mode, setMode] = useState<"points" | "clusters" | "heatmap">("clusters");
  const [points, setPoints] = useState<DvfPoint[]>([]);
  const [clusters, setClusters] = useState<DvfCluster[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [zoom] = useState(10);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.dept?.length) params.set("dept", filters.dept.join(","));
      if (filters.type_local?.length) params.set("type_local", filters.type_local[0]);
      if (filters.annee?.length) {
        params.set("annee_min", String(Math.min(...filters.annee)));
        params.set("annee_max", String(Math.max(...filters.annee)));
      }
      params.set("zoom", String(zoom));

      const res = await fetch(`/api/dvf/clusters?${params}`);
      const json = await res.json();

      if (json.mode === "points") {
        setPoints(json.data ?? []);
        setClusters([]);
      } else {
        setClusters(json.data ?? []);
        setPoints([]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }, [filters, zoom]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalTx =
    mode === "points"
      ? points.length
      : clusters.reduce((s, c) => s + c.count, 0);

  return (
    <div style={{ width: "100vw", height: "100vh", position: "relative", background: "#0a0a1e" }}>
      <DvfMap
        points={points}
        clusters={clusters}
        mode={mode}
        filters={filters}
        isLoading={isLoading}
      />
      <FilterPanel
        filters={filters}
        onFiltersChange={setFilters}
        mode={mode}
        onModeChange={setMode}
        totalTx={totalTx}
      />
    </div>
  );
}
