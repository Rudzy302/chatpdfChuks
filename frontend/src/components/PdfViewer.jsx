import React, { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist/build/pdf";
import { ZoomIn, ZoomOut, FileText } from "lucide-react";

// Configurar worker de pdfjs
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`;

export default function PdfViewer({ fileUrl, targetPage = 1, highlightWords = [] }) {
  const containerRef = useRef(null);
  const [scale, setScale] = useState(1.1);
  const [loading, setLoading] = useState(false);
  const [totalPages, setTotalPages] = useState(0);

  // Carga inicial y renderizado continuo de las páginas del PDF
  useEffect(() => {
    if (!fileUrl) return;

    let active = true;
    setLoading(true);

    const loadPdf = async () => {
      try {
        const loadingTask = pdfjsLib.getDocument(fileUrl);
        const pdf = await loadingTask.promise;
        if (!active) return;
        setTotalPages(pdf.numPages);

        if (containerRef.current) {
          containerRef.current.innerHTML = "";
        }

        for (let p = 1; p <= pdf.numPages; p++) {
          const page = await pdf.getPage(p);
          const viewport = page.getViewport({ scale });

          // Card contenedor de página
          const card = document.createElement("div");
          card.className = "page-card";
          card.id = `page-${p}`;
          card.style.position = "relative";
          card.style.background = "#ffffff";
          card.style.margin = "0 auto 20px auto";
          card.style.boxShadow = "0 4px 16px rgba(0,0,0,0.4)";
          card.style.borderRadius = "4px";
          card.style.width = `${viewport.width}px`;

          // Badge número de página
          const badge = document.createElement("div");
          badge.textContent = `Pág. ${p} de ${pdf.numPages}`;
          badge.style.position = "absolute";
          badge.style.top = "-12px";
          badge.style.right = "12px";
          badge.style.background = "var(--bg-card)";
          badge.style.color = "var(--text-muted)";
          badge.style.fontSize = "11px";
          badge.style.fontWeight = "600";
          badge.style.padding = "2px 8px";
          badge.style.borderRadius = "4px";
          badge.style.border = "1px solid var(--border)";
          badge.style.zIndex = "10";
          card.appendChild(badge);

          // Canvas render
          const canvas = document.createElement("canvas");
          canvas.height = viewport.height;
          canvas.width = viewport.width;
          canvas.style.display = "block";
          canvas.style.borderRadius = "4px";
          card.appendChild(canvas);

          // Text layer para selección y marcado de citas
          const textLayer = document.createElement("div");
          textLayer.className = "textLayer";
          textLayer.style.position = "absolute";
          textLayer.style.left = "0";
          textLayer.style.top = "0";
          textLayer.style.right = "0";
          textLayer.style.bottom = "0";
          textLayer.style.opacity = "1";
          card.appendChild(textLayer);

          if (containerRef.current) {
            containerRef.current.appendChild(card);
          }

          const ctx = canvas.getContext("2d");
          await page.render({ canvasContext: ctx, viewport }).promise;

          const textContent = await page.getTextContent();
          await pdfjsLib.renderTextLayer({
            textContentSource: textContent,
            container: textLayer,
            viewport: viewport,
            textDivs: [],
          }).promise;
        }

        setLoading(false);

        // Desplazarse a la página destino inicial
        setTimeout(() => {
          const targetEl = document.getElementById(`page-${targetPage}`);
          if (targetEl) {
            targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        }, 100);
      } catch (err) {
        console.error("Error al renderizar PDF:", err);
        setLoading(false);
      }
    };

    loadPdf();

    return () => {
      active = false;
    };
  }, [fileUrl, scale]);

  // Actualización instantánea de resaltado en el DOM (sin re-renderizar los canvas)
  useEffect(() => {
    if (!containerRef.current) return;

    // 1. Limpiar resaltados previos
    const prevMarks = containerRef.current.querySelectorAll(".pdf-highlight-mark");
    prevMarks.forEach((el) => el.classList.remove("pdf-highlight-mark"));

    if (!highlightWords || highlightWords.length === 0) return;

    // 2. Aplicar clases en spans que coincidan
    const terms = highlightWords.map((w) => w.trim().toLowerCase()).filter((w) => w.length >= 3);
    const spans = containerRef.current.querySelectorAll(".textLayer span");
    for (let i = 0; i < spans.length; i++) {
      const text = spans[i].textContent.toLowerCase();
      if (terms.some((t) => text.includes(t) || (text.length >= 3 && t.includes(text)))) {
        spans[i].classList.add("pdf-highlight-mark");
      }
    }
  }, [highlightWords]);

  // Desplazamiento suave al cambiar de página destino
  useEffect(() => {
    if (!targetPage) return;
    const targetEl = document.getElementById(`page-${targetPage}`);
    if (targetEl) {
      targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [targetPage]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", overflow: "hidden", background: "var(--bg-base)" }}>
      {/* Barra de herramientas */}
      <div style={{ height: "42px", padding: "0 16px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg-card)", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
          <FileText size={16} />
          <span>Visor de Documento</span>
          {totalPages > 0 && <span style={{ opacity: 0.6 }}>({totalPages} págs.)</span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            onClick={() => setScale((s) => Math.max(0.7, s - 0.15))}
            style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--text)", borderRadius: "4px", padding: "4px 8px", cursor: "pointer", display: "flex", alignItems: "center" }}
            title="Reducir"
          >
            <ZoomOut size={14} />
          </button>
          <span style={{ fontSize: "12px", minWidth: "40px", textAlign: "center", color: "var(--text-muted)" }}>{Math.round(scale * 100)}%</span>
          <button
            onClick={() => setScale((s) => Math.min(2.0, s + 0.15))}
            style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--text)", borderRadius: "4px", padding: "4px 8px", cursor: "pointer", display: "flex", alignItems: "center" }}
            title="Aumentar"
          >
            <ZoomIn size={14} />
          </button>
        </div>
      </div>

      {/* Contenedor con scroll continuo */}
      <div style={{ flex: 1, overflowY: "auto", overflowX: "auto", padding: "20px 10px", display: "flex", flexDirection: "column", alignItems: "center" }}>
        {loading && <div style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "40px" }}>Cargando páginas del documento...</div>}
        <div ref={containerRef} style={{ display: "flex", flexDirection: "column", alignItems: "center" }} />
      </div>
    </div>
  );
}
