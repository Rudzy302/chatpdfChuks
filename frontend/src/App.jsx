import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import ChatView from "./components/ChatView";
import PdfViewer from "./components/PdfViewer";
import SummaryView from "./components/SummaryView";
import VideoModal from "./components/VideoModal";
import { fetchDocuments, deleteDocument, sendChatMessage, getPdfFileUrl, generateVideo } from "./services/api";
import { MessageSquare, FileText, Sparkles, Film } from "lucide-react";

const THEMES = {
  "Minimal Dark (Grafito)": {
    "--bg-base": "#0f1115",
    "--bg-card": "#161920",
    "--bg-sidebar": "#12141a",
    "--border": "#232733",
    "--border-hover": "#363d4f",
    "--accent": "#4f6bf5",
    "--accent-light": "rgba(79, 107, 245, 0.15)",
    "--text": "#f1f3f7",
    "--text-muted": "#8d95a5",
  },
  "Minimal Light (Papel)": {
    "--bg-base": "#f8f9fa",
    "--bg-card": "#ffffff",
    "--bg-sidebar": "#f1f3f5",
    "--border": "#e5e7eb",
    "--border-hover": "#d1d5db",
    "--accent": "#2563eb",
    "--accent-light": "rgba(37, 99, 235, 0.12)",
    "--text": "#111827",
    "--text-muted": "#6b7280",
  },
  "Nordic Slate (Pizarra)": {
    "--bg-base": "#181d24",
    "--bg-card": "#1e242d",
    "--bg-sidebar": "#15191f",
    "--border": "#2a323e",
    "--border-hover": "#3d4858",
    "--accent": "#0ea5e9",
    "--accent-light": "rgba(14, 165, 233, 0.15)",
    "--text": "#eef2f6",
    "--text-muted": "#94a3b8",
  },
  "Monochrome (Noir)": {
    "--bg-base": "#000000",
    "--bg-card": "#0d0d0d",
    "--bg-sidebar": "#080808",
    "--border": "#222222",
    "--border-hover": "#444444",
    "--accent": "#e5e5e5",
    "--accent-light": "rgba(229, 229, 229, 0.15)",
    "--text": "#ffffff",
    "--text-muted": "#a3a3a3",
  },
};

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [activeDoc, setActiveDoc] = useState("");
  const [targetPage, setTargetPage] = useState(1);
  const [highlightWords, setHighlightWords] = useState([]);

  // Visibilidad de paneles independientes
  const [showChat, setShowChat] = useState(true);
  const [showPdf, setShowPdf] = useState(true);
  const [showSummary, setShowSummary] = useState(false);

  // Modal de Video Storyboard
  const [videoStoryboard, setVideoStoryboard] = useState(null);
  const [generatingVideo, setGeneratingVideo] = useState(false);

  // Tema
  const [currentTheme, setCurrentTheme] = useState("Minimal Dark (Grafito)");

  // Chat
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hola. Document Studio está listo con soporte para reconocimiento por micrófono, lector de voz y resaltado por citas. Toda respuesta citará la página exacta con un círculo numérico para saltar a la fuente.",
    },
  ]);
  const [suggestedQuestions, setSuggestedQuestions] = useState([
    "¿De qué trata este documento?",
    "Explícame los conceptos más importantes",
    "¿Qué ejercicios o imágenes contiene?"
  ]);
  const [sending, setSending] = useState(false);

  // Configuración de modelo
  const [aiSettings, setAiSettings] = useState({
    provider: "Llama.cpp Server (Local)",
    modelName: "qwen2.5:7b",
    apiKey: "",
    topK: 6,
  });

  const loadDocs = async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      if (docs.length > 0 && (!activeDoc || activeDoc === "Todos los documentos")) {
        setActiveDoc(docs[0].filename);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  // Aplicar tema dinámico en CSS root
  useEffect(() => {
    const t = THEMES[currentTheme] || THEMES["Minimal Dark (Grafito)"];
    for (const [key, val] of Object.entries(t)) {
      document.documentElement.style.setProperty(key, val);
    }
  }, [currentTheme]);

  const handleDeleteDoc = async (filename) => {
    if (!confirm(`¿Eliminar documento '${filename}' e invalidar sus vectores?`)) return;
    try {
      await deleteDocument(filename);
      setActiveDoc("Todos los documentos");
      loadDocs();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleUploadSuccess = (fname, uploadData) => {
    loadDocs();
    setActiveDoc(fname);

    // 3 & 4. Si el backend generó resumen automático y preguntas sugeridas, mostrarlas de inmediato
    if (uploadData?.auto_summary) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `📄 **Resumen inicial automático de '${fname}':**\n\n${uploadData.auto_summary}`,
          citations: [1],
        },
      ]);
    }
    if (uploadData?.suggested_questions && uploadData.suggested_questions.length > 0) {
      setSuggestedQuestions(uploadData.suggested_questions);
    }
  };

  const handleSendMessage = async (text) => {
    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);

    try {
      const historyToSend = messages.slice(-6).map((m) => ({ role: m.role, content: m.content }));
      const res = await sendChatMessage({
        prompt: text,
        activeDoc,
        history: historyToSend,
        provider: aiSettings.provider,
        apiKey: aiSettings.apiKey,
        modelName: aiSettings.modelName,
        topK: aiSettings.topK,
      });

      const assistantMsg = {
        role: "assistant",
        content: res.answer,
        citations: res.citations || [],
        target_content: res.target_content || "",
      };

      setMessages((prev) => [...prev, assistantMsg]);
      if (res.target_page) {
        setTargetPage(res.target_page);
      }
      // Inicialmente NO sobrecargamos con marcado de todas las palabras, se activa limpiamente por círculo
      setHighlightWords([]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${err.message}` }]);
    } finally {
      setSending(false);
    }
  };

  // 5. Salto y marcado de la parte citada al hacer clic en el círculo con número de orden
  const handleNavigateToPage = (pageNum, citedContent) => {
    setTargetPage(pageNum);
    setShowPdf(true);
    if (citedContent) {
      // Extraer términos clave exactos del fragmento citado específico
      const words = citedContent.match(/\b[A-Za-z0-9_áéíóúÁÉÍÓÚñÑ]{3,}\b/g) || [];
      const filtered = words.filter(
        (w) => !["para", "como", "este", "esta", "sobre", "desde", "entre", "texto", "pagina", "archivo"].includes(w.toLowerCase())
      );
      setHighlightWords(filtered.slice(0, 15));
    }
  };

  // 2. Generación de Video Resumen
  const handleGenerateVideo = async () => {
    if (!activeDoc || activeDoc === "Todos los documentos") {
      alert("Selecciona un documento primero para generar su video resumen.");
      return;
    }
    setGeneratingVideo(true);
    try {
      const res = await generateVideo({
        filename: activeDoc,
        provider: aiSettings.provider,
        apiKey: aiSettings.apiKey,
      });
      if (res.storyboard) {
        setVideoStoryboard(res.storyboard);
      }
    } catch (err) {
      alert("Error generando video: " + err.message);
    } finally {
      setGeneratingVideo(false);
    }
  };

  const activeViewsCount = [showChat, showPdf, showSummary].filter(Boolean).length;
  const pdfUrl = activeDoc && activeDoc !== "Todos los documentos" ? getPdfFileUrl(activeDoc) : null;

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", overflow: "hidden" }}>
      {/* Modal de Video */}
      {videoStoryboard && (
        <VideoModal storyboard={videoStoryboard} onClose={() => setVideoStoryboard(null)} />
      )}

      {/* Sidebar */}
      <Sidebar
        documents={documents}
        activeDoc={activeDoc}
        onSelectDoc={setActiveDoc}
        onDeleteDoc={handleDeleteDoc}
        onUploadSuccess={handleUploadSuccess}
        theme={currentTheme}
        onThemeChange={setCurrentTheme}
        themes={THEMES}
      />

      {/* Main Container */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
        {/* Top Navbar */}
        <header
          style={{
            height: "50px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 20px",
            background: "var(--bg-card)",
          }}
        >
          <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
            <span style={{ fontWeight: "700", fontSize: "1rem", color: "var(--text)" }}>Document Studio</span>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>/ {activeDoc || "Todos los documentos"}</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={() => setShowChat(!showChat)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "6px",
                fontSize: "0.82rem",
                cursor: "pointer",
                background: showChat ? "var(--accent)" : "transparent",
                color: showChat ? "#ffffff" : "var(--text)",
                border: "1px solid " + (showChat ? "var(--accent)" : "var(--border)"),
              }}
            >
              <MessageSquare size={14} />
              Chat ({showChat ? "Activo" : "Oculto"})
            </button>

            <button
              onClick={() => setShowPdf(!showPdf)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "6px",
                fontSize: "0.82rem",
                cursor: "pointer",
                background: showPdf ? "var(--accent)" : "transparent",
                color: showPdf ? "#ffffff" : "var(--text)",
                border: "1px solid " + (showPdf ? "var(--accent)" : "var(--border)"),
              }}
            >
              <FileText size={14} />
              Documento ({showPdf ? "Activo" : "Oculto"})
            </button>

            <button
              onClick={() => setShowSummary(!showSummary)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "6px",
                fontSize: "0.82rem",
                cursor: "pointer",
                background: showSummary ? "var(--accent)" : "transparent",
                color: showSummary ? "#ffffff" : "var(--text)",
                border: "1px solid " + (showSummary ? "var(--accent)" : "var(--border)"),
              }}
            >
              <Sparkles size={14} />
              Resumen ({showSummary ? "Activo" : "Oculto"})
            </button>
          </div>
        </header>

        {/* Dynamic Panels Layout */}
        <div
          style={{
            flex: 1,
            display: "grid",
            gridTemplateColumns:
              activeViewsCount === 3
                ? "35% 40% 25%"
                : activeViewsCount === 2
                ? "50% 50%"
                : "100%",
            height: "calc(100vh - 50px)",
            overflow: "hidden",
          }}
        >
          {showChat && (
            <div style={{ borderRight: activeViewsCount > 1 ? "1px solid var(--border)" : "none", height: "100%", overflow: "hidden" }}>
              <ChatView
                messages={messages}
                onSendMessage={handleSendMessage}
                onNavigateToPage={handleNavigateToPage}
                sending={sending}
                aiSettings={aiSettings}
                onUpdateAiSettings={setAiSettings}
                suggestedQuestions={suggestedQuestions}
                onGenerateVideo={handleGenerateVideo}
                activeDoc={activeDoc}
              />
            </div>
          )}

          {showPdf && (
            <div style={{ borderRight: activeViewsCount === 3 ? "1px solid var(--border)" : "none", height: "100%", overflow: "hidden" }}>
              {pdfUrl ? (
                <PdfViewer fileUrl={pdfUrl} targetPage={targetPage} highlightWords={highlightWords} />
              ) : (
                <div style={{ display: "flex", height: "100%", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: "0.9rem" }}>
                  Selecciona un documento en la barra lateral para visualizarlo.
                </div>
              )}
            </div>
          )}

          {showSummary && (
            <div style={{ height: "100%", overflow: "hidden" }}>
              <SummaryView filename={activeDoc} aiSettings={aiSettings} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
