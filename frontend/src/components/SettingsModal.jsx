import React, { useState } from "react";
import { X, Settings, Cpu, Layers, Volume2, Eye, EyeOff, Save, Check } from "lucide-react";

export default function SettingsModal({
  isOpen,
  onClose,
  aiSettings,
  onSaveSettings,
}) {
  const [formData, setFormData] = useState({
    provider: aiSettings.provider || "Ollama (Local)",
    modelName: aiSettings.modelName || "qwen2.5:7b",
    apiKey: aiSettings.apiKey || "",
    topK: aiSettings.topK || 6,
    chunkSize: aiSettings.chunkSize || 1000,
    chunkOverlap: aiSettings.chunkOverlap || 150,
    voiceSpeed: aiSettings.voiceSpeed || 1.0,
    karaokeEnabled: aiSettings.karaokeEnabled !== false,
  });

  const [showApiKey, setShowApiKey] = useState(false);
  const [activeTab, setActiveTab] = useState("model");
  const [savedSuccess, setSavedSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveSettings(formData);
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 600);
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        background: "rgba(0,0,0,0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 99999,
      }}
    >
      <div
        style={{
          width: "600px",
          maxWidth: "92vw",
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "14px",
          boxShadow: "0 20px 45px rgba(0,0,0,0.6)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: "700", color: "var(--text)", fontSize: "1.05rem" }}>
            <Settings size={18} color="var(--accent)" />
            <span>Configuración y Parámetros del Sistema</span>
          </div>
          <button onClick={onClose} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}>
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--border)", background: "var(--bg-base)" }}>
          <button
            onClick={() => setActiveTab("model")}
            style={{
              flex: 1,
              padding: "10px",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "model" ? "2px solid var(--accent)" : "none",
              color: activeTab === "model" ? "var(--accent)" : "var(--text-muted)",
              fontWeight: activeTab === "model" ? "600" : "400",
              fontSize: "0.85rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              cursor: "pointer",
            }}
          >
            <Cpu size={15} />
            <span>Modelo e IA</span>
          </button>

          <button
            onClick={() => setActiveTab("rag")}
            style={{
              flex: 1,
              padding: "10px",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "rag" ? "2px solid var(--accent)" : "none",
              color: activeTab === "rag" ? "var(--accent)" : "var(--text-muted)",
              fontWeight: activeTab === "rag" ? "600" : "400",
              fontSize: "0.85rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              cursor: "pointer",
            }}
          >
            <Layers size={15} />
            <span>Vectores y Chunks</span>
          </button>

          <button
            onClick={() => setActiveTab("voice")}
            style={{
              flex: 1,
              padding: "10px",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === "voice" ? "2px solid var(--accent)" : "none",
              color: activeTab === "voice" ? "var(--accent)" : "var(--text-muted)",
              fontWeight: activeTab === "voice" ? "600" : "400",
              fontSize: "0.85rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              cursor: "pointer",
            }}
          >
            <Volume2 size={15} />
            <span>Lector de Voz y Karaoke</span>
          </button>
        </div>

        {/* Tab Content */}
        <div style={{ padding: "22px", display: "flex", flexDirection: "column", gap: "16px", maxHeight: "65vh", overflowY: "auto" }}>
          {activeTab === "model" && (
            <>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "500" }}>
                  Proveedor de Inferencia:
                </label>
                <select
                  value={formData.provider}
                  onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    background: "var(--bg-base)",
                    border: "1px solid var(--border)",
                    color: "var(--text)",
                    fontSize: "0.85rem",
                    outline: "none",
                  }}
                >
                  <option value="Ollama (Local)">Ollama (Local en tu PC)</option>
                  <option value="OpenAI">OpenAI (GPT-4o, GPT-3.5)</option>
                  <option value="Google Gemini">Google Gemini (Gemini 1.5 Pro/Flash)</option>
                  <option value="Anthropic Claude">Anthropic Claude (Claude 3.5 Sonnet)</option>
                  <option value="Groq">Groq (Inferencia Ultra-rápida Llama 3)</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "500" }}>
                  Nombre del Modelo:
                </label>
                <input
                  type="text"
                  value={formData.modelName}
                  onChange={(e) => setFormData({ ...formData, modelName: e.target.value })}
                  placeholder="ej: qwen2.5:7b, llama3.2, gpt-4o"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    background: "var(--bg-base)",
                    border: "1px solid var(--border)",
                    color: "var(--text)",
                    fontSize: "0.85rem",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "500" }}>
                  Clave de API (si aplica):
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    type={showApiKey ? "text" : "password"}
                    value={formData.apiKey}
                    onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                    placeholder="sk-..."
                    style={{
                      width: "100%",
                      padding: "8px 36px 8px 12px",
                      borderRadius: "6px",
                      background: "var(--bg-base)",
                      border: "1px solid var(--border)",
                      color: "var(--text)",
                      fontSize: "0.85rem",
                      outline: "none",
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    style={{
                      position: "absolute",
                      right: "10px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "transparent",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                    }}
                  >
                    {showApiKey ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>
            </>
          )}

          {activeTab === "rag" && (
            <>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: "500" }}>
                    Top-K Fragmentos Recuperados (Contexto):
                  </label>
                  <span style={{ fontSize: "0.82rem", fontWeight: "700", color: "var(--accent)" }}>{formData.topK}</span>
                </div>
                <input
                  type="range"
                  min="3"
                  max="15"
                  value={formData.topK}
                  onChange={(e) => setFormData({ ...formData, topK: parseInt(e.target.value, 10) })}
                  style={{ width: "100%", cursor: "pointer", accentColor: "var(--accent)" }}
                />
                <span style={{ fontSize: "0.74rem", color: "var(--text-muted)" }}>
                  Determina cuántos fragmentos vectoriales de máxima similitud en PostgreSQL pgvector se inyectan al prompt.
                </span>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "500" }}>
                  Tamaño de Chunk (Caracteres):
                </label>
                <input
                  type="number"
                  value={formData.chunkSize}
                  onChange={(e) => setFormData({ ...formData, chunkSize: parseInt(e.target.value, 10) || 1000 })}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    background: "var(--bg-base)",
                    border: "1px solid var(--border)",
                    color: "var(--text)",
                    fontSize: "0.85rem",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "500" }}>
                  Solapamiento entre Chunks (Overlap):
                </label>
                <input
                  type="number"
                  value={formData.chunkOverlap}
                  onChange={(e) => setFormData({ ...formData, chunkOverlap: parseInt(e.target.value, 10) || 150 })}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    background: "var(--bg-base)",
                    border: "1px solid var(--border)",
                    color: "var(--text)",
                    fontSize: "0.85rem",
                    outline: "none",
                  }}
                />
              </div>
            </>
          )}

          {activeTab === "voice" && (
            <>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: "500" }}>
                    Velocidad del Lector de Voz:
                  </label>
                  <span style={{ fontSize: "0.82rem", fontWeight: "700", color: "var(--accent)" }}>{formData.voiceSpeed}x</span>
                </div>
                <input
                  type="range"
                  min="0.75"
                  max="1.75"
                  step="0.05"
                  value={formData.voiceSpeed}
                  onChange={(e) => setFormData({ ...formData, voiceSpeed: parseFloat(e.target.value) })}
                  style={{ width: "100%", cursor: "pointer", accentColor: "var(--accent)" }}
                />
              </div>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0" }}>
                <div>
                  <div style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--text)" }}>
                    Efecto Iluminado Karaoke
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Ilumina dinámicamente la palabra actual mientras el bot habla con una estela de luz suave.
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={formData.karaokeEnabled}
                  onChange={(e) => setFormData({ ...formData, karaokeEnabled: e.target.checked })}
                  style={{ width: "18px", height: "18px", accentColor: "var(--accent)", cursor: "pointer" }}
                />
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "flex-end", gap: "10px", background: "var(--bg-base)" }}>
          <button
            onClick={onClose}
            style={{
              padding: "8px 16px",
              borderRadius: "6px",
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text)",
              fontSize: "0.85rem",
              cursor: "pointer",
            }}
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            style={{
              padding: "8px 18px",
              borderRadius: "6px",
              background: savedSuccess ? "#10b981" : "var(--accent)",
              border: "none",
              color: "#ffffff",
              fontSize: "0.85rem",
              fontWeight: "600",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "background 0.2s ease",
            }}
          >
            {savedSuccess ? <Check size={16} /> : <Save size={16} />}
            <span>{savedSuccess ? "Guardado" : "Guardar Parámetros"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
