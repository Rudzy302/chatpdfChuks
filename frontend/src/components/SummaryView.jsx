import React, { useState, useEffect } from "react";
import { FileText, Sparkles, Loader2, Volume2, VolumeX } from "lucide-react";
import { fetchSummary } from "../services/api";

export default function SummaryView({ filename, aiSettings, onNavigateToPage }) {
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speed, setSpeed] = useState(1.0);

  // Detener voz al desmontar o cambiar de documento
  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [filename]);

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

  const toggleSpeak = () => {
    if (!window.speechSynthesis) {
      alert("Tu navegador no soporta síntesis de voz.");
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    if (!summary) return;

    window.speechSynthesis.cancel();
    // Limpiar marcadores [Pág. X] para que el lector no deletree los corchetes
    const textToRead = summary.replace(/\[(?:Pág\.|Página|Pag\.)\s*\d+\]/gi, "");
    const utterance = new SpeechSynthesisUtterance(textToRead);
    utterance.lang = "es-ES";
    utterance.rate = speed;

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  const renderWithCitations = (text) => {
    if (!text) return null;
    const regex = /\[(?:Pág\.|Página|Pag\.)\s*(\d+)\]/gi;
    const parts = [];
    let lastIdx = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      const pageNum = parseInt(match[1], 10);
      if (match.index > lastIdx) {
        parts.push(text.substring(lastIdx, match.index));
      }
      parts.push(
        <button
          key={match.index}
          onClick={() => onNavigateToPage && onNavigateToPage(pageNum)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "3px",
            background: "rgba(14, 165, 233, 0.12)",
            border: "1px solid rgba(14, 165, 233, 0.4)",
            color: "var(--accent)",
            padding: "1px 8px",
            borderRadius: "12px",
            fontSize: "0.78rem",
            fontWeight: "600",
            cursor: "pointer",
            margin: "0 3px",
            verticalAlign: "middle",
            transition: "all 0.15s ease",
          }}
          title={`Ir a Página ${pageNum} en el visor continuo del PDF`}
        >
          📄 Pág. {pageNum}
        </button>
      );
      lastIdx = regex.lastIndex;
    }

    if (lastIdx < text.length) {
      parts.push(text.substring(lastIdx));
    }
    return parts;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", overflow: "hidden", background: "var(--bg-base)", padding: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ fontSize: "1rem", fontWeight: "600", color: "var(--text)" }}>
          Síntesis Documental: <span style={{ color: "var(--accent)" }}>{filename || "Ningún archivo seleccionado"}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {summary && (
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <button
                onClick={toggleSpeak}
                style={{
                  background: isSpeaking ? "rgba(239, 68, 68, 0.15)" : "var(--bg-card)",
                  border: `1px solid ${isSpeaking ? "#ef4444" : "var(--border)"}`,
                  color: isSpeaking ? "#f87171" : "var(--text)",
                  padding: "7px 12px",
                  borderRadius: "6px",
                  fontSize: "0.82rem",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
                title={isSpeaking ? "Detener lectura de voz" : "Escuchar síntesis con voz natural"}
              >
                {isSpeaking ? <VolumeX size={15} color="#ef4444" /> : <Volume2 size={15} />}
                <span>{isSpeaking ? "Detener Lector" : "Escuchar Síntesis"}</span>
              </button>
              <select
                value={speed}
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  color: "var(--text-muted)",
                  padding: "6px 8px",
                  borderRadius: "6px",
                  fontSize: "0.78rem",
                  cursor: "pointer",
                }}
                title="Velocidad de locución"
              >
                <option value={0.85}>0.85x</option>
                <option value={1.0}>1.0x</option>
                <option value={1.2}>1.2x</option>
                <option value={1.5}>1.5x</option>
              </select>
            </div>
          )}

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
          lineHeight: "1.65",
          whiteSpace: "pre-wrap",
        }}
      >
        {summary ? (
          renderWithCitations(summary)
        ) : (
          <div style={{ color: "var(--text-muted)", textAlign: "center", marginTop: "40px" }}>
            Aún no has generado la síntesis de este archivo. Haz clic en "Generar Síntesis" para obtener un análisis estructurado con citas de página.
          </div>
        )}
      </div>
    </div>
  );
}
