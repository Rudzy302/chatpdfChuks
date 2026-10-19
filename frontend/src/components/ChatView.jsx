import React, { useState } from "react";
import { Send, Settings, Sparkles, MapPin } from "lucide-react";

export default function ChatView({
  messages = [],
  onSendMessage,
  onNavigateToPage,
  sending = false,
  aiSettings,
  onUpdateAiSettings,
}) {
  const [input, setInput] = useState("");
  const [showConfig, setShowConfig] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || sending) return;
    onSendMessage(input.trim());
    setInput("");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", overflow: "hidden", background: "var(--bg-base)" }}>
      {/* Feed de Mensajes */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
        {messages.map((m, idx) => {
          const isUser = m.role === "user";
          return (
            <div
              key={idx}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: isUser ? "flex-end" : "flex-start",
              }}
            >
              <div
                style={{
                  maxWidth: "85%",
                  padding: "12px 16px",
                  borderRadius: "10px",
                  background: isUser ? "var(--accent)" : "var(--bg-card)",
                  color: isUser ? "#ffffff" : "var(--text)",
                  border: isUser ? "none" : "1px solid var(--border)",
                  fontSize: "0.9rem",
                  lineHeight: "1.5",
                  whiteSpace: "pre-wrap",
                }}
              >
                {m.content}
              </div>

              {/* Botones de salto a página si el asistente incluye citas */}
              {!isUser && m.citations && m.citations.length > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "6px" }}>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Ir a la fuente:</span>
                  {m.citations.map((pNum) => (
                    <button
                      key={pNum}
                      onClick={() => onNavigateToPage(pNum, m.content)}
                      style={{
                        background: "var(--bg-card)",
                        border: "1px solid var(--border)",
                        color: "var(--accent)",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "0.75rem",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      <MapPin size={11} />
                      Pág. {pNum}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {sending && (
          <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontStyle: "italic" }}>
            Consultando información y citando fuentes...
          </div>
        )}
      </div>

      {/* Drawer de Configuración de Modelo / Chunks (Estilo ChatGPT) */}
      <div style={{ padding: "0 20px 10px 20px" }}>
        <button
          onClick={() => setShowConfig(!showConfig)}
          style={{
            background: "transparent",
            border: "none",
            color: "var(--text-muted)",
            fontSize: "0.75rem",
            display: "flex",
            alignItems: "center",
            gap: "5px",
            cursor: "pointer",
            marginBottom: "8px",
          }}
        >
          <Settings size={13} />
          {showConfig ? "Ocultar Parámetros de Inferencia" : "⚙️ Parámetros de Modelo, Chunks y Vectores"}
        </button>

        {showConfig && (
          <div
            style={{
              padding: "14px",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              marginBottom: "12px",
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "12px",
              fontSize: "0.8rem",
            }}
          >
            <div>
              <label style={{ display: "block", color: "var(--text-muted)", marginBottom: "4px" }}>Motor:</label>
              <select
                value={aiSettings.provider}
                onChange={(e) => onUpdateAiSettings({ ...aiSettings, provider: e.target.value })}
                style={{ width: "100%", background: "var(--bg-base)", border: "1px solid var(--border)", color: "var(--text)", padding: "4px", borderRadius: "4px" }}
              >
                <option value="Llama.cpp Server (Local)">Llama.cpp Server (Local)</option>
                <option value="Ollama (Local)">Ollama (Local)</option>
                <option value="Google Gemini (Nube)">Google Gemini (Nube)</option>
                <option value="OpenAI / Groq API (Nube)">OpenAI / Groq API (Nube)</option>
              </select>
            </div>

            {aiSettings.provider.includes("Gemini") || aiSettings.provider.includes("OpenAI") ? (
              <div>
                <label style={{ display: "block", color: "var(--text-muted)", marginBottom: "4px" }}>API Key:</label>
                <input
                  type="password"
                  value={aiSettings.apiKey}
                  onChange={(e) => onUpdateAiSettings({ ...aiSettings, apiKey: e.target.value })}
                  placeholder="Tu clave de API..."
                  style={{ width: "100%", background: "var(--bg-base)", border: "1px solid var(--border)", color: "var(--text)", padding: "4px", borderRadius: "4px" }}
                />
              </div>
            ) : (
              <div>
                <label style={{ display: "block", color: "var(--text-muted)", marginBottom: "4px" }}>Modelo Local:</label>
                <input
                  type="text"
                  value={aiSettings.modelName}
                  onChange={(e) => onUpdateAiSettings({ ...aiSettings, modelName: e.target.value })}
                  placeholder="qwen2.5:7b / llama3"
                  style={{ width: "100%", background: "var(--bg-base)", border: "1px solid var(--border)", color: "var(--text)", padding: "4px", borderRadius: "4px" }}
                />
              </div>
            )}

            <div>
              <label style={{ display: "block", color: "var(--text-muted)", marginBottom: "4px" }}>Top Chunks (RAG): {aiSettings.topK}</label>
              <input
                type="range"
                min="2"
                max="10"
                value={aiSettings.topK}
                onChange={(e) => onUpdateAiSettings({ ...aiSettings, topK: parseInt(e.target.value) })}
                style={{ width: "100%", accentColor: "var(--accent)" }}
              />
            </div>
          </div>
        )}

        {/* Input Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "8px" }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Escribe tu consulta sobre el contenido, texto o imágenes del documento..."
            disabled={sending}
            style={{
              flex: 1,
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "12px 16px",
              color: "var(--text)",
              fontSize: "0.9rem",
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            style={{
              background: "var(--accent)",
              border: "none",
              color: "#ffffff",
              borderRadius: "8px",
              padding: "0 18px",
              cursor: sending || !input.trim() ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
