import React, { useState } from "react";
import { Play, Pause, RotateCcw, X, Sparkles, Film } from "lucide-react";

export default function VideoModal({ storyboard, onClose }) {
  const [currentSceneIdx, setCurrentSceneIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = React.useRef(null);

  const scenes = storyboard?.scenes || [];
  const currentScene = scenes[currentSceneIdx] || {};

  React.useEffect(() => {
    if (isPlaying) {
      const dur = (currentScene.duration || 6) * 1000;
      timerRef.current = setTimeout(() => {
        if (currentSceneIdx < scenes.length - 1) {
          setCurrentSceneIdx((prev) => prev + 1);
        } else {
          setIsPlaying(false);
          setCurrentSceneIdx(0);
        }
      }, dur);
    }
    return () => clearTimeout(timerRef.current);
  }, [isPlaying, currentSceneIdx, scenes.length, currentScene.duration]);

  const togglePlay = () => {
    if (window.speechSynthesis) {
      if (!isPlaying) {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(currentScene.narration || "");
        utter.lang = "es-ES";
        window.speechSynthesis.speak(utter);
      } else {
        window.speechSynthesis.cancel();
      }
    }
    setIsPlaying(!isPlaying);
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        background: "rgba(0,0,0,0.85)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
    >
      <div
        style={{
          width: "550px",
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "14px",
          overflow: "hidden",
          boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: "700", color: "var(--text)" }}>
            <Film size={18} color="var(--accent)" />
            <span>{storyboard?.title || "Video Resumen con IA"}</span>
          </div>
          <button onClick={onClose} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}>
            <X size={18} />
          </button>
        </div>

        {/* Video Canvas / Scene Stage */}
        <div
          style={{
            height: "300px",
            background: "linear-gradient(135deg, #090a0f 0%, #151a24 100%)",
            position: "relative",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            textAlign: "center",
          }}
        >
          {/* Badge Escena */}
          <div
            style={{
              position: "absolute",
              top: "14px",
              left: "14px",
              background: "rgba(255,255,255,0.1)",
              padding: "4px 10px",
              borderRadius: "20px",
              fontSize: "0.75rem",
              color: "var(--accent)",
              fontWeight: "600",
            }}
          >
            Escena {currentSceneIdx + 1} / {scenes.length} ({currentScene.title || "Tópico"})
          </div>

          <div style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff", marginBottom: "12px", maxWidth: "80%" }}>
            {currentScene.title}
          </div>

          <p style={{ fontSize: "0.95rem", color: "#e2e8f0", lineHeight: "1.6", maxWidth: "90%", fontStyle: "italic" }}>
            "{currentScene.narration}"
          </p>

          <div style={{ marginTop: "16px", fontSize: "0.75rem", color: "var(--text-muted)", background: "rgba(0,0,0,0.3)", padding: "4px 10px", borderRadius: "6px" }}>
            🎥 Visual: {currentScene.visual_prompt}
          </div>
        </div>

        {/* Timeline Progress */}
        <div style={{ display: "flex", height: "4px", background: "var(--border)" }}>
          {scenes.map((s, idx) => (
            <div
              key={idx}
              style={{
                flex: s.duration || 6,
                background: idx === currentSceneIdx ? "var(--accent)" : idx < currentSceneIdx ? "var(--text-muted)" : "transparent",
                transition: "background 0.3s ease",
              }}
            />
          ))}
        </div>

        {/* Controls */}
        <div style={{ padding: "12px 18px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg-base)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
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
              {isPlaying ? "Pausar" : "Reproducir Video con Voz"}
            </button>

            <button
              onClick={() => {
                setIsPlaying(false);
                setCurrentSceneIdx(0);
                if (window.speechSynthesis) window.speechSynthesis.cancel();
              }}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                color: "var(--text)",
                padding: "8px 12px",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              <RotateCcw size={15} />
            </button>
          </div>

          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            Duración estimada: {scenes.reduce((acc, s) => acc + (s.duration || 6), 0)}s
          </span>
        </div>
      </div>
    </div>
  );
}
