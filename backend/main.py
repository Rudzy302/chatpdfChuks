import os
import re
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

from .config import settings
from .database import db
from .services.pdf_service import process_and_index_pdf, get_indexed_documents, delete_document, get_document_full_text
from .services.rag_service import retrieve_rag_context, extract_highlight_words
from .services.ai import call_llm

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API de Document Studio para procesamiento de PDF, OCR, RAG y Chat multimodal."
)

# Habilitar CORS para el frontend Next.js / React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    db.init_schema()

# --- MODELOS PYDANTIC ---

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    prompt: str
    active_doc: Optional[str] = ""
    history: List[ChatMessage] = []
    provider: Optional[str] = "Llama.cpp Server (Local)"
    api_key: Optional[str] = ""
    model_name: Optional[str] = ""
    top_k: Optional[int] = 6

class SummaryRequest(BaseModel):
    filename: str
    provider: Optional[str] = "Llama.cpp Server (Local)"
    api_key: Optional[str] = ""
    model_name: Optional[str] = ""

# --- RUTAS DE DOCUMENTOS ---

@app.get("/api/documents")
def list_documents():
    """Lista todos los documentos indexados en el sistema."""
    return get_indexed_documents()

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    analyze_images: bool = Form(True),
    provider: str = Form("Ollama (Local)"),
    api_key: str = Form("")
):
    """Sube e indexa un documento PDF con texto, OCR y visión multimodal."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se admiten archivos .pdf")

    contents = await file.read()
    try:
        result = process_and_index_pdf(
            file_bytes=contents,
            filename=file.filename,
            provider=provider,
            api_key=api_key,
            analyze_images=analyze_images
        )
        return {"status": "ok", "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar documento: {str(e)}")

@app.get("/api/documents/{filename}/file")
def get_pdf_file(filename: str):
    """Sirve el archivo PDF binario para visualización continua."""
    file_path = os.path.join(settings.UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return FileResponse(file_path, media_type="application/pdf", filename=filename)

@app.delete("/api/documents/{filename}")
def remove_document(filename: str):
    """Elimina el documento e invalida sus vectores."""
    success = delete_document(filename)
    if not success:
        raise HTTPException(status_code=500, detail="No se pudo eliminar el documento.")
    return {"status": "ok", "deleted": filename}

# --- RUTA DE CHAT RAG ---

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Endpoint principal de conversación con RAG, citas automáticas y OCR."""
    clean_p = req.prompt.strip().lower()
    
    # 1. Fast-path de cortesía
    if clean_p in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "que tal", "hola!", "holaa", "saludos"]:
        return {
            "answer": "¡Hola! Estoy listo para responder consultas técnicas sobre tu documento. Puedes preguntarme sobre el texto, pasos o sobre cualquier imagen que contenga.",
            "citations": [],
            "target_page": 1,
            "highlight_words": []
        }
    elif clean_p in ["gracias", "muchas gracias", "ok gracias", "vale gracias", "perfecto gracias"]:
        return {
            "answer": "¡Con gusto! Quedo a tu disposición si necesitas verificar cualquier otro dato o página.",
            "citations": [],
            "target_page": 1,
            "highlight_words": []
        }

    # 2. Recuperación RAG
    rag_info = retrieve_rag_context(req.prompt, req.active_doc, top_k=req.top_k)

    sys_prompt = f"""Eres un asistente de análisis documental riguroso, de alta fidelidad y especialista en transcripción y resolución.
Responde de forma clara, directa, comprensible y 100% legible basándote en el contexto del documento, el texto transcrito (OCR) y las descripciones visuales proporcionadas.

REGLAS DE FORMATO Y LEGIBILIDAD (CRÍTICO):
1. FORMATO DE FRACCIONES Y TEXTO PLANO:
   - PROHIBIDO TERMINANTEMENTE usar código o comandos crudos de LaTeX como '\\frac{{a}}{{b}}', '(\frac{{...}})' o etiquetas extrañas.
   - Escribe las fracciones SIEMPRE en formato natural de texto plano legible y limpio, con barra diagonal (ej: 3/8, 6/16, 24/64, 48/128, etc.).
   - Estructura los ejercicios línea por línea de forma ordenada y limpia (ejemplo:
     a) 3/8 = 6/16 = 12/32 = 24/64 = 48/128 = 96/256
     b) ...
   ).
2. CITACIÓN OBLIGATORIA: Cita SIEMPRE el número de página exacto entre corchetes, por ejemplo [Pág. 1].
3. TRANSCRIPCIÓN Y RESOLUCIÓN: Transcribe todos los ejercicios y texto que veas con máxima fidelidad, sin inventar y sin omitir nada.
4. Emplea la terminología textual exacta del documento para permitir el marcado fluorescente.

CONTEXTO DOCUMENTAL E IMÁGENES:
{rag_info['context_text']}
"""

    history_dicts = [{"role": m.role, "content": m.content} for m in req.history]
    raw_answer = call_llm(
        prompt=req.prompt,
        system_prompt=sys_prompt,
        history=history_dicts,
        provider=req.provider,
        api_key=req.api_key,
        model_name=req.model_name
    )

    # Sanitización de salida (evitar que se filtren comandos LaTeX)
    clean_ans = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', raw_answer)
    clean_ans = re.sub(r'\(?\\frac\{([^}]+)\}\{([^}]+)\}\)?', r'\1/\2', clean_ans)
    clean_ans = clean_ans.replace(r'\(', '').replace(r'\)', '').replace(r'\[', '[').replace(r'\]', ']')

    found_cites = re.findall(r'\[(?:Pág\.|Página|Imagen en Pág\.)\s*(\d+)\]', clean_ans, re.IGNORECASE)
    target_page = int(found_cites[0]) if found_cites else rag_info["target_page"]
    highlight_words = extract_highlight_words(req.prompt, clean_ans, rag_info["target_content"])

    # Extraer lista única de páginas citadas
    seen_pages = []
    for c in found_cites:
        p = int(c)
        if p not in seen_pages:
            seen_pages.append(p)

    return {
        "answer": clean_ans,
        "citations": seen_pages,
        "target_page": target_page,
        "target_file": rag_info["target_file"] or req.active_doc,
        "target_content": rag_info["target_content"],
        "highlight_words": highlight_words
    }

# --- RUTA DE SÍNTESIS ---

@app.post("/api/summary")
def summary_endpoint(req: SummaryRequest):
    """Genera una síntesis estructurada del documento completo."""
    full_text = get_document_full_text(req.filename)
    if not full_text:
        raise HTTPException(status_code=404, detail="El documento no tiene contenido para resumir.")

    prompt = f"Elabora una síntesis estructurada por puntos clave del documento '{req.filename}':\n\n{full_text[:12000]}"
    sys_prompt = "Eres un analista documental experto. Proporciona un resumen claro, estructurado y exhaustivo."
    
    summary_text = call_llm(
        prompt=prompt,
        system_prompt=sys_prompt,
        history=[],
        provider=req.provider,
        api_key=req.api_key,
        model_name=req.model_name
    )
    return {"summary": summary_text}

# --- RUTA DE GENERACIÓN DE VIDEO DE RESUMEN ---

class VideoRequest(BaseModel):
    filename: str
    summary_text: Optional[str] = ""
    provider: Optional[str] = "Ollama (Local)"
    api_key: Optional[str] = ""

@app.post("/api/video/generate")
def generate_video_endpoint(req: VideoRequest):
    """Genera un storyboard y escenas estructuradas para un video resumen animado del documento."""
    text_source = req.summary_text
    if not text_source:
        text_source = get_document_full_text(req.filename)[:4000]
    
    if not text_source:
        raise HTTPException(status_code=400, detail="No hay contenido suficiente para generar el video.")

    prompt = (
        f"Genera el guión y estructura de un video corto (Short/Reel de 30-45 segundos) resumiendo el documento '{req.filename}'. "
        f"Basado en este contenido:\n{text_source[:3000]}\n\n"
        "Devuelve un formato JSON estricto con la siguiente estructura:\n"
        "{\n"
        '  "title": "Título llamativo",\n'
        '  "scenes": [\n'
        '    {"id": 1, "duration": 5, "title": "Introducción", "narration": "Frase de locución...", "visual_prompt": "Descripción visual de la escena"},\n'
        '    {"id": 2, "duration": 8, "title": "Concepto Clave", "narration": "Explicación breve...", "visual_prompt": "Descripción visual..."},\n'
        '    {"id": 3, "duration": 8, "title": "Puntos Principales", "narration": "Detalle crucial...", "visual_prompt": "Gráfico o ilustración..."},\n'
        '    {"id": 4, "duration": 5, "title": "Conclusión", "narration": "Llamado a la acción o resumen final...", "visual_prompt": "Cierre..."}\n'
        "  ]\n"
        "}\n"
        "IMPORTANTE: Devuelve ÚNICAMENTE el bloque JSON válido, sin comentarios adicionales ni markdown."
    )

    storyboard_raw = call_llm(
        prompt=prompt,
        system_prompt="Eres un director audiovisual especializado en crear videos educativos y técnicos impactantes.",
        history=[],
        provider=req.provider,
        api_key=req.api_key
    )

    import json
    try:
        # Extraer JSON de la respuesta
        match = re.search(r'\{.*\}', storyboard_raw, re.DOTALL)
        if match:
            storyboard = json.loads(match.group(0))
        else:
            storyboard = json.loads(storyboard_raw)
    except Exception:
        storyboard = {
            "title": f"Resumen de {req.filename}",
            "scenes": [
                {"id": 1, "duration": 6, "title": "Visión General", "narration": f"Este documento aborda los aspectos centrales de {req.filename}.", "visual_prompt": "Documento abriéndose en un entorno de estudio analítico"},
                {"id": 2, "duration": 8, "title": "Desarrollo", "narration": text_source[:150].strip() + "...", "visual_prompt": "Visualización de conceptos y datos clave"},
                {"id": 3, "duration": 6, "title": "Conclusión", "narration": "Consulta el chat interactivo para explorar cada página citada en detalle.", "visual_prompt": "Pantalla interactiva con citas y resaltado"}
            ]
        }

    return {"status": "ok", "storyboard": storyboard}

# --- RUTA DE APAGADO SEGURO ---

@app.post("/api/system/shutdown")
def shutdown_system():
    """Apaga ordenadamente los procesos del backend y frontend para liberar memoria y recursos."""
    import threading
    def kill_soon():
        import time
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=kill_soon).start()
    return {"status": "ok", "message": "Servicios apagándose correctamente..."}

