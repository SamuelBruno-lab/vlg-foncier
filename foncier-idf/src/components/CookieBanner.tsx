"use client";

import { useEffect, useState } from "react";

export default function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Délai 1.5s pour ne pas choquer l'arrivée LinkedIn
    const timer = setTimeout(() => {
      if (!localStorage.getItem("cookie_consent")) {
        setVisible(true);
      }
    }, 1500);
    return () => clearTimeout(timer);
  }, []);

  const accept = () => {
    localStorage.setItem("cookie_consent", "accepted");
    setVisible(false);
  };

  const decline = () => {
    localStorage.setItem("cookie_consent", "declined");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: 16,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 3000,
        width: "min(560px, calc(100vw - 32px))",
        background: "linear-gradient(135deg, rgba(13,13,43,0.98), rgba(18,18,46,0.98))",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 14,
        padding: "16px 20px",
        boxShadow: "0 8px 40px rgba(0,0,0,0.7), 0 0 0 1px rgba(168,85,247,0.08)",
        display: "flex",
        alignItems: "center",
        gap: 16,
        fontFamily: "Segoe UI, Arial, sans-serif",
        animation: "slideUp 0.3s ease",
      }}
    >
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, color: "#e8e8f0", fontWeight: 600, marginBottom: 4 }}>
          🍪 Cookies & confidentialité
        </div>
        <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", lineHeight: 1.55 }}>
          Nous utilisons des cookies analytiques pour améliorer datamerry.com. Aucune donnée vendue à des tiers.
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 7, flexShrink: 0 }}>
        <button
          onClick={accept}
          style={{
            padding: "7px 18px",
            borderRadius: 8,
            border: "none",
            background: "linear-gradient(135deg, #a855f7, #7c3aed)",
            color: "#fff",
            fontWeight: 700,
            fontSize: 12,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          Tout accepter
        </button>
        <button
          onClick={decline}
          style={{
            padding: "7px 18px",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.12)",
            background: "transparent",
            color: "rgba(255,255,255,0.4)",
            fontSize: 12,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          Refuser
        </button>
      </div>

      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateX(-50%) translateY(16px); }
          to   { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      `}</style>
    </div>
  );
}
