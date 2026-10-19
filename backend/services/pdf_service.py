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

    pdf_save_path = os.path.join(settings.UPLOADS_DIR, filename)
    with open(pdf_save_path, "wb") as f:
        f.write(file_bytes)

    chunks = []
    full_text = ""
    total_pages = len(doc)

    for idx in range(total_pages):
        pnum = idx + 1
        page = doc.load_page(idx)
        t = page.get_text() or ""
        clean_t = re.sub(r'(\w+)-\n(\w+)', r'\1\2', t)
        clean_t = re.sub(r'[ \t]+', ' ', clean_t).strip()

        # Si la página es escaneada o tiene poco texto, aplicamos OCR neural directo
        ocr_text = ""
        if len(clean_t) < 40 or analyze_images:
            try:
                pix_ocr = page.get_pixmap(dpi=150)
                ocr_text = extract_ocr_text_from_pixmap(pix_ocr)
            except Exception:
                pass

        # Análisis visual bajo demanda para la página (ilustraciones, fotos)
        img_descriptions = []
        if analyze_images:
            try:
                page_imgs = extract_images_from_pdf(doc, pnum)
                if not page_imgs and len(clean_t.strip()) < 30 and not ocr_text:
                    pix = page.get_pixmap(dpi=130)
                    img_bytes = pix.tobytes("jpeg")
                    page_imgs.append({
                        "format": "jpeg",
                        "bytes": img_bytes,
                        "width": pix.width,
                        "height": pix.height
                    })

                for img_idx, img in enumerate(page_imgs[:2]):
                    desc = describe_image_with_vision(img["bytes"], pnum, provider=provider, api_key=api_key)
                    if desc:
                        img_descriptions.append(f"[Gráfico #{img_idx+1}]: {desc}")
            except Exception:
                pass

        # Construcción de 1 CHUNK ÚNICO Y COMPLETO POR PÁGINA
        page_chunk_parts = []
        if clean_t:
            page_chunk_parts.append(clean_t)
        if ocr_text and ocr_text != clean_t:
            page_chunk_parts.append("Texto transcrito de la página (OCR):\n" + ocr_text)
        if img_descriptions:
            page_chunk_parts.append("Contenido visual e ilustraciones:\n" + "\n".join(img_descriptions))

        page_combined_content = "\n\n".join(page_chunk_parts).strip()
        if not page_combined_content:
            page_combined_content = f"Página {pnum} del documento sin texto ni elementos gráficos legibles."

        chunk_type = "hybrid" if (clean_t or ocr_text) and img_descriptions else ("image" if img_descriptions else "text")
        chunks.append({
            "text": page_combined_content,
            "page": pnum,
            "type": chunk_type
        })
        full_text += f"\n[PÁGINA {pnum}]:\n" + page_combined_content + "\n"

    if not chunks:
        chunks.append({
            "text": f"Documento '{filename}' con {len(doc)} páginas.",
            "page": 1,
            "type": "text"
        })

    # Preparar e insertar chunks con embeddings
    chunks_to_insert = []
    for idx, item in enumerate(chunks):
        emb_vec = generate_embedding(item["text"])
        chunks_to_insert.append({
            "page": item["page"],
            "index": idx,
            "type": item["type"],
            "text": item["text"],
            "embedding": emb_vec
        })

    db.insert_chunks(filename, chunks_to_insert)

    return {
        "filename": filename,
        "pages": total_pages,
        "chunks_indexed": len(chunks)
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
