import React, { useState, useEffect, useRef } from "react";
import { Send, Settings, Sparkles, Volume2, VolumeX, Mic, MicOff, Film, Headphones } from "lucide-react";

export default function ChatView({
  messages = [],
  onSendMessage,
  onNavigateToPage,
  sending = false,
  aiSettings,
  onUpdateAiSettings,
  suggestedQuestions = [],
  onGenerateVideo,
  onOpenAudioReader,
  activeDoc = "",
}) {
  const [input, setInput] = useState("");
  const [showConfig, setShowConfig] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const recognitionRef = useRef(null);

  // Inicializar Speech Recognition (Reconocimiento por Micrófono)
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.lang = "es-ES";
      recognition.interimResults = false;

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput((prev) => (prev ? prev + " " + transcript : transcript));
        setIsListening(false);
      };

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("El reconocimiento de voz no está soportado en este navegador.");
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.error(err);
      }
    }
  };

  // Lector de voz (Text-to-Speech)
  const handleSpeak = (text, idx) => {
    if (!window.speechSynthesis) {
      alert("El sintetizador de voz no está soportado.");
      return;
    }

    if (speakingIndex === idx) {
      window.speechSynthesis.cancel();
      setSpeakingIndex(null);
      return;
    }

    window.speechSynthesis.cancel();
    // Limpiar etiquetas como [Pág. X] para que la lectura sea fluida
    const cleanSpeechText = text.replace(/\[(?:Pág\.|Página|Imagen en Pág\.)\s*\d+\]/gi, "");
    const utterance = new SpeechSynthesisUtterance(cleanSpeechText);
    utterance.lang = "es-ES";
    utterance.rate = 1.05;

    utterance.onend = () => setSpeakingIndex(null);
    utterance.onerror = () => setSpeakingIndex(null);

    setSpeakingIndex(idx);
    window.speechSynthesis.speak(utterance);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || sending) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const renderMessageContent = (text, isUser) => {
    if (isUser || !text) return text;
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
          onClick={() => onNavigateToPage && onNavigateToPage(pageNum, text)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "2px",
            background: "rgba(14, 165, 233, 0.12)",
            border: "1px solid rgba(14, 165, 233, 0.4)",
            color: "var(--accent)",
            padding: "1px 7px",
            borderRadius: "10px",
            fontSize: "0.78rem",
            fontWeight: "600",
            cursor: "pointer",
            margin: "0 3px",
            verticalAlign: "middle",
            transition: "all 0.15s ease",
          }}
          title={`Ir a Página ${pageNum} en el visor continuo`}
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
                {renderMessageContent(m.content, isUser)}
              </div>

              {/* Acciones del mensaje del asistente: Lector de Audio y Citas con círculos numerados */}
              {!isUser && (
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "6px" }}>
                  {/* Botón Lector TTS */}
                  <button
                    onClick={() => handleSpeak(m.content, idx)}
                    title={speakingIndex === idx ? "Detener lectura" : "Escuchar respuesta con voz natural"}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: speakingIndex === idx ? "var(--accent)" : "var(--text-muted)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      fontSize: "0.75rem",
                      padding: "2px 6px",
                    }}
                  >
                    {speakingIndex === idx ? <VolumeX size={14} color="#f87171" /> : <Volume2 size={14} />}
                    <span>{speakingIndex === idx ? "Detener" : "Escuchar"}</span>
                  </button>

                  {/* 5. Citas con círculo y número de orden exacto */}
                  {m.citations && m.citations.length > 0 && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Fuente:</span>
                      {m.citations.map((pNum, cIdx) => (
                        <div
                          key={cIdx}
                          onClick={() => onNavigateToPage(pNum, m.target_content || m.content)}
                          className="citation-bubble"
                          title={`Ver cita ${cIdx + 1} en Página ${pNum} (clic para resaltar unicamente este fragmento)`}
                        >
                          {cIdx + 1}
                        </div>
                      ))}
                    </div>
                  )}
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

      {/* 4. Preguntas sugeridas de seguimiento para continuar la conversación */}
      {suggestedQuestions && suggestedQuestions.length > 0 && (
        <div style={{ padding: "0 20px 8px 20px", display: "flex", gap: "6px", flexWrap: "wrap" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
            <Sparkles size={12} color="var(--accent)" /> Sugerencias:
          </span>
          {suggestedQuestions.map((q, qIdx) => (
            <button
              key={qIdx}
              onClick={() => onSendMessage(q)}
              disabled={sending}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text)",
                padding: "3px 10px",
                borderRadius: "14px",
                fontSize: "0.75rem",
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "border-color 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Drawer de Configuración de Modelo / Chunks */}
      <div style={{ padding: "0 20px 10px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
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
            }}
          >
            <Settings size={13} />
            {showConfig ? "Ocultar Parámetros de Inferencia" : "⚙️ Parámetros de Modelo, Chunks y Vectores"}
          </button>

          {/* Botón de Lector de Audio Documental */}
          {activeDoc && activeDoc !== "Todos los documentos" && (onOpenAudioReader || onGenerateVideo) && (
            <button
              onClick={onOpenAudioReader || onGenerateVideo}
              style={{
                background: "rgba(14, 165, 233, 0.12)",
                border: "1px solid rgba(14, 165, 233, 0.35)",
                color: "var(--accent)",
                fontSize: "0.78rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "4px 10px",
                borderRadius: "5px",
                cursor: "pointer",
                fontWeight: "500",
                transition: "all 0.15s ease",
              }}
              title="Escuchar audio narración completa del documento"
            >
              <Headphones size={14} />
              <span>Lector de Audio Documental</span>
            </button>
          )}
        </div>

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
              <label style={{ display: "block", color: "var(--text-muted)", marginBottom: "4px" }}>Motor de Inferencia:</label>
              <select
                value={aiSettings.provider}
                onChange={(e) => onUpdateAiSettings({ ...aiSettings, provider: e.target.value })}
                style={{ width: "100%", background: "var(--bg-base)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px", borderRadius: "4px" }}
              >
                <option value="Llama.cpp Server (Local)">Llama.cpp Server (Local CUDA :8080)</option>
                <option value="Ollama (Local)">Ollama (Local :11434)</option>
                <option value="Google Gemini (Nube)">Google Gemini (Nube)</option>
                <option value="OpenAI / Groq API (Nube)">OpenAI / Groq API (Nube)</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", color: "var(--text-muted)", marginBottom: "4px" }}>Modelo / Checkpoint:</label>
              <input
                type="text"
                value={aiSettings.modelName}
                onChange={(e) => onUpdateAiSettings({ ...aiSettings, modelName: e.target.value })}
                placeholder="qwen2.5:7b, llava:7b..."
                style={{ width: "100%", background: "var(--bg-base)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px", borderRadius: "4px" }}
              />
            </div>

            {aiSettings.provider.includes("Nube") && (
              <div>
                <label style={{ display: "block", color: "var(--text-muted)", marginBottom: "4px" }}>API Key:</label>
                <input
                  type="password"
                  value={aiSettings.apiKey}
                  onChange={(e) => onUpdateAiSettings({ ...aiSettings, apiKey: e.target.value })}
                  placeholder="AIzaSy... / gsk_..."
                  style={{ width: "100%", background: "var(--bg-base)", border: "1px solid var(--border)", color: "var(--text)", padding: "6px", borderRadius: "4px" }}
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

        {/* Input Form con Micrófono y Reconocimiento de Voz */}
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "8px" }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isListening ? "Escuchando tu voz por el micrófono..." : "Escribe tu consulta o usa el micrófono..."}
            disabled={sending}
            style={{
              flex: 1,
              background: "var(--bg-card)",
              border: isListening ? "1px solid #ef4444" : "1px solid var(--border)",
              borderRadius: "8px",
              padding: "12px 16px",
              color: "var(--text)",
              fontSize: "0.9rem",
              outline: "none",
            }}
          />

          {/* Botón de Micrófono (Audio Recognition) */}
          <button
            type="button"
            onClick={toggleListening}
            title={isListening ? "Detener grabación" : "Dictar consulta con tu voz"}
            style={{
              background: isListening ? "#ef4444" : "var(--bg-card)",
              border: "1px solid " + (isListening ? "#ef4444" : "var(--border)"),
              color: isListening ? "#ffffff" : "var(--text)",
              borderRadius: "8px",
              padding: "0 14px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "background 0.2s ease",
            }}
          >
            {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          </button>

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
