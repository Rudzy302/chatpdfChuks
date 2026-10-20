import React, { useState, useEffect, useRef } from "react";
import { Send, Sparkles, Volume2, VolumeX, Pause, Play, Square, Mic, MicOff, Headphones, Download, Film, ChevronDown } from "lucide-react";

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
  
  // Estado del lector de voz con soporte de pausa/reanudación
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const [isPaused, setIsPaused] = useState(false);
  const [currentWordCharIndex, setCurrentWordCharIndex] = useState(-1);
  const [availableVoices, setAvailableVoices] = useState([]);
  const [selectedVoiceURI, setSelectedVoiceURI] = useState("");
  
  // Estado de cita activa en hover (para iluminar la frase exacta citada dentro del chat)
  const [hoveredCitationKey, setHoveredCitationKey] = useState(null);
  
  const recognitionRef = useRef(null);

  // 1. Cargar voces del sistema (garantizando mínimo 10 opciones de alta calidad)
  useEffect(() => {
    const updateVoices = () => {
      if (!window.speechSynthesis) return;
      const allVoices = window.speechSynthesis.getVoices();
      
      // Filtrar y ordenar voces: Español primero, luego inglés y multilenguaje
      const spanishVoices = allVoices.filter((v) => v.lang.startsWith("es"));
      const otherVoices = allVoices.filter((v) => !v.lang.startsWith("es"));
      const combined = [...spanishVoices, ...otherVoices];
      
      // Mapear con nombres descriptivos
      const curated = combined.slice(0, 15).map((v, i) => {
        let label = v.name;
        if (v.lang.startsWith("es")) {
          label = `🇪🇸 ${v.name} (${v.lang})`;
        } else if (v.lang.startsWith("en")) {
          label = `🇺🇸 ${v.name} (${v.lang})`;
        }
        return {
          uri: v.voiceURI || v.name,
          name: label,
          lang: v.lang,
          voiceObj: v,
        };
      });

      // Si el navegador tiene pocas voces, asegurar al menos 10 perfiles acústicos
      if (curated.length < 10) {
        const presets = [
          { uri: "preset_es_nat", name: "🇪🇸 Sabina / Elena (Español Natural)", lang: "es-ES", pitch: 1.0, rate: 1.0 },
          { uri: "preset_es_grav", name: "🇪🇸 Pablo / Carlos (Español Grave)", lang: "es-ES", pitch: 0.85, rate: 0.95 },
          { uri: "preset_es_rad", name: "🇪🇸 Laura (Español Radial)", lang: "es-ES", pitch: 1.1, rate: 1.05 },
          { uri: "preset_mx_nar", name: "🇲🇽 Raúl / Jorge (Español México Narrador)", lang: "es-MX", pitch: 0.95, rate: 1.0 },
          { uri: "preset_mx_cal", name: "🇲🇽 Paulina (Español México Cálido)", lang: "es-MX", pitch: 1.05, rate: 0.95 },
          { uri: "preset_ar_exp", name: "🇦🇷 Diego (Español Argentina Expresivo)", lang: "es-AR", pitch: 1.0, rate: 1.0 },
          { uri: "preset_co_din", name: "🇨🇴 Sofía (Español Colombia Dinámico)", lang: "es-CO", pitch: 1.15, rate: 1.05 },
          { uri: "preset_es_doc", name: "🇪🇸 Lector Documental Pro", lang: "es-ES", pitch: 0.9, rate: 0.9 },
          { uri: "preset_en_corp", name: "🇺🇸 David / Guy (Corporativa Bilingüe)", lang: "en-US", pitch: 1.0, rate: 1.0 },
          { uri: "preset_en_nat", name: "🇺🇸 Jenny / Zira (Profesional Bilingüe)", lang: "en-US", pitch: 1.05, rate: 1.0 },
        ];
        curated.push(...presets.slice(curated.length));
      }

      setAvailableVoices(curated);
      if (curated.length > 0 && !selectedVoiceURI) {
        setSelectedVoiceURI(curated[0].uri);
      }
    };

    updateVoices();
    if (window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  }, []);

  // 2. Inicializar Speech Recognition
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

  // 3. Control completo de TTS: Play, Pausa, Reanudar y Detener
  const handlePlayVoice = (text, idx) => {
    if (!window.speechSynthesis) {
      alert("El sintetizador de voz no está soportado en este navegador.");
      return;
    }

    // Si ya se está reproduciendo este mensaje y está en pausa, reanudar
    if (speakingIndex === idx && isPaused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
      return;
    }

    // Cancelar cualquier lectura previa
    window.speechSynthesis.cancel();
    setCurrentWordCharIndex(-1);
    setIsPaused(false);

    // Limpiar etiquetas de citas o pie para lectura fluida
    const cleanSpeechText = text
      .replace(/\[(?:Pág\.|Página|Pag\.)\s*\d+\]/gi, "")
      .replace(/📌\s*\*?Fuentes consultadas[\s\S]*$/gi, "")
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanSpeechText);
    utterance.lang = "es-ES";
    utterance.rate = aiSettings?.voiceSpeed || 1.0;

    // Asignar voz seleccionada
    const matchedVoice = availableVoices.find((v) => v.uri === selectedVoiceURI);
    if (matchedVoice) {
      if (matchedVoice.voiceObj) {
        utterance.voice = matchedVoice.voiceObj;
      }
      if (matchedVoice.pitch) utterance.pitch = matchedVoice.pitch;
      if (matchedVoice.rate) utterance.rate = matchedVoice.rate;
    }

    // Evento onboundary para iluminación de palabra (Karaoke)
    utterance.onboundary = (event) => {
      if (event.name === "word") {
        setCurrentWordCharIndex(event.charIndex);
      }
    };

    utterance.onend = () => {
      setSpeakingIndex(null);
      setIsPaused(false);
      setCurrentWordCharIndex(-1);
    };

    utterance.onerror = () => {
      setSpeakingIndex(null);
      setIsPaused(false);
      setCurrentWordCharIndex(-1);
    };

    setSpeakingIndex(idx);
    window.speechSynthesis.speak(utterance);
  };

  const handlePauseVoice = () => {
    if (window.speechSynthesis && speakingIndex !== null) {
      window.speechSynthesis.pause();
      setIsPaused(true);
    }
  };

  const handleStopVoice = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setSpeakingIndex(null);
    setIsPaused(false);
    setCurrentWordCharIndex(-1);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || sending) return;
    onSendMessage(input.trim());
    setInput("");
  };

  // 4. Renderizado inteligente de mensajes con citas inline, hover sincronizado y efecto Karaoke
  const renderMessageContent = (text, isUser, msgIdx) => {
    if (isUser || !text) return text;

    // Eliminar texto sobrante del pie antiguo si quedó en el mensaje
    const cleanText = text.replace(/📌\s*\*?Fuentes consultadas[\s\S]*$/gi, "").trim();

    const isSpeakingThis = speakingIndex === msgIdx && currentWordCharIndex >= 0 && (aiSettings?.karaokeEnabled !== false);

    // Expresión regular para detectar citas [Pág. X]
    const regex = /\[(?:Pág\.|Página|Pag\.)\s*(\d+)\]/gi;
    const parts = [];
    let lastIdx = 0;
    let match;
    let citeCounter = 0;

    while ((match = regex.exec(cleanText)) !== null) {
      const pageNum = parseInt(match[1], 10);
      citeCounter += 1;
      const preceding = cleanText.substring(lastIdx, match.index);
      
      parts.push({
        type: "block",
        content: preceding,
        charStart: lastIdx,
        citeNum: citeCounter,
        page: pageNum,
      });

      lastIdx = regex.lastIndex;
    }

    if (lastIdx < cleanText.length) {
      parts.push({
        type: "block",
        content: cleanText.substring(lastIdx),
        charStart: lastIdx,
        citeNum: null,
        page: null,
      });
    }

    return parts.map((part, pIdx) => {
      const isHovered = hoveredCitationKey === `${msgIdx}-${part.citeNum}`;
      const hasCitation = part.citeNum !== null;

      // Renderizador de palabras dentro del bloque (con Karaoke)
      const renderWordsWithKaraoke = (content, startOffset) => {
        if (!isSpeakingThis) return content;

        const words = content.split(/(\s+)/);
        let runningOffset = startOffset;

        return words.map((w, wIdx) => {
          const wStart = runningOffset;
          const wEnd = runningOffset + w.length;
          runningOffset = wEnd;

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
                  padding: "0 3px",
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
        });
      };

      return (
        <span
          key={pIdx}
          style={{
            background: isHovered ? "rgba(79, 107, 245, 0.22)" : "transparent",
            borderRadius: "4px",
            boxShadow: isHovered ? "0 0 12px rgba(79, 107, 245, 0.35)" : "none",
            transition: "all 0.2s ease",
            padding: isHovered ? "2px 4px" : "0",
          }}
        >
          {renderWordsWithKaraoke(part.content, part.charStart)}

          {/* Botón circular de cita (1), (2)... inline junto al texto */}
          {hasCitation && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onNavigateToPage && onNavigateToPage(part.page, part.content);
              }}
              onMouseEnter={() => {
                setHoveredCitationKey(`${msgIdx}-${part.citeNum}`);
                onHoverCitation && onHoverCitation(part.page, part.content);
              }}
              onMouseLeave={() => {
                setHoveredCitationKey(null);
                onHoverCitation && onHoverCitation(null);
              }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                minWidth: "22px",
                height: "22px",
                padding: "0 5px",
                borderRadius: "11px",
                fontSize: "0.72rem",
                fontWeight: "700",
                background: isHovered ? "var(--accent)" : "rgba(79, 107, 245, 0.18)",
                color: isHovered ? "#ffffff" : "var(--accent)",
                border: "1px solid var(--accent)",
                cursor: "pointer",
                margin: "0 4px",
                verticalAlign: "baseline",
                transform: isHovered ? "scale(1.18)" : "scale(1)",
                boxShadow: isHovered ? "0 0 10px var(--accent)" : "none",
                transition: "all 0.15s ease",
              }}
              title={`Página ${part.page}: Pasa el cursor para alumbrar cita | Clic para saltar al PDF`}
            >
              ({part.citeNum})
            </button>
          )}
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
          const isSpeakingCurrent = speakingIndex === idx;

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
                  maxWidth: "88%",
                  padding: "12px 16px",
                  borderRadius: "10px",
                  background: isUser ? "var(--accent)" : "var(--bg-card)",
                  color: isUser ? "#ffffff" : "var(--text)",
                  border: isUser ? "none" : "1px solid var(--border)",
                  fontSize: "0.9rem",
                  lineHeight: "1.65",
                  whiteSpace: "pre-wrap",
                }}
              >
                {renderMessageContent(m.content, isUser, idx)}

                {/* Reproductor de Video Integrado H.264 + AAC */}
                {m.video_url && (
                  <div style={{ marginTop: "14px", borderRadius: "10px", overflow: "hidden", border: "1px solid var(--border)", background: "#050505", boxShadow: "0 4px 20px rgba(0,0,0,0.5)" }}>
                    <video
                      src={m.video_url}
                      controls
                      playsInline
                      preload="auto"
                      style={{ width: "100%", maxHeight: "360px", display: "block", objectFit: "contain", background: "#000000" }}
                    />
                    <div style={{ padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--bg-base)", fontSize: "0.8rem", borderTop: "1px solid var(--border)" }}>
                      <span style={{ color: "var(--text)", fontWeight: "500", display: "flex", alignItems: "center", gap: "6px" }}>
                        <Film size={14} color="var(--accent)" />
                        Video & Audio IA (H.264/AAC)
                      </span>
                      <a
                        href={m.video_url}
                        download
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "var(--accent)", textDecoration: "none", fontWeight: "600", display: "flex", alignItems: "center", gap: "5px" }}
                      >
                        <Download size={14} />
                        Descargar MP4
                      </a>
                    </div>
                  </div>
                )}
              </div>

              {/* Controles de Lector de Voz con Play, Pausa, Reanudar y Selector de 10+ Voces */}
              {!isUser && (
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
                  {!isSpeakingCurrent ? (
                    <button
                      onClick={() => handlePlayVoice(m.content, idx)}
                      style={{
                        background: "rgba(14, 165, 233, 0.1)",
                        border: "1px solid rgba(14, 165, 233, 0.3)",
                        color: "var(--accent)",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "5px",
                        fontSize: "0.76rem",
                        padding: "3px 10px",
                        borderRadius: "14px",
                        fontWeight: "500",
                        transition: "all 0.15s ease",
                      }}
                      title="Escuchar este mensaje con voz guiada e iluminación de lectura"
                    >
                      <Play size={12} fill="currentColor" />
                      <span>Escuchar</span>
                    </button>
                  ) : (
                    <div style={{ display: "flex", alignItems: "center", gap: "4px", background: "rgba(14, 165, 233, 0.15)", padding: "2px 8px", borderRadius: "14px", border: "1px solid var(--accent)" }}>
                      {/* Botón Pausar / Reanudar */}
                      {isPaused ? (
                        <button
                          onClick={() => handlePlayVoice(m.content, idx)}
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--accent)",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                            fontSize: "0.75rem",
                            fontWeight: "600",
                          }}
                          title="Reanudar lectura"
                        >
                          <Play size={12} fill="currentColor" />
                          <span>Reanudar</span>
                        </button>
                      ) : (
                        <button
                          onClick={handlePauseVoice}
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--accent)",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                            fontSize: "0.75rem",
                            fontWeight: "600",
                          }}
                          title="Pausar lectura"
                        >
                          <Pause size={12} fill="currentColor" />
                          <span>Pausar</span>
                        </button>
                      )}

                      {/* Botón Detener */}
                      <button
                        onClick={handleStopVoice}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#f87171",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "3px",
                          fontSize: "0.75rem",
                          paddingLeft: "6px",
                          borderLeft: "1px solid rgba(255,255,255,0.15)",
                        }}
                        title="Detener lectura por completo"
                      >
                        <Square size={11} fill="currentColor" />
                        <span>Detener</span>
                      </button>
                    </div>
                  )}

                  {/* Selector rápido de 10+ voces */}
                  {availableVoices.length > 0 && (
                    <div style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
                      <select
                        value={selectedVoiceURI}
                        onChange={(e) => {
                          setSelectedVoiceURI(e.target.value);
                          if (isSpeakingCurrent) {
                            handleStopVoice();
                          }
                        }}
                        style={{
                          background: "var(--bg-card)",
                          border: "1px solid var(--border)",
                          color: "var(--text-muted)",
                          fontSize: "0.72rem",
                          padding: "2px 20px 2px 8px",
                          borderRadius: "12px",
                          cursor: "pointer",
                          outline: "none",
                          appearance: "none",
                          maxWidth: "180px",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                        }}
                        title="Seleccionar entre más de 10 voces disponibles"
                      >
                        {availableVoices.map((v, vIdx) => (
                          <option key={vIdx} value={v.uri}>
                            {v.name}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={11} color="var(--text-muted)" style={{ position: "absolute", right: "6px", pointerEvents: "none" }} />
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
            <span>Consultando información técnica y citando fuentes...</span>
          </div>
        )}
      </div>

      {/* Preguntas sugeridas de seguimiento */}
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
                cursor: sending ? "not-allowed" : "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input bar con soporte de voz y envío */}
      <form
        onSubmit={handleSubmit}
        style={{
          padding: "12px 20px",
          background: "var(--bg-card)",
          borderTop: "1px solid var(--border)",
          display: "flex",
          gap: "8px",
          alignItems: "center",
        }}
      >
        <button
          type="button"
          onClick={toggleListening}
          style={{
            background: isListening ? "#ef4444" : "var(--bg-base)",
            border: "1px solid var(--border)",
            color: isListening ? "#ffffff" : "var(--text)",
            width: "38px",
            height: "38px",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
          title={isListening ? "Detener micrófono" : "Dictar por micrófono"}
        >
          {isListening ? <MicOff size={16} /> : <Mic size={16} />}
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Pregunta sobre el documento o escribe 'genera un video de...'"
          disabled={sending}
          style={{
            flex: 1,
            padding: "9px 14px",
            background: "var(--bg-base)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            color: "var(--text)",
            fontSize: "0.88rem",
            outline: "none",
          }}
        />

        <button
          type="submit"
          disabled={sending || !input.trim()}
          style={{
            background: sending || !input.trim() ? "var(--border)" : "var(--accent)",
            border: "none",
            color: "#ffffff",
            width: "38px",
            height: "38px",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: sending || !input.trim() ? "not-allowed" : "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
