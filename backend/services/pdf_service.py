import os
import re
import json
import pymupdf
from ..config import settings
from ..database import db
from .ocr import extract_ocr_text_from_pixmap
from .ai import describe_image_with_vision, generate_embedding

def extract_images_from_pdf(doc, page_num: int):
    """Extrae imágenes incrustadas de una página, ignorando iconos minúsculos."""
    images = []
    page = doc.load_page(page_num - 1)
    image_list = page.get_images(full=True)
    for img_info in image_list:
        xref = img_info[0]
        base_img = doc.extract_image(xref)
        img_bytes = base_img["image"]
        w = base_img.get("width", 0)
        h = base_img.get("height", 0)
        if w >= 90 and h >= 90:
            images.append({
                "format": base_img.get("ext", "png"),
                "bytes": img_bytes,
                "width": w,
                "height": h
            })
    return images

def process_and_index_pdf(file_bytes: bytes, filename: str, provider: str = "Ollama (Local)", api_key: str = "", analyze_images: bool = True):
    """Procesa el PDF extrayendo texto digital, texto OCR e ilustraciones visuales (1 chunk consolidado por página)."""
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    if len(doc) > settings.MAX_PDF_PAGES:
        raise ValueError(f"El documento supera el límite de {settings.MAX_PDF_PAGES} páginas ({len(doc)} páginas).")

    # CACHÉ INSTANTÁNEO EN BASE DE DATOS:
    # Si el archivo ya fue indexado previamente en PostgreSQL/SQLite, reutilizar los chunks y vectores existentes
    existing_docs = db.get_indexed_documents()
    already_indexed = next((d for d in existing_docs if d["filename"] == filename and d.get("chunks", 0) > 0), None)
    
    pdf_save_path = os.path.join(settings.UPLOADS_DIR, filename)
    if not os.path.exists(pdf_save_path):
        with open(pdf_save_path, "wb") as f:
            f.write(file_bytes)

    if already_indexed:
        print(f"[CACHE] Documento '{filename}' ya indexado en base de datos ({already_indexed['chunks']} chunks). Retornando con preguntas dinámicas.")
        preview_text = get_document_full_text(filename)[:3000]
        cached_questions = []
        auto_summary = f"Documento '{filename}' cargado ({already_indexed['chunks']} páginas indexadas con vectores en base de datos)."
        try:
            from .ai import call_llm
            q_prompt = (
                f"El documento '{filename}' contiene este contenido:\n{preview_text}\n\n"
                "Genera exactamente 3 preguntas muy interesantes, específicas y concretas que un usuario haría sobre este contenido específico. "
                "Devuelve solo las 3 preguntas, una por línea, empezando con '-'."
            )
            q_res = call_llm(q_prompt, system_prompt="Eres un analista documental experto.", history=[], provider=provider, api_key=api_key)
            for line in q_res.split("\n"):
                cl = line.strip().lstrip("-").lstrip("0123456789.").strip()
                if cl and len(cl) > 8:
                    cached_questions.append(cl)
        except Exception:
            pass

        if len(cached_questions) < 3:
            cached_questions = [
                f"¿Qué objetivos y temas principales aborda {filename}?",
                "¿Cuáles son los pasos, conceptos o conclusiones más relevantes?",
                "¿Qué ejercicios, vulnerabilidades o datos técnicos detalla el documento?"
            ]

        return {
            "filename": filename,
            "pages": len(doc),
            "chunks_indexed": already_indexed["chunks"],
            "cached": True,
            "auto_summary": auto_summary,
            "suggested_questions": cached_questions[:3]
        }

    chunks = []
    full_text = ""
    total_pages = len(doc)

    from concurrent.futures import ThreadPoolExecutor

    def process_page(idx):
        pnum = idx + 1
        page = doc.load_page(idx)
        t = page.get_text() or ""
        clean_t = re.sub(r'(\w+)-\n(\w+)', r'\1\2', t)
        clean_t = re.sub(r'[ \t]+', ' ', clean_t).strip()

        # Optimización 1: OCR selectivo e inteligente
        # Solo ejecutar OCR si la página tiene poco texto digital legible (< 60 caracteres)
        ocr_text = ""
        if len(clean_t) < 60:
            try:
                pix_ocr = page.get_pixmap(dpi=130)
                ocr_text = extract_ocr_text_from_pixmap(pix_ocr)
            except Exception:
                pass

        # Optimización 2: Análisis visual únicamente si se solicita y si hay imágenes reales
        img_descriptions = []
        if analyze_images and (len(clean_t) < 40 or idx < 2):
            try:
                page_imgs = extract_images_from_pdf(doc, pnum)
                for img_idx, img in enumerate(page_imgs[:1]):
                    desc = describe_image_with_vision(img["bytes"], pnum, provider=provider, api_key=api_key)
                    if desc:
                        img_descriptions.append(f"[Ilustración #{img_idx+1}]: {desc}")
            except Exception:
                pass

        # 1 CHUNK ÚNICO Y COMPLETO POR PÁGINA
        page_chunk_parts = []
        if clean_t:
            page_chunk_parts.append(clean_t)
        if ocr_text and ocr_text != clean_t:
            page_chunk_parts.append("Texto transcrito (OCR):\n" + ocr_text)
        if img_descriptions:
            page_chunk_parts.append("Elementos visuales:\n" + "\n".join(img_descriptions))

        page_combined_content = "\n\n".join(page_chunk_parts).strip()
        if not page_combined_content:
            page_combined_content = f"Página {pnum} del documento sin texto legible."

        chunk_type = "hybrid" if (clean_t or ocr_text) and img_descriptions else ("image" if img_descriptions else "text")
        return {
            "text": page_combined_content,
            "page": pnum,
            "type": chunk_type
        }

    # Procesar páginas secuencialmente de forma ultra rápida
    for idx in range(total_pages):
        chunk_data = process_page(idx)
        chunks.append(chunk_data)
        full_text += f"\n[PÁGINA {chunk_data['page']}]:\n" + chunk_data["text"] + "\n"

    if not chunks:
        chunks.append({
            "text": f"Documento '{filename}' con {len(doc)} páginas.",
            "page": 1,
            "type": "text"
        })

    # Optimización 3: Generación paralela de embeddings con nomic-embed-text
    chunks_to_insert = [None] * len(chunks)
    def embed_chunk(item_idx):
        item = chunks[item_idx]
        emb_vec = generate_embedding(item["text"])
        chunks_to_insert[item_idx] = {
            "page": item["page"],
            "index": item_idx,
            "type": item["type"],
            "text": item["text"],
            "embedding": emb_vec
        }

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(embed_chunk, range(len(chunks))))

    db.insert_chunks(filename, chunks_to_insert)

    # 3 & 4. Resumen automático inicial y generación de preguntas para seguir la conversación
    auto_summary = ""
    suggested_questions = []
    try:
        from .ai import call_llm
        summary_prompt = (
            f"El documento '{filename}' acaba de ser indexado con {total_pages} páginas. "
            f"Lee los primeros fragmentos:\n{full_text[:5000]}\n\n"
            "Por favor, responde con dos secciones:\n"
            "RESUMEN:\n"
            "(Un resumen ejecutivo conciso de 3 a 5 puntos clave sobre qué trata el documento. En cada punto clave, cita la página de origen obligatoriamente con [Pág. X])\n\n"
            "PREGUNTAS SUGERIDAS:\n"
            "(Exactamente 3 preguntas interesantes y específicas sobre el tema del documento para continuar el chat. Cada pregunta en una línea empezando con '-')\n"
        )
        llm_reply = call_llm(
            prompt=summary_prompt,
            system_prompt="Eres un asistente analista de documentos eficiente y cordial.",
            history=[],
            provider=provider,
            api_key=api_key
        )
        
        # Separar resumen y preguntas
        if "PREGUNTAS SUGERIDAS:" in llm_reply:
            parts = llm_reply.split("PREGUNTAS SUGERIDAS:")
            auto_summary = parts[0].replace("RESUMEN:", "").strip()
            q_lines = parts[1].strip().split("\n")
            for q in q_lines:
                q_clean = q.strip().lstrip("-").lstrip("0123456789.").strip()
                if q_clean and len(q_clean) > 8:
                    suggested_questions.append(q_clean)
        else:
            auto_summary = llm_reply.strip()
    except Exception as e:
        auto_summary = f"Documento '{filename}' indexado exitosamente ({total_pages} páginas)."
        suggested_questions = ["¿De qué trata este documento?", "¿Cuáles son los puntos principales?"]

    if not suggested_questions:
        suggested_questions = [
            f"¿Cuál es el objetivo principal de {filename}?",
            "Explícame los conceptos más importantes",
            "¿Qué datos o conclusiones destacadas contiene?"
        ]

    return {
        "filename": filename,
        "pages": total_pages,
        "chunks_indexed": len(chunks),
        "auto_summary": auto_summary,
        "suggested_questions": suggested_questions[:3]
    }

def get_indexed_documents():
    """Obtiene el listado de documentos indexados en la base de datos."""
    return db.get_indexed_documents()

def delete_document(filename: str):
    """Elimina los fragmentos y el archivo físico del documento."""
    db.delete_document(filename)
    pdf_file = os.path.join(settings.UPLOADS_DIR, filename)
    if os.path.exists(pdf_file):
        os.remove(pdf_file)
    return True

def get_document_full_text(filename: str) -> str:
    """Reconstruye el texto completo del documento para síntesis."""
    return db.get_document_full_text(filename)
