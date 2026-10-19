import React, { useState } from "react";
import { Upload, Trash2, File, CheckCircle2, ChevronDown, Palette, RefreshCw } from "lucide-react";

export default function Sidebar({
  documents = [],
  activeDoc = "",
  onSelectDoc,
  onDeleteDoc,
  onUploadSuccess,
  theme,
  onThemeChange,
  themes = {},
}) {
  const [uploading, setUploading] = useState(false);
  const [analyzeImages, setAnalyzeImages] = useState(true);
  const [provider, setProvider] = useState("Ollama (Local)");

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const { uploadDocument } = await import("../services/api");
      await uploadDocument(file, { analyzeImages, provider });
      if (onUploadSuccess) onUploadSuccess(file.name);
    } catch (err) {
      alert("Error en la subida: " + err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  return (
    <aside
      style={{
        width: "280px",
        background: "var(--bg-sidebar)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        padding: "16px",
        height: "100%",
        overflowY: "auto",
      }}
    >
      {/* Brand Header */}
      <div style={{ marginBottom: "20px", paddingBottom: "12px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontSize: "1.1rem", fontWeight: "700", letterSpacing: "-0.02em", color: "var(--text)" }}>
          Document Studio
        </div>
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
          Next.js + FastAPI Microservices
        </div>
      </div>

      {/* Selector de Documento Activo */}
      <div style={{ marginBottom: "20px" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--text-muted)", marginBottom: "8px", textTransform: "uppercase" }}>
          Documento Activo
        </div>
        <select
          value={activeDoc}
          onChange={(e) => onSelectDoc(e.target.value)}
          style={{
            width: "100%",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            color: "var(--text)",
            borderRadius: "6px",
            padding: "8px 10px",
            fontSize: "0.85rem",
            outline: "none",
            cursor: "pointer",
          }}
        >
          <option value="Todos los documentos">Todos los documentos</option>
          {documents.map((d) => (
            <option key={d.filename} value={d.filename}>
              {d.filename} ({d.chunks} págs)
            </option>
          ))}
        </select>

        {activeDoc && activeDoc !== "Todos los documentos" && (
          <button
            onClick={() => onDeleteDoc(activeDoc)}
            style={{
              marginTop: "8px",
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--danger)",
              padding: "6px 10px",
              borderRadius: "6px",
              fontSize: "0.8rem",
              cursor: "pointer",
            }}
          >
            <Trash2 size={13} />
            Eliminar documento
          </button>
        )}
      </div>

      {/* Subida de PDF */}
      <div style={{ marginBottom: "20px", paddingBottom: "16px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--text-muted)", marginBottom: "8px", textTransform: "uppercase" }}>
          Cargar PDF (Hasta 30 Págs)
        </div>
        
        <label
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "16px",
            background: "var(--bg-card)",
            border: "1px dashed var(--border)",
            borderRadius: "8px",
            cursor: uploading ? "not-allowed" : "pointer",
            textAlign: "center",
          }}
        >
          <Upload size={20} color="var(--accent)" style={{ marginBottom: "6px" }} />
          <span style={{ fontSize: "0.82rem", fontWeight: "500" }}>{uploading ? "Indexando con OCR..." : "Seleccionar archivo PDF"}</span>
          <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "2px" }}>1 chunk por página</span>
          <input type="file" accept=".pdf" onChange={handleFileUpload} disabled={uploading} style={{ display: "none" }} />
        </label>

        <div style={{ marginTop: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
          <input
            type="checkbox"
            id="chk-vision"
            checked={analyzeImages}
            onChange={(e) => setAnalyzeImages(e.target.checked)}
            style={{ accentColor: "var(--accent)" }}
          />
          <label htmlFor="chk-vision" style={{ fontSize: "0.75rem", color: "var(--text-muted)", cursor: "pointer" }}>
            Analizar imágenes con IA de visión
          </label>
        </div>
      </div>

      {/* Selector de Tema */}
      <div style={{ marginTop: "auto" }}>
        <div style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--text-muted)", marginBottom: "8px", textTransform: "uppercase" }}>
          Tema y Apariencia
        </div>
        <select
          value={theme}
          onChange={(e) => onThemeChange(e.target.value)}
          style={{
            width: "100%",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            color: "var(--text)",
            borderRadius: "6px",
            padding: "8px 10px",
            fontSize: "0.82rem",
            outline: "none",
            cursor: "pointer",
          }}
        >
          {Object.keys(themes).map((tName) => (
            <option key={tName} value={tName}>
              {tName}
            </option>
          ))}
        </select>
      </div>
    </aside>
  );
}
