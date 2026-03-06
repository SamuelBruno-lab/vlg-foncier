"use client";

import { useState } from "react";

interface Props {
  onClose: () => void;
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 8,
  padding: "10px 14px",
  color: "#fff",
  fontSize: 14,
  outline: "none",
  boxSizing: "border-box",
  fontFamily: "Segoe UI, Arial, sans-serif",
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  color: "rgba(255,255,255,0.4)",
  marginBottom: 5,
  letterSpacing: 0.5,
  display: "block",
};

export default function LeadModal({ onClose }: Props) {
  const [form, setForm] = useState({
    prenom: "",
    nom: "",
    societe: "",
    email: "",
    telephone: "",
    consentement: false,
  });
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.consentement) {
      setErrorMsg("Veuillez accepter les conditions pour continuer.");
      return;
    }
    setStatus("loading");
    setErrorMsg("");
    try {
      const res = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email,
          nom: `${form.prenom} ${form.nom}`.trim(),
          prenom: form.prenom,
          nom_famille: form.nom,
          societe: form.societe,
          telephone: form.telephone,
          consentement: form.consentement,
        }),
      });
      if (!res.ok) {
        const j = await res.json();
        throw new Error(j.error ?? "Erreur serveur");
      }
      setStatus("success");
      // Marquer le consentement cookies en localStorage
      if (typeof window !== "undefined") {
        localStorage.setItem("cookie_consent", "accepted");
      }
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
        background: "rgba(0,0,0,0.75)",
        padding: "16px",
        backdropFilter: "blur(4px)",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        style={{
          background: "linear-gradient(145deg, #0d0d2b, #13132e)",
          border: "1px solid rgba(168,85,247,0.3)",
          borderRadius: 18,
          padding: "32px 36px",
          maxWidth: 480,
          width: "100%",
          boxShadow: "0 24px 80px rgba(0,0,0,0.85), 0 0 60px rgba(168,85,247,0.08)",
          fontFamily: "Segoe UI, Arial, sans-serif",
          position: "relative",
          maxHeight: "95vh",
          overflowY: "auto",
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: "absolute",
            top: 14,
            right: 16,
            background: "none",
            border: "none",
            color: "rgba(255,255,255,0.3)",
            fontSize: 22,
            cursor: "pointer",
            lineHeight: 1,
          }}
        >
          ×
        </button>

        {status === "success" ? (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{ fontSize: 52, marginBottom: 16 }}>🎉</div>
            <h2 style={{ color: "#fff", margin: "0 0 12px", fontSize: 22 }}>
              Bienvenue {form.prenom} !
            </h2>
            <p style={{ color: "rgba(255,255,255,0.55)", fontSize: 15, lineHeight: 1.65 }}>
              Vous serez parmi les premiers à découvrir les nouvelles fonctionnalités et analyses de datamerry.com.
            </p>
            <button
              onClick={onClose}
              style={{
                marginTop: 24,
                padding: "11px 30px",
                borderRadius: 9,
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
            {/* Badge */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                background: "rgba(168,85,247,0.12)",
                border: "1px solid rgba(168,85,247,0.3)",
                borderRadius: 99,
                padding: "5px 14px",
                marginBottom: 18,
                fontSize: 11,
                color: "#c084fc",
                letterSpacing: 1.2,
                textTransform: "uppercase",
                fontWeight: 600,
              }}
            >
              Accès anticipé · Gratuit
            </div>

            <h2 style={{ margin: "0 0 8px", color: "#fff", fontSize: 21, lineHeight: 1.25 }}>
              Soyez prévenus en avant-première
            </h2>
            <p style={{ margin: "0 0 22px", color: "rgba(255,255,255,0.45)", fontSize: 13, lineHeight: 1.6 }}>
              Analyses de marché IDF, alertes de prix, nouvelles fonctionnalités —
              en exclusivité pour les inscrits.
            </p>

            <form onSubmit={handleSubmit}>
              {/* Prénom + Nom côte à côte */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 12 }}>
                <label>
                  <span style={labelStyle}>Prénom *</span>
                  <input
                    type="text"
                    required
                    value={form.prenom}
                    onChange={set("prenom")}
                    placeholder="Thomas"
                    style={inputStyle}
                  />
                </label>
                <label>
                  <span style={labelStyle}>Nom *</span>
                  <input
                    type="text"
                    required
                    value={form.nom}
                    onChange={set("nom")}
                    placeholder="Dupont"
                    style={inputStyle}
                  />
                </label>
              </div>

              {/* Société */}
              <label style={{ display: "block", marginBottom: 12 }}>
                <span style={labelStyle}>Société</span>
                <input
                  type="text"
                  value={form.societe}
                  onChange={set("societe")}
                  placeholder="Agence, promoteur, cabinet..."
                  style={inputStyle}
                />
              </label>

              {/* Email */}
              <label style={{ display: "block", marginBottom: 12 }}>
                <span style={labelStyle}>Email *</span>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={set("email")}
                  placeholder="vous@exemple.fr"
                  style={inputStyle}
                />
              </label>

              {/* Téléphone */}
              <label style={{ display: "block", marginBottom: 18 }}>
                <span style={labelStyle}>Téléphone</span>
                <input
                  type="tel"
                  value={form.telephone}
                  onChange={set("telephone")}
                  placeholder="+33 6 ..."
                  style={inputStyle}
                />
              </label>

              {/* Consentement RGPD */}
              <label
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  marginBottom: 18,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  required
                  checked={form.consentement}
                  onChange={set("consentement")}
                  style={{ marginTop: 3, accentColor: "#a855f7", flexShrink: 0 }}
                />
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", lineHeight: 1.6 }}>
                  J&apos;accepte de recevoir les communications de datamerry.com (analyses, nouveautés, surprises) et
                  l&apos;utilisation de cookies analytiques.{" "}
                  <span style={{ color: "rgba(255,255,255,0.2)" }}>
                    Données protégées · Désabonnement à tout moment.
                  </span>
                </span>
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
                  boxShadow: "0 0 24px rgba(168,85,247,0.35)",
                  transition: "opacity 0.2s",
                  fontFamily: "Segoe UI, Arial, sans-serif",
                }}
              >
                {status === "loading" ? "Enregistrement..." : "Je veux être prévenu(e) →"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
