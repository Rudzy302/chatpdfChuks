# Document Studio (ChatPDF con Reconocimiento Visual y Citas Directas)

Aplicación integral de análisis documental, RAG (Retrieval-Augmented Generation) avanzado, visión multimodal y citas interactivas sobre documentos PDF.

## 🚀 Características Principales

- **Diseño Minimalista & Personalizable:** Paleta de colores interactiva, soporte de temas personalizados y alternancia de vistas (Chat, Visor continuo de PDF y Síntesis documental).
- **RAG con Chunks por Página:** Indexación estructurada (1 chunk por página) almacenada en PostgreSQL con extensión `pgvector`.
- **Reconocimiento Visual & OCR Híbrido:**
  - Extracción y análisis de imágenes embebidas con modelos de visión (`llava:7b` / Google Gemini).
  - OCR local mediante `RapidOCR` (ONNX) para extraer texto y expresiones matemáticas de páginas escaneadas.
- **Citas Interactivas & Resaltado Fluorescente:** Botones de salto directo a la página referenciada (`[Pág. X]`) y marcado amarillo sobre el documento.
- **Multi-Motor de Inferencia:**
  - Local: Ollama (`qwen2.5`, `mistral`, `llava`) y `llama-server` (`llama.cpp` CUDA).
  - Nube: Google Gemini API y OpenAI / Groq.

## 🛠️ Tecnologías

- **Frontend & Backend:** Streamlit, Python
- **Base de Datos Vectorial:** PostgreSQL 16 + `pgvector`
- **PDF Engine & OCR:** PyMuPDF (`fitz`), PDF.js, RapidOCR ONNX
- **Inferencia:** Ollama, Llama.cpp, Google Gemini API
# chatpdfChuks
