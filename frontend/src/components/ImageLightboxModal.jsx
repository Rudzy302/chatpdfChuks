import React, { useState, useEffect } from "react";
import { X, ZoomIn, ZoomOut, RotateCw, Download, Maximize2, RefreshCw } from "lucide-react";

export default function ImageLightboxModal({ imageUrl, onClose }) {
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!imageUrl) return null;

  const handleZoomIn = () => setScale((prev) => Math.min(prev + 0.25, 3.5));
  const handleZoomOut = () => setScale((prev) => Math.max(prev - 0.25, 0.5));
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);
  const handleReset = () => {
    setScale(1);
    setRotation(0);
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(0, 0, 0, 0.88)",
        backdropFilter: "blur(10px)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      {/* Barra de herramientas flotante superior */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "absolute",
          top: "16px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          background: "rgba(22, 27, 34, 0.85)",
          padding: "8px 16px",
          borderRadius: "30px",
          border: "1px solid rgba(255, 255, 255, 0.15)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
          zIndex: 10000,
        }}
      >
        <button
          onClick={handleZoomIn}
          style={{ background: "transparent", border: "none", color: "#ffffff", cursor: "pointer", display: "flex", alignItems: "center", padding: "4px" }}
          title="Acercar (Zoom In)"
        >
          <ZoomIn size={18} />
        </button>

        <button
          onClick={handleZoomOut}
          style={{ background: "transparent", border: "none", color: "#ffffff", cursor: "pointer", display: "flex", alignItems: "center", padding: "4px" }}
          title="Alejar (Zoom Out)"
        >
          <ZoomOut size={18} />
        </button>

        <button
          onClick={handleRotate}
          style={{ background: "transparent", border: "none", color: "#ffffff", cursor: "pointer", display: "flex", alignItems: "center", padding: "4px" }}
          title="Girar 90°"
        >
          <RotateCw size={18} />
        </button>

        <button
          onClick={handleReset}
          style={{ background: "transparent", border: "none", color: "#ffffff", cursor: "pointer", display: "flex", alignItems: "center", padding: "4px" }}
          title="Restablecer tamaño"
        >
          <RefreshCw size={17} />
        </button>

        <div style={{ width: "1px", height: "18px", background: "rgba(255,255,255,0.2)" }} />

        <a
          href={imageUrl}
          download
          target="_blank"
          rel="noreferrer"
          style={{ color: "#38bdf8", textDecoration: "none", display: "flex", alignItems: "center", gap: "6px", fontSize: "0.82rem", fontWeight: "600", padding: "2px 6px" }}
          title="Descargar imagen completa"
        >
          <Download size={17} />
          <span>Descargar</span>
        </a>

        <div style={{ width: "1px", height: "18px", background: "rgba(255,255,255,0.2)" }} />

        <button
          onClick={onClose}
          style={{ background: "#ef4444", border: "none", color: "#ffffff", cursor: "pointer", display: "flex", alignItems: "center", padding: "4px", borderRadius: "50%" }}
          title="Cerrar visor (Esc)"
        >
          <X size={16} />
        </button>
      </div>

      {/* Contenedor de la Imagen con Zoom y Rotación */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: "92vw",
          maxHeight: "85vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
          transition: "transform 0.15s ease",
          transform: `scale(${scale}) rotate(${rotation}deg)`,
        }}
      >
        <img
          src={imageUrl}
          alt="Visualización en alta resolución"
          style={{
            maxWidth: "100%",
            maxHeight: "82vh",
            objectFit: "contain",
            borderRadius: "8px",
            boxShadow: "0 10px 40px rgba(0,0,0,0.8)",
            cursor: scale > 1 ? "grab" : "default",
          }}
        />
      </div>

      {/* Pie de foto indicador */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "absolute",
          bottom: "16px",
          color: "rgba(255, 255, 255, 0.75)",
          fontSize: "0.8rem",
          background: "rgba(0,0,0,0.5)",
          padding: "4px 14px",
          borderRadius: "20px",
        }}
      >
        Zoom: {Math.round(scale * 100)}% • Haz clic fuera o presiona Esc para cerrar
      </div>
    </div>
  );
}
