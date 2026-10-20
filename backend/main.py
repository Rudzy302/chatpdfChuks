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
from .services.video_service import detect_video_request, generate_ai_video, VIDEOS_DIR
from .services.image_service import detect_image_request, generate_ai_image, IMAGES_DIR

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API de Document Studio para procesamiento de PDF, OCR, RAG y Chat multimodal."
)

# Habilitar CORS para el frontend Next.js / React
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8008",
        "http://localhost:8008",
        "*"
    ],
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
    provider: Optional[str] = "Ollama (Local)"
    api_key: Optional[str] = ""
    model_name: Optional[str] = ""
    top_k: Optional[int] = 6

class SummaryRequest(BaseModel):
    filename: str
    provider: Optional[str] = "Ollama (Local)"
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

@app.get("/api/videos/{filename}")
def get_generated_video(filename: str):
    """Sirve archivos MP4 de video generados con IA directamente en el chat."""
    file_path = os.path.join(VIDEOS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video no encontrado.")
    return FileResponse(file_path, media_type="video/mp4", filename=filename)

@app.get("/api/images/{filename}")
def get_generated_image(filename: str):
    """Sirve archivos JPG de imágenes generadas con IA directamente en el chat."""
    file_path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    return FileResponse(file_path, media_type="image/jpeg", filename=filename)

# --- RUTA DE CHAT RAG ---

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Endpoint principal de conversación con RAG, citas automáticas, generación de video/imagen y OCR."""
    clean_p = req.prompt.strip().lower()
    
    # Detección de solicitud de generación de video directo en el chat
    is_vid, vid_subject = detect_video_request(req.prompt)
    if is_vid:
        try:
            vid_filename = generate_ai_video(vid_subject)
            vid_url = f"http://127.0.0.1:8008/api/videos/{vid_filename}"
            return {
                "answer": f"🎬 ¡Aquí tienes el video generado de **{vid_subject}** con movimiento cinematográfico e iluminación dinámica:",
                "video_url": vid_url,
                "citations": [],
                "suggested_questions": [
                    f"¿Puedes generar otro video de {vid_subject} con más detalle?",
                    "Explícame los conceptos visuales clave de esta escena",
                    "Genera un video de un paisaje futurista"
                ],
                "target_page": 1,
                "target_file": req.active_doc,
                "target_content": "",
                "highlight_words": []
            }
        except Exception as e:
            print(f"[VIDEO GENERATION ERROR] {e}")

    # Detección de solicitud de generación de imagen directa en el chat
    is_img, img_subject = detect_image_request(req.prompt)
    if is_img:
        try:
            img_filename = generate_ai_image(img_subject)
            img_url = f"http://127.0.0.1:8008/api/images/{img_filename}"
            return {
                "answer": f"🎨 ¡Aquí tienes la imagen digital en alta definición de **{img_subject}**:",
                "image_url": img_url,
                "citations": [],
                "suggested_questions": [
                    f"Quiero que me generes un video de {img_subject}",
                    f"Genera otra imagen de {img_subject} con estilo cinemático 4k",
                    "Explícame la composición visual de esta escena"
                ],
                "target_page": 1,
                "target_file": req.active_doc,
                "target_content": "",
                "highlight_words": []
            }
        except Exception as e:
            print(f"[IMAGE GENERATION ERROR] {e}")

    # 2. Recuperación RAG
    rag_info = retrieve_rag_context(req.prompt, req.active_doc, top_k=req.top_k)
    clean_context = rag_info.get('context_text', '').strip()

    if clean_context:
        # Modo Análisis Documental RAG con Citas
        sys_prompt = f"""Eres un asistente de análisis documental riguroso, de alta fidelidad y especialista en resolución de consultas técnicas.
Responde de forma clara, directa, comprensible y 100% legible basándote en el contexto del documento, el texto transcrito (OCR) y las descripciones visuales proporcionadas.

REGLAS DE FORMATO Y CITACIÓN OBLIGATORIAS:
1. CITACIÓN OBLIGATORIA: Cita SIEMPRE el número de página exacto entre corchetes, por ejemplo [Pág. 1] o [Pág. 3], al final de las afirmaciones o datos que menciones del documento.
2. FORMATO DE FRACCIONES Y TEXTO PLANO:
   - PROHIBIDO usar código o comandos LaTeX como '\\frac{{a}}{{b}}'. Escribe las fracciones siempre en texto plano legible (ej: 3/8, 6/16).
3. PREGUNTAS DE SEGUIMIENTO (OBLIGATORIO):
   Al final de tu respuesta, añade exactamente 3 preguntas cortas e interesantes que el usuario podría hacer a continuación para seguir profundizando en este documento. Usa exactamente este delimitador:
   --- SUGERENCIAS ---
   - ¿Pregunta 1 de seguimiento?
   - ¿Pregunta 2 de seguimiento?
   - ¿Pregunta 3 de seguimiento?

CONTEXTO DOCUMENTAL E IMÁGENES:
{clean_context}
"""
    else:
        # Modo Asistente Inteligente Conversacional (Sin documento o preguntas generales)
        sys_prompt = """Eres un asistente de inteligencia artificial avanzado, inteligente, útil y amigable (con capacidades similares a ChatGPT o Gemini).
Puedes responder con profundidad, precisión y amabilidad a cualquier pregunta de conocimiento general, programación, matemáticas, ciencia, redacción creativa o mantener una conversación amena y natural.
Si el usuario aún no ha subido o seleccionado ningún documento PDF, responde ampliamente a su consulta y recuérdale con naturalidad que también puede cargar archivos PDF para analizarlos con OCR y citas exactas.
Responde en español, usando formato Markdown limpio y legible.

REGLAS:
- Al final de tu respuesta, añade exactamente 3 preguntas cortas de sugerencia interesantes para continuar la conversación. Usa exactamente este delimitador:
--- SUGERENCIAS ---
- ¿Pregunta 1 de sugerencia?
- ¿Pregunta 2 de sugerencia?
- ¿Pregunta 3 de sugerencia?
"""

    history_dicts = [{"role": m.role, "content": m.content} for m in req.history]
    raw_answer = call_llm(
        prompt=req.prompt,
        system_prompt=sys_prompt,
        history=history_dicts,
        provider=req.provider or "Ollama (Local)",
        api_key=req.api_key or "",
        model_name=req.model_name or ""
    )

    # Separar respuesta principal de las preguntas de seguimiento dinámicas
    suggested_questions = []
    if "--- SUGERENCIAS ---" in raw_answer:
        parts = raw_answer.split("--- SUGERENCIAS ---")
        clean_ans = parts[0].strip()
        sug_text = parts[1].strip()
        for line in sug_text.split("\n"):
            cl = line.strip().lstrip("-").lstrip("*").lstrip("0123456789.").strip()
            if cl and len(cl) > 6 and ("¿" in cl or "?" in cl):
                suggested_questions.append(cl)
    else:
        clean_ans = raw_answer.strip()

    # Sanitización de salida (evitar que se filtren comandos LaTeX)
    clean_ans = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', clean_ans)
    clean_ans = re.sub(r'\(?\\frac\{([^}]+)\}\{([^}]+)\}\)?', r'\1/\2', clean_ans)
    clean_ans = clean_ans.replace(r'\(', '').replace(r'\)', '').replace(r'\[', '[').replace(r'\]', ']')

    found_cites = re.findall(r'\[(?:Pág\.|Página|Imagen en Pág\.|Pag\.)\s*(\d+)\]', clean_ans, re.IGNORECASE)
    
    # Extraer lista única de páginas citadas
    seen_pages = []
    for c in found_cites:
        p = int(c)
        if p not in seen_pages:
            seen_pages.append(p)

    # Si hay contexto documental y el LLM no puso [Pág. X], enlazar la página consultada
    if clean_context and not seen_pages and rag_info.get("retrieved_pages"):
        seen_pages = rag_info["retrieved_pages"][:3]
        if seen_pages and not re.search(r'\[(?:Pág\.|Página|Pag\.)\s*\d+\]', clean_ans):
            clean_ans = clean_ans.rstrip() + f" [Pág. {seen_pages[0]}]"

    target_page = seen_pages[0] if seen_pages else (rag_info["target_page"] if clean_context else 1)
    highlight_words = extract_highlight_words(req.prompt, clean_ans, rag_info["target_content"]) if clean_context else []

    # Si no se generaron sugerencias dinámicas, proporcionar sugerencias según el modo
    if not suggested_questions:
        if clean_context:
            suggested_questions = [
                f"¿Qué otros detalles contiene la página {target_page}?",
                "¿Cuáles son las conclusiones o pasos a seguir de este apartado?",
                "Explícame los conceptos técnicos más importantes de esta sección"
            ]
        else:
            suggested_questions = [
                "¿Qué temas de programación o tecnología dominas?",
                "¿Cómo funciona la indexación vectorial y OCR de PDFs?",
                "Genera un video explicativo sobre inteligencia artificial"
            ]

    return {
        "answer": clean_ans,
        "citations": seen_pages,
        "suggested_questions": suggested_questions[:3],
        "target_page": target_page,
        "target_file": rag_info["target_file"] or req.active_doc,
        "target_content": rag_info["target_content"] if clean_context else "",
        "highlight_words": highlight_words
    }

# --- RUTA DE SÍNTESIS ---

@app.post("/api/summary")
def summary_endpoint(req: SummaryRequest):
    """Genera una síntesis estructurada del documento completo con citas exactas por página."""
    full_text = get_document_full_text(req.filename)
    if not full_text:
        raise HTTPException(status_code=404, detail="El documento no tiene contenido para resumir.")

    prompt = (
        f"Elabora una síntesis ejecutiva estructurada y completa del documento '{req.filename}'.\n\n"
        "REGLAS CRÍTICAS DE CITACIÓN Y FORMATO:\n"
        "1. Estructura el resumen en secciones claras:\n"
        "   - 📌 Objetivo General del Documento\n"
        "   - 🔑 Puntos Clave y Temas Principales\n"
        "   - 🛠️ Procedimientos, Ejercicios o Casos de Estudio\n"
        "   - 📝 Conclusiones y Resultados Relevantes\n"
        "2. CITACIÓN OBLIGATORIA: En CADA sección, afirmación o punto clave, cita SIEMPRE entre corchetes la página exacta de donde proviene la información usando el formato [Pág. X] (por ejemplo: [Pág. 1], [Pág. 3]).\n"
        "3. Sé conciso, profesional y riguroso sin inventar datos.\n\n"
        f"CONTENIDO DEL DOCUMENTO CON NÚMEROS DE PÁGINA:\n{full_text[:14000]}"
    )
    sys_prompt = "Eres un analista documental riguroso. Siempre citas las páginas de origen usando el formato [Pág. X]."
    
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

