import React, { useState, useEffect, useRef } from "react";
import { Send, Sparkles, Volume2, VolumeX, Mic, MicOff, Headphones, Download, Film } from "lucide-react";

export default function ChatView({
  messages = [],
  onSendMessage,
  onNavigateToPage,
  onHoverCitation,
  sending = false,
  aiSettings = {},
  suggestedQuestions = [],
  onOpenAudioReader,
  activeDoc = "",
}) {
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const [currentWordCharIndex, setCurrentWordCharIndex] = useState(-1);
  const recognitionRef = useRef(null);

  // Inicializar Speech Recognition
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

      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);

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

  // Lector de voz (Text-to-Speech con Karaoke de palabras iluminadas)
  const handleSpeak = (text, idx) => {
    if (!window.speechSynthesis) {
      alert("El sintetizador de voz no está soportado.");
      return;
    }

    if (speakingIndex === idx) {
      window.speechSynthesis.cancel();
      setSpeakingIndex(null);
      setCurrentWordCharIndex(-1);
      return;
    }

    window.speechSynthesis.cancel();
    setCurrentWordCharIndex(-1);

    // Limpiar citas [Pág. X] para no deletrearlas al hablar
    const cleanSpeechText = text.replace(/\[(?:Pág\.|Página|Pag\.)\s*\d+\]/gi, "");
    const utterance = new SpeechSynthesisUtterance(cleanSpeechText);
    utterance.lang = "es-ES";
    utterance.rate = aiSettings?.voiceSpeed || 1.05;

    // Evento onboundary para iluminar la palabra actual (Efecto Karaoke)
    utterance.onboundary = (event) => {
      if (event.name === "word") {
        setCurrentWordCharIndex(event.charIndex);
      }
    };

    utterance.onend = () => {
      setSpeakingIndex(null);
      setCurrentWordCharIndex(-1);
    };

    utterance.onerror = () => {
      setSpeakingIndex(null);
      setCurrentWordCharIndex(-1);
    };

    setSpeakingIndex(idx);
    window.speechSynthesis.speak(utterance);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || sending) return;
    onSendMessage(input.trim());
    setInput("");
  };

  // Renderizador de contenido con citas interactivas y efecto Karaoke
  const renderMessageContent = (text, isUser, msgIdx) => {
    if (isUser || !text) return text;

    const isSpeakingThis = speakingIndex === msgIdx && currentWordCharIndex >= 0 && (aiSettings?.karaokeEnabled !== false);

    // Segmentar el texto identificando citas [Pág. X]
    const regex = /\[(?:Pág\.|Página|Pag\.)\s*(\d+)\]/gi;
    const segments = [];
    let lastIdx = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      const pageNum = parseInt(match[1], 10);
      if (match.index > lastIdx) {
        segments.push({ type: "text", content: text.substring(lastIdx, match.index), charStart: lastIdx });
      }
      segments.push({ type: "citation", page: pageNum, raw: match[0] });
      lastIdx = regex.lastIndex;
    }

    if (lastIdx < text.length) {
      segments.push({ type: "text", content: text.substring(lastIdx), charStart: lastIdx });
    }

    return segments.map((seg, sIdx) => {
      if (seg.type === "citation") {
        return (
          <button
            key={sIdx}
            onClick={() => onNavigateToPage && onNavigateToPage(seg.page, text)}
            onMouseEnter={() => onHoverCitation && onHoverCitation(seg.page, text)}
            onMouseLeave={() => onHoverCitation && onHoverCitation(null)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "3px",
              background: "rgba(14, 165, 233, 0.14)",
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
            title={`Pasa el cursor para ver la cita; haz clic para saltar a la Página ${seg.page}`}
          >
            📄 Pág. {seg.page}
          </button>
        );
      }

      // Si no es un mensaje que se esté hablando actualmente, renderizar texto plano
      if (!isSpeakingThis) {
        return <span key={sIdx}>{seg.content}</span>;
      }

      // Si se está hablando: renderizar con efecto Karaoke
      const words = seg.content.split(/(\s+)/);
      let runningCharOffset = seg.charStart;

      return (
        <span key={sIdx}>
          {words.map((w, wIdx) => {
            const wStart = runningCharOffset;
            const wEnd = runningCharOffset + w.length;
            runningCharOffset = wEnd;

            // Determinar cercanía con la palabra actual hablada
            const isCurrent = currentWordCharIndex >= wStart && currentWordCharIndex <= wEnd && w.trim().length > 0;
            const diff = currentWordCharIndex - wStart;
            const isRecentTrail = diff > 0 && diff < 35 && w.trim().length > 0;

            if (isCurrent) {
              return (
                <span
                  key={wIdx}
                  style={{
                    color: "#ffffff",
                    background: "var(--accent)",
                    boxShadow: "0 0 12px var(--accent)",
                    borderRadius: "3px",
                    padding: "0 4px",
                    fontWeight: "700",
                    transition: "all 0.1s ease",
                  }}
                >
                  {w}
                </span>
              );
            }

            if (isRecentTrail) {
              return (
                <span
                  key={wIdx}
                  style={{
                    color: "var(--accent)",
                    background: "rgba(14, 165, 233, 0.15)",
                    borderRadius: "3px",
                    transition: "all 0.2s ease",
                  }}
                >
                  {w}
                </span>
              );
            }

            return <span key={wIdx}>{w}</span>;
          })}
        </span>
      );
    });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", overflow: "hidden", background: "var(--bg-base)" }}>
      {/* Header bar de la conversación */}
      <div style={{ height: "42px", padding: "0 16px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg-card)", borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontSize: "0.85rem", fontWeight: "600", color: "var(--text)", display: "flex", alignItems: "center", gap: "6px" }}>
          <span>💬 Conversación Asistida</span>
          {activeDoc && activeDoc !== "Todos los documentos" && (
            <span style={{ fontSize: "0.75rem", color: "var(--accent)", opacity: 0.85 }}>• {activeDoc}</span>
          )}
        </div>

        {activeDoc && activeDoc !== "Todos los documentos" && onOpenAudioReader && (
          <button
            onClick={onOpenAudioReader}
            style={{
              background: "rgba(14, 165, 233, 0.12)",
              border: "1px solid rgba(14, 165, 233, 0.35)",
              color: "var(--accent)",
              fontSize: "0.76rem",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              borderRadius: "5px",
              cursor: "pointer",
              fontWeight: "500",
              transition: "all 0.15s ease",
            }}
            title="Escuchar audio resumen estructurado del documento"
          >
            <Headphones size={13} />
            <span>Lector de Audio Documental</span>
          </button>
        )}
      </div>

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
                  lineHeight: "1.6",
                  whiteSpace: "pre-wrap",
                }}
              >
                {renderMessageContent(m.content, isUser, idx)}

                {/* Reproductor de Video Integrado si el mensaje generó video */}
                {m.video_url && (
                  <div style={{ marginTop: "12px", borderRadius: "8px", overflow: "hidden", border: "1px solid var(--border)", background: "#050505" }}>
                    <video
                      src={m.video_url}
                      controls
                      autoPlay
                      loop
                      style={{ width: "100%", maxHeight: "320px", display: "block", objectFit: "contain" }}
                    />
                    <div style={{ padding: "8px 12px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--bg-base)", fontSize: "0.78rem" }}>
                      <span style={{ color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "5px" }}>
                        <Film size={13} color="var(--accent)" /> Video Generado por IA
                      </span>
                      <a
                        href={m.video_url}
                        download
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "var(--accent)", textDecoration: "none", fontWeight: "600", display: "flex", alignItems: "center", gap: "4px" }}
                      >
                        <Download size={13} />
                        Descargar MP4
                      </a>
                    </div>
                  </div>
                )}
              </div>

              {/* Acciones del mensaje del asistente: Lector con Karaoke y Círculos Clickeables/Hover */}
              {!isUser && (
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "6px" }}>
                  {/* Botón Lector TTS */}
                  <button
                    onClick={() => handleSpeak(m.content, idx)}
                    title={speakingIndex === idx ? "Detener lectura" : "Escuchar con voz y seguimiento de lectura iluminada"}
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

                  {/* Citas sincronizadas con Hover y Clic */}
                  {m.citations && m.citations.length > 0 && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Fuente:</span>
                      {m.citations.map((pNum, cIdx) => (
                        <div
                          key={cIdx}
                          onClick={() => onNavigateToPage(pNum, m.target_content || m.content)}
                          onMouseEnter={() => onHoverCitation && onHoverCitation(pNum, m.target_content || m.content)}
                          onMouseLeave={() => onHoverCitation && onHoverCitation(null)}
                          className="citation-bubble"
                          style={{ cursor: "pointer", transition: "transform 0.15s ease, box-shadow 0.15s ease" }}
                          title={`Hover: Resalta en visor | Clic: Abre Página ${pNum}`}
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
          <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontStyle: "italic", display: "flex", alignItems: "center", gap: "6px" }}>
            <Sparkles size={14} className="animate-spin" color="var(--accent)" />
            <span>Consultando información y citando fuentes...</span>
          </div>
        )}
      </div>

      {/* Preguntas sugeridas de seguimiento dinámicas */}
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

      {/* Input Form con Micrófono y Reconocimiento de Voz */}
      <div style={{ padding: "0 20px 16px 20px" }}>
        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "8px" }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isListening ? "Escuchando tu voz por el micrófono..." : "Pregunta sobre el documento o escribe 'genera un video de...'"}
            disabled={sending}
            style={{
              flex: 1,
              padding: "10px 14px",
              borderRadius: "8px",
              background: "var(--bg-card)",
              border: isListening ? "1px solid #ef4444" : "1px solid var(--border)",
              color: "var(--text)",
              fontSize: "0.9rem",
              outline: "none",
            }}
          />

          <button
            type="button"
            onClick={toggleListening}
            style={{
              padding: "0 12px",
              borderRadius: "8px",
              background: isListening ? "rgba(239, 68, 68, 0.2)" : "var(--bg-card)",
              border: `1px solid ${isListening ? "#ef4444" : "var(--border)"}`,
              color: isListening ? "#ef4444" : "var(--text-muted)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            title={isListening ? "Detener micrófono" : "Dictar consulta por voz"}
          >
            {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          </button>

          <button
            type="submit"
            disabled={!input.trim() || sending}
            style={{
              padding: "0 16px",
              borderRadius: "8px",
              background: "var(--accent)",
              border: "none",
              color: "#ffffff",
              cursor: !input.trim() || sending ? "not-allowed" : "pointer",
              opacity: !input.trim() || sending ? 0.6 : 1,
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
