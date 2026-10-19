import React, { useState } from "react";
import { FileText, Sparkles, Loader2 } from "lucide-react";
import { fetchSummary } from "../services/api";

export default function SummaryView({ filename, aiSettings }) {
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerateSummary = async () => {
    if (!filename || filename === "Todos los documentos") {
      alert("Por favor selecciona un documento específico para generar su síntesis.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetchSummary({
        filename,
        provider: aiSettings.provider,
        apiKey: aiSettings.apiKey,
        modelName: aiSettings.modelName,
      });
      setSummary(res.summary);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", overflow: "hidden", background: "var(--bg-base)", padding: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
        <div style={{ fontSize: "1rem", fontWeight: "600", color: "var(--text)" }}>
          Síntesis Documental: <span style={{ color: "var(--accent)" }}>{filename || "Ningún archivo seleccionado"}</span>
        </div>
        <button
          onClick={handleGenerateSummary}
          disabled={loading || !filename || filename === "Todos los documentos"}
          style={{
            background: "var(--accent)",
            border: "none",
            color: "#ffffff",
            padding: "8px 16px",
            borderRadius: "6px",
            fontSize: "0.85rem",
            cursor: loading ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
          {summary ? "Regenerar Síntesis" : "Generar Síntesis"}
        </button>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "20px",
          fontSize: "0.92rem",
          lineHeight: "1.6",
          whiteSpace: "pre-wrap",
        }}
      >
        {summary ? (
          summary
        ) : (
          <div style={{ color: "var(--text-muted)", textAlign: "center", marginTop: "40px" }}>
            Aún no has generado la síntesis de este archivo. Haz clic en "Generar Síntesis" para obtener un análisis estructurado.
          </div>
        )}
      </div>
    </div>
  );
}
