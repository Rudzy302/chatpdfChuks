import React, { useState, useEffect, useRef } from "react";
import { Play, Pause, RotateCcw, X, Volume2, SkipForward, SkipBack, Headphones } from "lucide-react";

export default function AudioReaderModal({ storyboard, onClose }) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1.0);
  const utteranceRef = useRef(null);

  const sections = storyboard?.scenes || [];
  const currentSection = sections[currentIdx] || {};

  const speakCurrent = (index) => {
    if (!window.speechSynthesis) {
      alert("Tu navegador no soporta síntesis de voz.");
      return;
    }

    window.speechSynthesis.cancel();
    const item = sections[index];
    if (!item) {
      setIsPlaying(false);
      return;
    }

    const textToSpeak = `${item.title ? item.title + '. ' : ''}${item.narration || ''}`;
    const cleanText = textToSpeak.replace(/\[(?:Pág\.|Página|Pag\.)\s*\d+\]/gi, "");

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = "es-ES";
    utterance.rate = speed;

    utterance.onend = () => {
      if (index < sections.length - 1) {
        setCurrentIdx(index + 1);
        speakCurrent(index + 1);
      } else {
        setIsPlaying(false);
        setCurrentIdx(0);
      }
    };

    utterance.onerror = () => {
      setIsPlaying(false);
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
    setIsPlaying(true);
  };

  const togglePlay = () => {
    if (isPlaying) {
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      setIsPlaying(false);
    } else {
      speakCurrent(currentIdx);
    }
  };

  const handleNext = () => {
    if (currentIdx < sections.length - 1) {
      const nextIdx = currentIdx + 1;
      setCurrentIdx(nextIdx);
      if (isPlaying) speakCurrent(nextIdx);
    }
  };

  const handlePrev = () => {
    if (currentIdx > 0) {
      const prevIdx = currentIdx - 1;
      setCurrentIdx(prevIdx);
      if (isPlaying) speakCurrent(prevIdx);
    }
  };

  const handleRestart = () => {
    setCurrentIdx(0);
    if (isPlaying) {
      speakCurrent(0);
    }
  };

  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        background: "rgba(0,0,0,0.8)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
    >
      <div
        style={{
          width: "560px",
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "14px",
          overflow: "hidden",
          boxShadow: "0 24px 48px rgba(0,0,0,0.6)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: "700", color: "var(--text)" }}>
            <Headphones size={18} color="var(--accent)" />
            <span>Lector de Audio Documental: {storyboard?.title || "Resumen de Voz"}</span>
          </div>
          <button onClick={() => { if (window.speechSynthesis) window.speechSynthesis.cancel(); onClose(); }} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}>
            <X size={18} />
          </button>
        </div>

        {/* Player Stage */}
        <div
          style={{
            padding: "30px 24px",
            background: "linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
            minHeight: "220px",
            justifyContent: "center",
          }}
        >
          {/* Badge Sección */}
          <div
            style={{
              background: "rgba(14, 165, 233, 0.15)",
              border: "1px solid rgba(14, 165, 233, 0.3)",
              padding: "4px 12px",
              borderRadius: "20px",
              fontSize: "0.78rem",
              color: "var(--accent)",
              fontWeight: "600",
              marginBottom: "14px",
            }}
          >
            Sección {currentIdx + 1} de {sections.length}: {currentSection.title || "Tópico"}
          </div>

          <h3 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#ffffff", marginBottom: "14px" }}>
            {currentSection.title}
          </h3>

          <p style={{ fontSize: "1rem", color: "#cbd5e1", lineHeight: "1.6", maxWidth: "90%", fontStyle: "italic" }}>
            "{currentSection.narration}"
          </p>

          {/* Animación de ondas sonoras si está activo */}
          {isPlaying && (
            <div style={{ display: "flex", gap: "4px", alignItems: "center", marginTop: "18px" }}>
              <div style={{ width: "3px", height: "16px", background: "var(--accent)", borderRadius: "2px", animation: "bounce 0.8s infinite ease-in-out" }} />
              <div style={{ width: "3px", height: "24px", background: "var(--accent)", borderRadius: "2px", animation: "bounce 0.8s infinite ease-in-out 0.2s" }} />
              <div style={{ width: "3px", height: "12px", background: "var(--accent)", borderRadius: "2px", animation: "bounce 0.8s infinite ease-in-out 0.4s" }} />
              <div style={{ width: "3px", height: "20px", background: "var(--accent)", borderRadius: "2px", animation: "bounce 0.8s infinite ease-in-out 0.1s" }} />
            </div>
          )}
        </div>

        {/* Barra de progreso */}
        <div style={{ display: "flex", height: "4px", background: "var(--border)" }}>
          {sections.map((_, idx) => (
            <div
              key={idx}
              style={{
                flex: 1,
                background: idx === currentIdx ? "var(--accent)" : idx < currentIdx ? "var(--accent-light, #38bdf8)" : "transparent",
                transition: "background 0.3s ease",
              }}
            />
          ))}
        </div>

        {/* Controles de Reproducción */}
        <div style={{ padding: "14px 18px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg-base)", flexWrap: "wrap", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={handlePrev}
              disabled={currentIdx === 0}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: currentIdx === 0 ? "var(--text-muted)" : "var(--text)",
                padding: "8px 10px",
                borderRadius: "6px",
                cursor: currentIdx === 0 ? "not-allowed" : "pointer",
              }}
              title="Sección anterior"
            >
              <SkipBack size={15} />
            </button>

            <button
              onClick={togglePlay}
              style={{
                background: "var(--accent)",
                border: "none",
                color: "#ffffff",
                padding: "8px 16px",
                borderRadius: "6px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontWeight: "600",
                fontSize: "0.85rem",
              }}
            >
              {isPlaying ? <Pause size={15} /> : <Play size={15} />}
              {isPlaying ? "Pausar" : "Escuchar Audio"}
            </button>

            <button
              onClick={handleNext}
              disabled={currentIdx === sections.length - 1}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: currentIdx === sections.length - 1 ? "var(--text-muted)" : "var(--text)",
                padding: "8px 10px",
                borderRadius: "6px",
                cursor: currentIdx === sections.length - 1 ? "not-allowed" : "pointer",
              }}
              title="Siguiente sección"
            >
              <SkipForward size={15} />
            </button>

            <button
              onClick={handleRestart}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text)",
                padding: "8px 10px",
                borderRadius: "6px",
                cursor: "pointer",
              }}
              title="Reiniciar desde el inicio"
            >
              <RotateCcw size={15} />
            </button>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Velocidad:</span>
            <select
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text)",
                padding: "5px 8px",
                borderRadius: "6px",
                fontSize: "0.78rem",
                cursor: "pointer",
              }}
            >
              <option value={0.85}>0.85x</option>
              <option value={1.0}>1.0x</option>
              <option value={1.2}>1.2x</option>
              <option value={1.5}>1.5x</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
