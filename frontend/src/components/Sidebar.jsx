import React, { useState } from "react";
import {
  Upload,
  Trash2,
  File,
  CheckCircle2,
  ChevronDown,
  Palette,
  RefreshCw,
  Power,
  Settings,
  Plus,
  MessageSquare,
  FolderOpen,
} from "lucide-react";

export default function Sidebar({
  documents = [],
  activeDoc = "",
  onSelectDoc,
  onDeleteDoc,
  onUploadSuccess,
  theme,
  onThemeChange,
  themes = {},
  onOpenSettings,
  sessions = [],
  currentSessionId = "",
  onSelectSession,
  onNewSession,
  onDeleteSession,
}) {
  const [sidebarTab, setSidebarTab] = useState("chats"); // 'chats' | 'docs'
  const [uploading, setUploading] = useState(false);
  const [analyzeImages, setAnalyzeImages] = useState(true);
  const [provider, setProvider] = useState("Ollama (Local)");

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const { uploadDocument } = await import("../services/api");
      const res = await uploadDocument(file, { analyzeImages, provider });
      if (onUploadSuccess) onUploadSuccess(file.name, res.data);
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
        width: "300px",
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
      <div style={{ marginBottom: "14px", paddingBottom: "12px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: "1.1rem", fontWeight: "700", letterSpacing: "-0.02em", color: "var(--text)" }}>
            Document Studio
          </div>
          <span style={{ fontSize: "0.68rem", padding: "2px 6px", borderRadius: "10px", background: "rgba(16, 185, 129, 0.15)", color: "#10b981", fontWeight: "600" }}>
            Local PC
          </span>
        </div>
        <div style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginTop: "2px" }}>
          Historial & Contextos RAG Persistentes
        </div>
      </div>

      {/* Botón de Nueva Sesión */}
      <button
        onClick={onNewSession}
        style={{
          width: "100%",
          padding: "9px 12px",
          borderRadius: "8px",
          background: "linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%)",
          border: "1px solid rgba(168, 85, 247, 0.35)",
          color: "var(--text)",
          fontSize: "0.82rem",
          fontWeight: "600",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          cursor: "pointer",
          marginBottom: "12px",
          transition: "all 0.2s ease",
        }}
      >
        <Plus size={15} color="#c084fc" />
        <span>Nueva Sesión de Chat</span>
      </button>

      {/* Tabs Superiores de la Barra Lateral */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border)", marginBottom: "14px" }}>
        <button
          onClick={() => setSidebarTab("chats")}
          style={{
            flex: 1,
            padding: "8px 4px",
            background: "transparent",
            border: "none",
            borderBottom: sidebarTab === "chats" ? "2px solid var(--accent)" : "2px solid transparent",
            color: sidebarTab === "chats" ? "var(--accent)" : "var(--text-muted)",
            fontSize: "0.8rem",
            fontWeight: sidebarTab === "chats" ? "700" : "500",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "5px",
            cursor: "pointer",
          }}
        >
          <MessageSquare size={13} />
          <span>Chats ({sessions.length})</span>
        </button>

        <button
          onClick={() => setSidebarTab("docs")}
          style={{
            flex: 1,
            padding: "8px 4px",
            background: "transparent",
            border: "none",
            borderBottom: sidebarTab === "docs" ? "2px solid var(--accent)" : "2px solid transparent",
            color: sidebarTab === "docs" ? "var(--accent)" : "var(--text-muted)",
            fontSize: "0.8rem",
            fontWeight: sidebarTab === "docs" ? "700" : "500",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "5px",
            cursor: "pointer",
          }}
        >
          <FolderOpen size={13} />
          <span>PDFs ({documents.length})</span>
        </button>
      </div>

      {/* Contenido de la pestaña: CHATS / SESIONES */}
      {sidebarTab === "chats" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "16px", maxHeight: "280px", overflowY: "auto", paddingRight: "2px" }}>
          {sessions.length === 0 ? (
            <div style={{ padding: "16px 8px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.78rem" }}>
              No hay chats guardados aún. Inicia uno con el botón superior.
            </div>
          ) : (
            sessions.map((s) => {
              const isActive = s.id === currentSessionId;
              return (
                <div
                  key={s.id}
                  onClick={() => onSelectSession && onSelectSession(s)}
                  style={{
                    padding: "8px 10px",
                    borderRadius: "6px",
                    background: isActive ? "var(--accent-light)" : "var(--bg-card)",
                    border: isActive ? "1px solid var(--accent)" : "1px solid var(--border)",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px" }}>
                    <span
                      style={{
                        fontSize: "0.8rem",
                        fontWeight: isActive ? "700" : "500",
                        color: isActive ? "var(--accent)" : "var(--text)",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        flex: 1,
                      }}
                      title={s.title}
                    >
                      {s.title || "Nuevo Chat"}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`¿Eliminar la sesión '${s.title}' del historial?`)) {
                          onDeleteSession && onDeleteSession(s.id);
                        }
                      }}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "var(--text-muted)",
                        cursor: "pointer",
                        padding: "2px",
                        display: "flex",
                        alignItems: "center",
                      }}
                      title="Eliminar sesión"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.68rem", color: "var(--text-muted)" }}>
                    <span
                      style={{
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        maxWidth: "180px",
                        color: s.active_doc ? "var(--text)" : "var(--text-muted)",
                      }}
                      title={s.active_doc ? `Asociado a: ${s.active_doc}` : "Sin documento asociado"}
                    >
                      {s.active_doc ? `📄 ${s.active_doc}` : "🌐 Consulta General"}
                    </span>
                    <span>{s.message_count || 0} msgs</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Contenido de la pestaña: DOCUMENTOS */}
      {sidebarTab === "docs" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "16px" }}>
          <div>
            <div style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px", textTransform: "uppercase" }}>
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
                fontSize: "0.82rem",
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
                  marginTop: "6px",
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
                  fontSize: "0.78rem",
                  cursor: "pointer",
                }}
              >
                <Trash2 size={12} />
                Eliminar de la base de datos
              </button>
            )}
          </div>

          {/* Subida de PDF */}
          <div>
            <div style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px", textTransform: "uppercase" }}>
              Cargar Nuevo PDF
            </div>
            
            <label
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "14px",
                background: "var(--bg-card)",
                border: "1px dashed var(--border)",
                borderRadius: "8px",
                cursor: uploading ? "not-allowed" : "pointer",
                textAlign: "center",
              }}
            >
              <Upload size={18} color="var(--accent)" style={{ marginBottom: "4px" }} />
              <span style={{ fontSize: "0.8rem", fontWeight: "500" }}>{uploading ? "Indexando con OCR..." : "Seleccionar archivo PDF"}</span>
              <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginTop: "2px" }}>1 chunk consolidado por pág.</span>
              <input type="file" accept=".pdf" onChange={handleFileUpload} disabled={uploading} style={{ display: "none" }} />
            </label>

            <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
              <input
                type="checkbox"
                id="chk-vision"
                checked={analyzeImages}
                onChange={(e) => setAnalyzeImages(e.target.checked)}
                style={{ accentColor: "var(--accent)" }}
              />
              <label htmlFor="chk-vision" style={{ fontSize: "0.72rem", color: "var(--text-muted)", cursor: "pointer" }}>
                Analizar imágenes con visión
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Indicador de Documento Asociado al Chat Actual */}
      {sidebarTab === "chats" && (
        <div style={{ padding: "8px 10px", background: "rgba(255, 255, 255, 0.03)", border: "1px solid var(--border)", borderRadius: "6px", marginBottom: "14px", fontSize: "0.74rem" }}>
          <div style={{ color: "var(--text-muted)", marginBottom: "2px", fontSize: "0.68rem", fontWeight: "600", textTransform: "uppercase" }}>
            Contexto Documental Activo:
          </div>
          <div style={{ color: "var(--accent)", fontWeight: "600", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {activeDoc || "Sin documento (Modo General)"}
          </div>
        </div>
      )}

      {/* Botón de Parámetros de IA y Chunks */}
      <div style={{ marginTop: "auto", marginBottom: "14px" }}>
        <button
          onClick={onOpenSettings}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
            padding: "9px 12px",
            borderRadius: "6px",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            color: "var(--text)",
            fontSize: "0.82rem",
            fontWeight: "500",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--accent)";
            e.currentTarget.style.color = "var(--accent)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--border)";
            e.currentTarget.style.color = "var(--text)";
          }}
        >
          <Settings size={15} />
          <span>Parámetros de IA y Chunks</span>
        </button>
      </div>

      {/* Selector de Tema */}
      <div style={{ marginBottom: "16px" }}>
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

      {/* Botón de Apagado Completo de Procesos */}
      <button
        onClick={async () => {
          if (confirm("¿Deseas cerrar la aplicación y apagar todos los procesos de fondo (backend, frontend y servidores)?")) {
            const { shutdownSystem } = await import("../services/api");
            await shutdownSystem();
            window.close();
            document.body.innerHTML = "<div style='display:flex;height:100vh;align-items:center;justify-content:center;background:#111;color:#fff;font-family:sans-serif;'><h1>Aplicación y procesos cerrados correctamente. Ya puedes cerrar esta pestaña.</h1></div>";
          }
        }}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          padding: "10px",
          borderRadius: "6px",
          background: "rgba(239, 68, 68, 0.12)",
          border: "1px solid rgba(239, 68, 68, 0.3)",
          color: "#f87171",
          fontSize: "0.82rem",
          fontWeight: "600",
          cursor: "pointer",
          transition: "background 0.2s ease",
        }}
      >
        <Power size={14} />
        Cerrar y Apagar Servidor
      </button>
    </aside>
  );
}
