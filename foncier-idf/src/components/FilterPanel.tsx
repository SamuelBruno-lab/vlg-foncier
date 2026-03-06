"use client";

import { useState } from "react";
import type { DvfFilters } from "@/types/dvf";

const DEPTS_IDF = [
  { code: "75", nom: "Paris" },
  { code: "77", nom: "Seine-et-Marne" },
  { code: "78", nom: "Yvelines" },
  { code: "91", nom: "Essonne" },
  { code: "92", nom: "Hauts-de-Seine" },
  { code: "93", nom: "Seine-Saint-Denis" },
  { code: "94", nom: "Val-de-Marne" },
  { code: "95", nom: "Val-d'Oise" },
];

const TYPES = ["Appartement", "Maison", "Local industriel. commercial ou assimilé", "Dépendance"];

interface Props {
  filters: DvfFilters;
  onFiltersChange: (f: DvfFilters) => void;
  mode: "points" | "clusters" | "heatmap";
  onModeChange: (m: "points" | "clusters" | "heatmap") => void;
  totalTx: number;
}

export default function FilterPanel({ filters, onFiltersChange, mode, onModeChange, totalTx }: Props) {
  const [open, setOpen] = useState(true);

  const toggleDept = (code: string) => {
    const current = filters.dept ?? [];
    const next = current.includes(code) ? current.filter((d) => d !== code) : [...current, code];
    onFiltersChange({ ...filters, dept: next.length === 0 ? undefined : next });
  };

  return (
    <div
      style={{
        position: "absolute",
        top: 12,
        left: 12,
        zIndex: 900,
        background: "linear-gradient(135deg, rgba(10,10,30,0.97), rgba(20,20,50,0.97))",
        color: "#e8e8f0",
        borderRadius: 12,
        width: 260,
        border: "1px solid rgba(255,255,255,0.1)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        fontFamily: "Segoe UI, Arial, sans-serif",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "linear-gradient(90deg, #00d4ff22, #ff005522)",
          padding: "12px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ fontWeight: 700, fontSize: 14, color: "#fff" }}>datamerry</div>
          <div style={{ fontSize: 10, color: "rgba(255,255,255,.5)", marginTop: 2 }}>
            {totalTx.toLocaleString("fr-FR")} transactions visibles
          </div>
        </div>
        <button
          onClick={() => setOpen(!open)}
          style={{ background: "none", border: "none", color: "rgba(255,255,255,.5)", cursor: "pointer", fontSize: 16 }}
        >
          {open ? "▲" : "▼"}
        </button>
      </div>

      {open && (
        <div style={{ padding: "14px 16px" }}>
          {/* Mode vue */}
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 1, color: "rgba(255,255,255,.4)", marginBottom: 6 }}>
            Mode
          </div>
          <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
            {(["clusters", "points", "heatmap"] as const).map((m) => (
              <button
                key={m}
                onClick={() => onModeChange(m)}
                style={{
                  flex: 1,
                  padding: "5px 0",
                  borderRadius: 6,
                  border: "1px solid",
                  borderColor: mode === m ? "#00d4ff" : "rgba(255,255,255,0.15)",
                  background: mode === m ? "rgba(0,212,255,0.15)" : "rgba(255,255,255,0.05)",
                  color: mode === m ? "#00d4ff" : "#aaa",
                  cursor: "pointer",
                  fontSize: 11,
                  fontWeight: mode === m ? 700 : 400,
                }}
              >
                {m === "clusters" ? "Zones" : m === "points" ? "Points" : "Heatmap"}
              </button>
            ))}
          </div>

          {/* Départements */}
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 1, color: "rgba(255,255,255,.4)", marginBottom: 6 }}>
            Départements IDF
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 14 }}>
            {DEPTS_IDF.map(({ code, nom }) => {
              const active = !filters.dept || filters.dept.includes(code);
              return (
                <button
                  key={code}
                  onClick={() => toggleDept(code)}
                  title={nom}
                  style={{
                    padding: "3px 8px",
                    borderRadius: 4,
                    border: "1px solid",
                    borderColor: active ? "#00d4ff" : "rgba(255,255,255,0.15)",
                    background: active ? "rgba(0,212,255,0.15)" : "rgba(255,255,255,0.04)",
                    color: active ? "#00d4ff" : "#666",
                    cursor: "pointer",
                    fontSize: 12,
                    fontWeight: active ? 700 : 400,
                  }}
                >
                  {code}
                </button>
              );
            })}
          </div>

          {/* Type de bien */}
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 1, color: "rgba(255,255,255,.4)", marginBottom: 6 }}>
            Type de bien
          </div>
          <select
            value={filters.type_local?.[0] ?? ""}
            onChange={(e) =>
              onFiltersChange({ ...filters, type_local: e.target.value ? [e.target.value] : undefined })
            }
            style={{
              width: "100%",
              background: "rgba(255,255,255,0.07)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "#ccc",
              borderRadius: 6,
              padding: "6px 8px",
              fontSize: 12,
              marginBottom: 14,
            }}
          >
            <option value="">Tous types</option>
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>

          {/* Années */}
          <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: 1, color: "rgba(255,255,255,.4)", marginBottom: 6 }}>
            Période
          </div>
          <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
            {[2020, 2021, 2022, 2023, 2024, 2025].map((y) => {
              const active = !filters.annee || filters.annee.includes(y);
              return (
                <button
                  key={y}
                  onClick={() => {
                    const cur = filters.annee ?? [2020, 2021, 2022, 2023, 2024, 2025];
                    const next = cur.includes(y) ? cur.filter((a) => a !== y) : [...cur, y];
                    onFiltersChange({ ...filters, annee: next.length === 6 ? undefined : next });
                  }}
                  style={{
                    flex: 1,
                    padding: "3px 0",
                    borderRadius: 4,
                    border: "1px solid",
                    borderColor: active ? "#ff6600" : "rgba(255,255,255,0.1)",
                    background: active ? "rgba(255,102,0,0.12)" : "rgba(255,255,255,0.03)",
                    color: active ? "#ff8844" : "#555",
                    cursor: "pointer",
                    fontSize: 10,
                    fontWeight: active ? 700 : 400,
                  }}
                >
                  {String(y).slice(2)}
                </button>
              );
            })}
          </div>

          <div style={{ fontSize: 10, color: "rgba(255,255,255,.25)", textAlign: "center", paddingTop: 8, borderTop: "1px solid rgba(255,255,255,.06)" }}>
            datamerry.fr · Source DVF data.gouv.fr
          </div>
        </div>
      )}
    </div>
  );
}
