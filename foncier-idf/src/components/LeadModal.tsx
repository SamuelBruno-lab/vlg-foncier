"use client";

import { useState } from "react";

interface Props {
  onClose: () => void;
}

export default function LeadModal({ onClose }: Props) {
  const [email, setEmail] = useState("");
  const [nom, setNom] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setStatus("loading");
    setErrorMsg("");

    try {
      const res = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, nom }),
      });
      if (!res.ok) {
        const j = await res.json();
        throw new Error(j.error ?? "Erreur serveur");
      }
      setStatus("success");
    } catch (err: unknown) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Erreur inconnue");
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 2000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0,0,0,0.7)",
        padding: 20,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        style={{
          background: "linear-gradient(135deg, #0d0d2b, #12122e)",
          border: "1px solid rgba(168,85,247,0.3)",
          borderRadius: 16,
          padding: "36px 40px",
          maxWidth: 440,
          width: "100%",
          boxShadow: "0 20px 60px rgba(0,0,0,0.8), 0 0 40px rgba(168,85,247,0.1)",
          fontFamily: "Segoe UI, Arial, sans-serif",
          position: "relative",
        }}
      >
        {/* Fermer */}
        <button
          onClick={onClose}
          style={{
            position: "absolute",
            top: 14,
            right: 16,
            background: "none",
            border: "none",
            color: "rgba(255,255,255,0.3)",
            fontSize: 20,
            cursor: "pointer",
            lineHeight: 1,
          }}
        >
          ×
        </button>

        {status === "success" ? (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
            <h2 style={{ color: "#fff", margin: "0 0 12px", fontSize: 22 }}>
              C&apos;est noté !
            </h2>
            <p style={{ color: "rgba(255,255,255,0.55)", fontSize: 15, lineHeight: 1.6 }}>
              Vous recevrez les prochaines analyses immobilières directement dans votre boîte mail.
            </p>
            <button
              onClick={onClose}
              style={{
                marginTop: 24,
                padding: "10px 28px",
                borderRadius: 8,
                border: "none",
                background: "linear-gradient(135deg, #00d4ff, #0099cc)",
                color: "#000",
                fontWeight: 700,
                fontSize: 14,
                cursor: "pointer",
              }}
            >
              Explorer la carte →
            </button>
          </div>
        ) : (
          <>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "rgba(168,85,247,0.12)",
                border: "1px solid rgba(168,85,247,0.3)",
                borderRadius: 99,
                padding: "5px 14px",
                marginBottom: 20,
                fontSize: 11,
                color: "#c084fc",
                letterSpacing: 1.2,
                textTransform: "uppercase",
                fontWeight: 600,
              }}
            >
              Gratuit · Sans engagement
            </div>

            <h2 style={{ margin: "0 0 10px", color: "#fff", fontSize: 22, lineHeight: 1.3 }}>
              Recevez les analyses du marché IDF
            </h2>
            <p style={{ margin: "0 0 24px", color: "rgba(255,255,255,0.5)", fontSize: 14, lineHeight: 1.6 }}>
              Données DVF, zones de prix, tendances par quartier — directement dans votre boîte mail.
            </p>

            <form onSubmit={handleSubmit}>
              <label style={{ display: "block", marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginBottom: 6, letterSpacing: 0.5 }}>
                  Prénom (optionnel)
                </div>
                <input
                  type="text"
                  value={nom}
                  onChange={(e) => setNom(e.target.value)}
                  placeholder="Thomas"
                  style={{
                    width: "100%",
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 8,
                    padding: "10px 14px",
                    color: "#fff",
                    fontSize: 14,
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </label>

              <label style={{ display: "block", marginBottom: 20 }}>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginBottom: 6, letterSpacing: 0.5 }}>
                  Email *
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="vous@exemple.fr"
                  style={{
                    width: "100%",
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 8,
                    padding: "10px 14px",
                    color: "#fff",
                    fontSize: 14,
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </label>

              {errorMsg && (
                <div style={{ color: "#ff6060", fontSize: 12, marginBottom: 12 }}>
                  {errorMsg}
                </div>
              )}

              <button
                type="submit"
                disabled={status === "loading"}
                style={{
                  width: "100%",
                  padding: "13px",
                  borderRadius: 9,
                  border: "none",
                  background: status === "loading"
                    ? "rgba(168,85,247,0.4)"
                    : "linear-gradient(135deg, #a855f7, #7c3aed)",
                  color: "#fff",
                  fontWeight: 700,
                  fontSize: 15,
                  cursor: status === "loading" ? "not-allowed" : "pointer",
                  boxShadow: "0 0 20px rgba(168,85,247,0.3)",
                  transition: "opacity 0.2s",
                }}
              >
                {status === "loading" ? "Enregistrement..." : "Je m'inscris gratuitement →"}
              </button>
            </form>

            <p style={{ margin: "14px 0 0", fontSize: 11, color: "rgba(255,255,255,0.2)", textAlign: "center" }}>
              Pas de spam. Désinscription en 1 clic. Données protégées RGPD.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
