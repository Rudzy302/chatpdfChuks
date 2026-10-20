const API_BASE = (typeof window !== "undefined" && window.location.port === "4173") ? "/api" : "http://127.0.0.1:8008/api";

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error("Error obteniendo documentos");
  return res.json();
}

export async function uploadDocument(file, { analyzeImages = true, provider = "Ollama (Local)", apiKey = "" } = {}) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("analyze_images", analyzeImages);
  formData.append("provider", provider);
  formData.append("api_key", apiKey);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error en la subida" }));
    throw new Error(err.detail || "Error al procesar el archivo");
  }
  return res.json();
}

export async function deleteDocument(filename) {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Error al eliminar documento");
  return res.json();
}

export function getPdfFileUrl(filename) {
  return `${API_BASE}/documents/${encodeURIComponent(filename)}/file`;
}

export async function sendChatMessage({ prompt, activeDoc = "", history = [], provider = "Ollama (Local)", apiKey = "", modelName = "", topK = 6 }) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      active_doc: activeDoc,
      history,
      provider,
      api_key: apiKey,
      model_name: modelName,
      top_k: topK,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error en el chat" }));
    throw new Error(err.detail || "Error en el servidor de IA");
  }
  return res.json();
}

export async function fetchSummary({ filename, provider = "Ollama (Local)", apiKey = "", modelName = "" }) {
  const res = await fetch(`${API_BASE}/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename,
      provider,
      api_key: apiKey,
      model_name: modelName,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error al generar resumen" }));
    throw new Error(err.detail || "Error al obtener síntesis");
  }
  return res.json();
}

export async function generateVideo({ filename, summaryText = "", provider = "Ollama (Local)", apiKey = "" }) {
  const res = await fetch(`${API_BASE}/video/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename,
      summary_text: summaryText,
      provider,
      api_key: apiKey,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error al generar video" }));
    throw new Error(err.detail || "Error al crear storyboard del video");
  }
  return res.json();
}

export async function detectAvailableModels({ provider = "Ollama (Local)", apiKey = "" } = {}) {
  const res = await fetch(`${API_BASE}/models/detect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider,
      api_key: apiKey,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Error al detectar modelos" }));
    throw new Error(err.detail || "No se pudieron obtener los modelos de la cuenta");
  }
  return res.json();
}

export async function shutdownSystem() {
  try {
    await fetch(`${API_BASE}/system/shutdown`, { method: "POST" });
  } catch (e) {
    // Si la conexión se cierra porque el servidor murió, es el resultado esperado
  }
}


