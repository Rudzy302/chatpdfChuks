import React, { useState, useEffect } from "react";
import {
  X,
  Settings,
  Cpu,
  Layers,
  Volume2,
  Eye,
  EyeOff,
  Save,
  Check,
  Info,
  Sparkles,
  RefreshCw,
  Zap,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";
import { detectAvailableModels } from "../services/api";

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

  // Estados de detección inteligente de modelos y plan
  const [detectingModels, setDetectingModels] = useState(false);
  const [detectedData, setDetectedData] = useState(null);
  const [detectionError, setDetectionError] = useState("");

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

  const handleDetectModels = async () => {
    setDetectingModels(true);
    setDetectionError("");
    try {
      const data = await detectAvailableModels({
        provider: formData.provider,
        apiKey: formData.apiKey,
      });
      setDetectedData(data);
      if (data.models && data.models.length > 0) {
        const hasCurrent = data.models.some((m) => m.id === formData.modelName);
        if (!hasCurrent) {
          setFormData((prev) => ({ ...prev, modelName: data.models[0].id }));
        }
      }
    } catch (err) {
      setDetectionError(err.message || "Error al conectar con el proveedor");
    } finally {
      setDetectingModels(false);
    }
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
                  onChange={(e) => {
                    const newProv = e.target.value;
                    setFormData({ ...formData, provider: newProv });
                    setDetectedData(null);
                    setDetectionError("");
                  }}
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
                  <option value="Ollama (Local)">🟢 Ollama (Local en tu PC - 100% Gratuito y Privado)</option>
                  <option value="OpenRouter">🌐 OpenRouter (Acceso Universal: DeepSeek R1, GPT-4o, Claude, Gemini)</option>
                  <option value="Google Gemini">✨ Google Gemini (Nube Oficial - 15 req/min Gratis)</option>
                  <option value="DeepSeek API">⚡ DeepSeek API (Oficial - Chat V3 & R1 Reasoner)</option>
                  <option value="OpenAI">🤖 OpenAI (Oficial - GPT-4o, o1, o3-mini)</option>
                  <option value="Llama.cpp Server (Local)">🖥️ Llama.cpp Server (Local en puerto 8080)</option>
                </select>

                {formData.provider === "Llama.cpp Server (Local)" && (
                  <div style={{ marginTop: "6px", padding: "8px 10px", background: "rgba(234, 179, 8, 0.12)", border: "1px solid rgba(234, 179, 8, 0.3)", borderRadius: "6px", fontSize: "0.76rem", color: "#facc15", display: "flex", gap: "6px" }}>
                    <Info size={14} style={{ flexShrink: 0, marginTop: "1px" }} />
                    <span>Llama.cpp requiere ejecutar manualmente <code>llama-server.exe</code> en el puerto 8080. Si usas Ollama, tus modelos están listos en el puerto 11434.</span>
                  </div>
                )}
              </div>

              {formData.provider !== "Ollama (Local)" && formData.provider !== "Llama.cpp Server (Local)" && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: "500" }}>
                      Clave de API / Token:
                    </label>
                    {formData.provider.includes("OpenRouter") && (
                      <a
                        href="https://openrouter.ai/keys"
                        target="_blank"
                        rel="noreferrer"
                        style={{ fontSize: "0.74rem", color: "#a855f7", textDecoration: "none", display: "flex", alignItems: "center", gap: "3px" }}
                      >
                        <span>Crear clave gratis (sin tarjeta)</span>
                        <ExternalLink size={11} />
                      </a>
                    )}
                    {formData.provider.includes("Gemini") && (
                      <a
                        href="https://aistudio.google.com/apikey"
                        target="_blank"
                        rel="noreferrer"
                        style={{ fontSize: "0.74rem", color: "var(--accent)", textDecoration: "none", display: "flex", alignItems: "center", gap: "3px" }}
                      >
                        <span>Obtener clave Google gratis</span>
                        <ExternalLink size={11} />
                      </a>
                    )}
                    {formData.provider.includes("DeepSeek") && (
                      <a
                        href="https://platform.deepseek.com"
                        target="_blank"
                        rel="noreferrer"
                        style={{ fontSize: "0.74rem", color: "#38bdf8", textDecoration: "none", display: "flex", alignItems: "center", gap: "3px" }}
                      >
                        <span>Consola DeepSeek Oficial</span>
                        <ExternalLink size={11} />
                      </a>
                    )}
                  </div>
                  <div style={{ position: "relative" }}>
                    <input
                      type={showApiKey ? "text" : "password"}
                      value={formData.apiKey}
                      onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                      placeholder={formData.provider.includes("OpenRouter") ? "sk-or-v1-..." : "sk-..."}
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
              )}

              {/* Botón de Auto-Detección Inteligente */}
              <div>
                <button
                  type="button"
                  onClick={handleDetectModels}
                  disabled={detectingModels}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                    width: "100%",
                    padding: "10px 14px",
                    background: "linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(168, 85, 247, 0.18) 100%)",
                    border: "1px solid rgba(168, 85, 247, 0.4)",
                    borderRadius: "8px",
                    color: "#c084fc",
                    fontWeight: "600",
                    fontSize: "0.84rem",
                    cursor: detectingModels ? "not-allowed" : "pointer",
                    transition: "all 0.2s ease",
                  }}
                >
                  {detectingModels ? (
                    <>
                      <RefreshCw size={15} style={{ animation: "spin 1s linear infinite" }} />
                      <span>Detectando plan y modelos de tu cuenta en tiempo real...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} />
                      <span>✨ Detectar modelos y plan de mi cuenta</span>
                    </>
                  )}
                </button>

                {detectionError && (
                  <div style={{ marginTop: "6px", padding: "8px 10px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "6px", fontSize: "0.76rem", color: "#f87171" }}>
                    ⚠️ {detectionError}
                  </div>
                )}
              </div>

              {/* Resultado de la Detección */}
              {detectedData && (
                <div style={{ background: "rgba(255, 255, 255, 0.03)", border: "1px solid var(--border)", borderRadius: "8px", padding: "12px", display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <ShieldCheck size={16} color={detectedData.plan_info?.is_free_tier ? "#10b981" : "#a855f7"} />
                      <span style={{ fontSize: "0.82rem", fontWeight: "700", color: detectedData.plan_info?.is_free_tier ? "#10b981" : "#c084fc" }}>
                        {detectedData.plan_info?.name || "Cuenta Activa"}
                      </span>
                    </div>
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                      {detectedData.models?.length || 0} modelos disponibles
                    </span>
                  </div>

                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {detectedData.plan_info?.description}
                  </div>

                  {/* Listado de modelos detectados */}
                  {detectedData.models && detectedData.models.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "180px", overflowY: "auto", paddingRight: "4px" }}>
                      {detectedData.models.map((m) => {
                        const isSelected = formData.modelName === m.id;
                        return (
                          <div
                            key={m.id}
                            onClick={() => setFormData({ ...formData, modelName: m.id })}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              padding: "6px 10px",
                              borderRadius: "6px",
                              background: isSelected ? "var(--accent-light)" : "var(--bg-base)",
                              border: isSelected ? "1px solid var(--accent)" : "1px solid var(--border)",
                              cursor: "pointer",
                              transition: "all 0.15s ease",
                            }}
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              {isSelected ? <CheckCircle2 size={14} color="var(--accent)" /> : <Zap size={14} color="var(--text-muted)" />}
                              <div>
                                <div style={{ fontSize: "0.78rem", fontWeight: isSelected ? "700" : "500", color: isSelected ? "var(--accent)" : "var(--text)" }}>
                                  {m.name}
                                </div>
                                <div style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>{m.id}</div>
                              </div>
                            </div>
                            <span
                              style={{
                                fontSize: "0.65rem",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                background: m.is_free ? "rgba(16, 185, 129, 0.15)" : "rgba(168, 85, 247, 0.15)",
                                color: m.is_free ? "#34d399" : "#c084fc",
                                fontWeight: "600",
                              }}
                            >
                              {m.is_free ? "GRATIS" : "AVANZADO"}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Modelo Seleccionado */}
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "500" }}>
                  Modelo Seleccionado para Respuestas:
                </label>
                <input
                  type="text"
                  value={formData.modelName}
                  onChange={(e) => setFormData({ ...formData, modelName: e.target.value })}
                  placeholder="ej: deepseek/deepseek-r1:free, qwen2.5:14b, gemini-2.0-flash"
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

                {formData.provider === "Ollama (Local)" && !detectedData && (
                  <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "0.74rem", color: "var(--text-muted)" }}>Modelos comunes en PC:</span>
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
