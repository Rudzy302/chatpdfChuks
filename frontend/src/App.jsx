import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import ChatView from "./components/ChatView";
import PdfViewer from "./components/PdfViewer";
import AudioReaderModal from "./components/AudioReaderModal";
import SettingsModal from "./components/SettingsModal";
import { fetchDocuments, deleteDocument, sendChatMessage, getPdfFileUrl, generateVideo } from "./services/api";

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

  // Modal de Video Storyboard
  const [videoStoryboard, setVideoStoryboard] = useState(null);
  const [generatingVideo, setGeneratingVideo] = useState(false);

  // Tema
  const [currentTheme, setCurrentTheme] = useState("Minimal Dark (Grafito)");

  // Modal de Parámetros de IA y Chunks
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Chat
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hola. Document Studio está listo con soporte para reconocimiento por micrófono, lector de voz, generación de imágenes y resaltado por citas. Toda respuesta citará la página exacta con un círculo numérico para saltar a la fuente.",
    },
  ]);
  const [suggestedQuestions, setSuggestedQuestions] = useState([
    "¿De qué trata este documento?",
    "Explícame los conceptos más importantes",
    "¿Qué ejercicios o imágenes contiene?"
  ]);
  const [sending, setSending] = useState(false);

  // Configuración de modelo y lectura
  const [aiSettings, setAiSettings] = useState({
    provider: "Ollama (Local)",
    modelName: "qwen2.5:7b",
    apiKey: "",
    topK: 6,
    chunkSize: 1000,
    chunkOverlap: 150,
    voiceSpeed: 1.0,
    karaokeEnabled: true,
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

    // Resumen instantáneo directo en el chat al terminar de indexar ("al toque insta")
    const summaryText = uploadData?.auto_summary || `Documento '${fname}' indexado exitosamente. Ya puedes consultar cualquier duda sobre sus páginas.`;
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `📄 **Resumen instantáneo de '${fname}':**\n\n${summaryText}`,
        citations: [1],
        target_content: summaryText.slice(0, 150),
      },
    ]);

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
        video_url: res.video_url || null,
        image_url: res.image_url || null,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      if (res.target_page) {
        setTargetPage(res.target_page);
      }
      if (res.suggested_questions && res.suggested_questions.length > 0) {
        setSuggestedQuestions(res.suggested_questions);
      }
      setHighlightWords([]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${err.message}` }]);
    } finally {
      setSending(false);
    }
  };

  // Salto y marcado de la parte citada al hacer clic en el círculo con número de orden
  const handleNavigateToPage = (pageNum, citedContent) => {
    setTargetPage(pageNum);
    if (citedContent) {
      const words = citedContent.match(/\b[A-Za-z0-9_áéíóúÁÉÍÓÚñÑ]{3,}\b/g) || [];
      const filtered = words.filter(
        (w) => !["para", "como", "este", "esta", "sobre", "desde", "entre", "texto", "pagina", "archivo"].includes(w.toLowerCase())
      );
      setHighlightWords(filtered.slice(0, 15));
    }
  };

  // Resaltado instantáneo al pasar el cursor (hover) por citas o círculos numéricos
  const handleHoverCitation = (pageNum, citedContent) => {
    if (!pageNum) {
      setHighlightWords([]);
      return;
    }
    if (citedContent) {
      const words = citedContent.match(/\b[A-Za-z0-9_áéíóúÁÉÍÓÚñÑ]{3,}\b/g) || [];
      const filtered = words.filter(
        (w) => !["para", "como", "este", "esta", "sobre", "desde", "entre", "texto", "pagina", "archivo"].includes(w.toLowerCase())
      );
      setHighlightWords(filtered.slice(0, 15));
    }
  };

  // Generación de Video Resumen
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

  const pdfUrl = activeDoc && activeDoc !== "Todos los documentos" ? getPdfFileUrl(activeDoc) : null;

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", overflow: "hidden" }}>
      {/* Modal de Lector de Audio Documental */}
      {videoStoryboard && (
        <AudioReaderModal storyboard={videoStoryboard} onClose={() => setVideoStoryboard(null)} />
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
        onOpenSettings={() => setIsSettingsOpen(true)}
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

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", background: "var(--bg-base)", padding: "4px 10px", borderRadius: "12px", border: "1px solid var(--border)" }}>
              {activeDoc && activeDoc !== "Todos los documentos" ? `Documento: ${activeDoc}` : "Modo Asistente General"}
            </span>
          </div>
        </header>

        {/* Dual Panel Workspace: Chat (Izquierda) + Visor PDF (Derecha) */}
        <div
          style={{
            flex: 1,
            display: "grid",
            gridTemplateColumns: "48% 52%",
            height: "calc(100vh - 50px)",
            overflow: "hidden",
          }}
        >
          <div style={{ borderRight: "1px solid var(--border)", height: "100%", overflow: "hidden" }}>
            <ChatView
              messages={messages}
              onSendMessage={handleSendMessage}
              onNavigateToPage={handleNavigateToPage}
              onHoverCitation={handleHoverCitation}
              sending={sending}
              aiSettings={aiSettings}
              onUpdateAiSettings={setAiSettings}
              suggestedQuestions={suggestedQuestions}
              onOpenAudioReader={handleGenerateVideo}
              activeDoc={activeDoc}
            />
          </div>

          <div style={{ height: "100%", overflow: "hidden" }}>
            {pdfUrl ? (
              <PdfViewer fileUrl={pdfUrl} targetPage={targetPage} highlightWords={highlightWords} />
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  height: "100%",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--text-muted)",
                  fontSize: "0.9rem",
                  padding: "20px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "2.4rem", marginBottom: "8px" }}>📄</div>
                <div style={{ fontWeight: "600", color: "var(--text)" }}>Visualizador de Documento PDF</div>
                <div style={{ fontSize: "0.82rem", marginTop: "6px", maxWidth: "280px" }}>
                  Sube o selecciona un archivo PDF en la barra lateral para explorarlo página por página.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal de Configuración Avanzada de IA, Chunks y Lector */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        aiSettings={aiSettings}
        onSaveSettings={setAiSettings}
      />
    </div>
  );
}
