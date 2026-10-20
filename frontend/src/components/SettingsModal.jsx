import React, { useState, useEffect } from "react";
import { X, Settings, Cpu, Layers, Volume2, Eye, EyeOff, Save, Check, Info } from "lucide-react";

export default function SettingsModal({
  isOpen,
  onClose,
  aiSettings,
  onSaveSettings,
}) {
  const [formData, setFormData] = useState({
    provider: aiSettings?.provider || "Ollama (Local)",
    modelName: aiSettings?.modelName || "qwen2.5:14b",
    apiKey: aiSettings?.apiKey || "",
    topK: aiSettings?.topK || 6,
    chunkSize: aiSettings?.chunkSize || 1000,
    chunkOverlap: aiSettings?.chunkOverlap || 150,
    voiceSpeed: aiSettings?.voiceSpeed || 1.0,
    voiceURI: aiSettings?.voiceURI || "",
    karaokeEnabled: aiSettings?.karaokeEnabled !== false,
  });

  const [showApiKey, setShowApiKey] = useState(false);
  const [activeTab, setActiveTab] = useState("model");
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [voiceList, setVoiceList] = useState([]);

  useEffect(() => {
    if (window.speechSynthesis) {
      const loadVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        const curated = voices.slice(0, 15).map((v) => ({
          uri: v.voiceURI || v.name,
          name: v.lang.startsWith("es") ? `🇪🇸 ${v.name} (${v.lang})` : `🇺🇸 ${v.name} (${v.lang})`,
        }));
        if (curated.length < 10) {
          curated.push(
            { uri: "preset_es_1", name: "🇪🇸 Sabina / Elena (Español Natural)" },
            { uri: "preset_es_2", name: "🇪🇸 Pablo (Español Grave)" },
            { uri: "preset_es_3", name: "🇪🇸 Laura (Español Radial)" },
            { uri: "preset_mx_1", name: "🇲🇽 Raúl (Español México Narrador)" },
            { uri: "preset_mx_2", name: "🇲🇽 Paulina (Español México Cálido)" },
            { uri: "preset_ar_1", name: "🇦🇷 Diego (Español Argentina)" },
            { uri: "preset_co_1", name: "🇨🇴 Sofía (Español Colombia)" },
            { uri: "preset_es_doc", name: "🇪🇸 Narrador Documental Pro" },
            { uri: "preset_en_1", name: "🇺🇸 David (Corporativa Bilingüe)" },
            { uri: "preset_en_2", name: "🇺🇸 Jenny (Profesional Bilingüe)" }
          );
        }
        setVoiceList(curated);
      };
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveSettings(formData);
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 600);
  };

  const installedOllamaModels = [
    "qwen2.5:14b",
    "qwen2.5:7b",
    "mistral-small:24b",
    "qwen2.5:32b",
    "llava:7b",
  ];

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
          width: "620px",
          maxWidth: "94vw",
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
                  <option value="Ollama (Local)">Ollama (Local con Aceleración GPU - Recomendado)</option>
                  <option value="Llama.cpp Server (Local)">Llama.cpp Server (Requiere llama-server en puerto 8080)</option>
                  <option value="OpenAI / Groq API (Nube)">OpenAI / Groq API (Nube)</option>
                  <option value="Google Gemini (Nube)">Google Gemini (Nube)</option>
                </select>

                {formData.provider === "Llama.cpp Server (Local)" && (
                  <div style={{ marginTop: "6px", padding: "8px 10px", background: "rgba(234, 179, 8, 0.12)", border: "1px solid rgba(234, 179, 8, 0.3)", borderRadius: "6px", fontSize: "0.76rem", color: "#facc15", display: "flex", gap: "6px" }}>
                    <Info size={14} style={{ flexShrink: 0, marginTop: "1px" }} />
                    <span>Llama.cpp requiere que ejecutes manualmente <code>llama-server.exe</code> en el puerto 8080. Si usas Ollama, tus modelos como qwen2.5:14b ya están listos en el puerto 11434.</span>
                  </div>
                )}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "500" }}>
                  Nombre del Modelo:
                </label>
                <input
                  type="text"
                  value={formData.modelName}
                  onChange={(e) => setFormData({ ...formData, modelName: e.target.value })}
                  placeholder="ej: qwen2.5:14b, qwen2.5:7b, gpt-4o-mini"
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

                {formData.provider === "Ollama (Local)" && (
                  <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "0.74rem", color: "var(--text-muted)" }}>Modelos instalados en tu PC:</span>
                    {installedOllamaModels.map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setFormData({ ...formData, modelName: m })}
                        style={{
                          background: formData.modelName === m ? "var(--accent)" : "var(--bg-base)",
                          color: formData.modelName === m ? "#ffffff" : "var(--text)",
                          border: "1px solid var(--border)",
                          padding: "2px 8px",
                          borderRadius: "10px",
                          fontSize: "0.72rem",
                          cursor: "pointer",
                          fontWeight: formData.modelName === m ? "600" : "400",
                        }}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                )}
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
                    placeholder="sk-... (solo para modelos en la nube)"
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
                    Top-K Fragmentos Recuperados por Consulta:
                  </label>
                  <span style={{ fontSize: "0.82rem", fontWeight: "700", color: "var(--accent)" }}>{formData.topK} Chunks</span>
                </div>
                <input
                  type="range"
                  min="2"
                  max="12"
                  value={formData.topK}
                  onChange={(e) => setFormData({ ...formData, topK: parseInt(e.target.value, 10) })}
                  style={{ width: "100%", cursor: "pointer", accentColor: "var(--accent)" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "500" }}>
                  Tamaño de Fragmento (Chunk Size en caracteres):
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
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "500" }}>
                  Voz Predeterminada del Lector:
                </label>
                <select
                  value={formData.voiceURI}
                  onChange={(e) => setFormData({ ...formData, voiceURI: e.target.value })}
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
                  {voiceList.map((v, idx) => (
                    <option key={idx} value={v.uri}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </div>

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
              padding: "8px 20px",
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
              transition: "all 0.2s ease",
            }}
          >
            {savedSuccess ? <Check size={16} /> : <Save size={16} />}
            <span>{savedSuccess ? "Guardado" : "Guardar Cambios"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
