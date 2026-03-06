"use client";

import { useState, useCallback, useMemo } from "react";
import Map, { NavigationControl, ScaleControl } from "react-map-gl/mapbox";
import DeckGL from "@deck.gl/react";
import { ScatterplotLayer } from "@deck.gl/layers";
import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import type { PickingInfo } from "@deck.gl/core";
import type { DvfPoint, DvfCluster, DvfFilters } from "@/types/dvf";
import "mapbox-gl/dist/mapbox-gl.css";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!;

const INITIAL_VIEW = {
  longitude: 2.347,
  latitude: 48.859,
  zoom: 10,
  pitch: 0,
  bearing: 0,
};

// Gradient couleur prix/m²  (bleu→vert→jaune→orange→rouge)
function priceColor(prix_m2: number | null, min: number, max: number): [number, number, number, number] {
  if (!prix_m2) return [150, 150, 150, 180];
  const t = Math.max(0, Math.min(1, (prix_m2 - min) / (max - min)));
  // 0=bleu, 0.25=cyan, 0.5=vert, 0.75=jaune, 1=rouge
  const stops = [
    [0, 100, 255],
    [0, 220, 180],
    [50, 220, 50],
    [255, 200, 0],
    [255, 30, 30],
  ];
  const idx = t * (stops.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, stops.length - 1);
  const f = idx - lo;
  const r = Math.round(stops[lo][0] + f * (stops[hi][0] - stops[lo][0]));
  const g = Math.round(stops[lo][1] + f * (stops[hi][1] - stops[lo][1]));
  const b = Math.round(stops[lo][2] + f * (stops[hi][2] - stops[lo][2]));
  return [r, g, b, 200];
}

interface Props {
  points: DvfPoint[];
  clusters: DvfCluster[];
  mode: "points" | "clusters" | "heatmap";
  filters: DvfFilters;
  isLoading: boolean;
}

export default function DvfMap({ points, clusters, mode, filters, isLoading }: Props) {
  const [hovered, setHovered] = useState<DvfPoint | DvfCluster | null>(null);
  const [cursor, setCursor] = useState("grab");

  const priceRange = useMemo(() => {
    const vals = points.map((p) => p.prix_m2).filter(Boolean) as number[];
    if (vals.length === 0) return [2000, 12000] as [number, number];
    const sorted = [...vals].sort((a, b) => a - b);
    return [sorted[Math.floor(sorted.length * 0.05)], sorted[Math.floor(sorted.length * 0.95)]] as [number, number];
  }, [points]);

  const layers = useMemo(() => {
    if (mode === "heatmap") {
      return [
        new HeatmapLayer<DvfPoint>({
          id: "heatmap",
          data: points,
          getPosition: (d) => [d.lon, d.lat],
          getWeight: (d) => d.prix_m2 ?? 1,
          radiusPixels: 40,
          intensity: 1,
          threshold: 0.1,
          colorRange: [
            [0, 25, 180, 0],
            [0, 150, 255, 200],
            [0, 255, 150, 220],
            [255, 200, 0, 230],
            [255, 60, 0, 240],
            [200, 0, 50, 255],
          ],
        }),
      ];
    }

    if (mode === "clusters") {
      return [
        new ScatterplotLayer<DvfCluster>({
          id: "clusters",
          data: clusters,
          getPosition: (d) => [d.lon, d.lat],
          getRadius: (d) => Math.sqrt(d.count) * 40,
          getFillColor: (d) => priceColor(d.prix_m2_median, priceRange[0], priceRange[1]),
          getLineColor: [255, 255, 255, 80],
          lineWidthMinPixels: 1,
          radiusMinPixels: 6,
          radiusMaxPixels: 60,
          pickable: true,
          onHover: (info: PickingInfo) => {
            setHovered(info.object ?? null);
            setCursor(info.object ? "pointer" : "grab");
          },
        }),
      ];
    }

    // mode === "points"
    return [
      new ScatterplotLayer<DvfPoint>({
        id: "points",
        data: points,
        getPosition: (d) => [d.lon, d.lat],
        getRadius: 12,
        radiusMinPixels: 3,
        radiusMaxPixels: 14,
        getFillColor: (d) => priceColor(d.prix_m2, priceRange[0], priceRange[1]),
        getLineColor: [255, 255, 255, 60],
        lineWidthMinPixels: 0.5,
        pickable: true,
        onHover: (info: PickingInfo) => {
          setHovered(info.object ?? null);
          setCursor(info.object ? "pointer" : "grab");
        },
      }),
    ];
  }, [points, clusters, mode, priceRange]);

  const renderTooltip = useCallback(() => {
    if (!hovered) return null;
    const isCluster = "cluster_id" in hovered;

    return (
      <div
        style={{
          position: "fixed",
          top: 16,
          right: 16,
          background: "rgba(10,10,30,0.95)",
          color: "#e8e8f0",
          borderRadius: 10,
          padding: "14px 18px",
          minWidth: 220,
          border: "1px solid rgba(255,255,255,0.12)",
          fontFamily: "Segoe UI, Arial, sans-serif",
          fontSize: 13,
          zIndex: 1000,
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        }}
      >
        {isCluster ? (
          <>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: "#00d4ff" }}>
              Zone {(hovered as DvfCluster).dept}
            </div>
            <div>{(hovered as DvfCluster).count.toLocaleString("fr-FR")} transactions</div>
            <div style={{ marginTop: 4, color: "#ffdd00", fontWeight: 600 }}>
              {(hovered as DvfCluster).prix_m2_median?.toLocaleString("fr-FR")} €/m² médian
            </div>
            <div style={{ color: "#aaa", marginTop: 4 }}>
              {(hovered as DvfCluster).prix_median?.toLocaleString("fr-FR")} € médian
            </div>
          </>
        ) : (
          <>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>
              {(hovered as DvfPoint).adresse ?? "Adresse inconnue"}
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: "#fff" }}>
              {(hovered as DvfPoint).valeur_fonciere.toLocaleString("fr-FR")} €
            </div>
            <div style={{ color: "#ffdd00", fontWeight: 600, marginTop: 2 }}>
              {(hovered as DvfPoint).prix_m2?.toLocaleString("fr-FR")} €/m²
            </div>
            <div style={{ color: "#aaa", marginTop: 6, fontSize: 12 }}>
              {(hovered as DvfPoint).type_local} · {(hovered as DvfPoint).surface} m² ·{" "}
              {(hovered as DvfPoint).date_mutation?.slice(0, 7)}
            </div>
            <div style={{ color: "#666", fontSize: 11, marginTop: 2 }}>
              {(hovered as DvfPoint).commune} ({(hovered as DvfPoint).dept})
            </div>
          </>
        )}
      </div>
    );
  }, [hovered]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {isLoading && (
        <div
          style={{
            position: "absolute",
            top: 12,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 999,
            background: "rgba(0,212,255,0.15)",
            border: "1px solid #00d4ff",
            color: "#00d4ff",
            padding: "6px 16px",
            borderRadius: 20,
            fontSize: 12,
            fontFamily: "Segoe UI, sans-serif",
          }}
        >
          Chargement...
        </div>
      )}

      <DeckGL
        initialViewState={INITIAL_VIEW}
        controller={{ dragPan: true, scrollZoom: true, doubleClickZoom: true }}
        layers={layers}
        getCursor={() => cursor}
      >
        <Map
          mapboxAccessToken={MAPBOX_TOKEN}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          reuseMaps
        >
          <NavigationControl position="top-right" />
          <ScaleControl position="bottom-right" />
        </Map>
      </DeckGL>

      {renderTooltip()}
    </div>
  );
}
