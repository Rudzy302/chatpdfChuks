import re
from ..database import db
from .ai import generate_embedding

ALL_DOCS_OPTION = "Todos los documentos"

def is_global_query(prompt: str) -> bool:
    p = prompt.lower()
    global_terms = [
        "proceso", "procesos", "paso", "pasos", "actividad", "actividades",
        "etapa", "etapas", "metodologia", "metodología", "resumen", "sintesis",
        "síntesis", "todo", "todos", "completo", "completa", "totalidad",
        "cronologia", "cronología", "desarrollo", "que hicieron", "qué hicieron",
        "cuales fueron", "cuáles fueron", "conclusiones", "taller", "procedimiento"
    ]
    return any(re.search(r'\b' + re.escape(w) + r'\b', p) for w in global_terms) or any(w in p for w in ["que hicieron", "cuales fueron"])

def retrieve_rag_context(user_prompt: str, active_filename: str = "", top_k: int = 6):
    es_global = is_global_query(user_prompt)
    embedding_list = generate_embedding(user_prompt)
    top_chunks = db.search_similar_chunks(embedding_list, filename=active_filename, limit=top_k)

    target_file = ""
    target_page = 1
    target_content = ""

    if top_chunks:
        target_file = top_chunks[0][0]
        target_page = top_chunks[0][1]
        target_content = top_chunks[0][3]

    context_str = ""
    for r in top_chunks:
        p_prefix = "[Imagen en Pág." if r[4] == "image" else "[Pág."
        context_str += f"{p_prefix} {r[1]} - Archivo: {r[0]}]:\n{r[3]}\n\n"

    return {
        "context_text": context_str,
        "target_file": target_file,
        "target_page": target_page,
        "target_content": target_content,
        "is_global": es_global
    }

def extract_highlight_words(user_prompt: str, assistant_reply: str, chunk_content: str) -> list:
    words = set()
    for w in re.findall(r'\b[A-Za-z0-9_áéíóúÁÉÍÓÚñÑ]{3,}\b', assistant_reply):
        if w.lower() not in ["para", "como", "este", "esta", "estos", "estas", "sobre", "desde", "entre", "hacia", "hasta", "donde", "cuando", "porque", "pagina", "documento", "archivo", "claro", "aqui", "tienes", "informacion", "portada", "cita"]:
            words.add(w)

    if chunk_content:
        for w in re.findall(r'\b[A-Z][a-z0-9áéíóúñ]{3,}\b', chunk_content):
            words.add(w)
        for w in re.findall(r'\b[A-Z0-9_-]{4,}\b', chunk_content):
            words.add(w)

    for w in re.findall(r'\b[A-Za-z0-9_áéíóúÁÉÍÓÚñÑ]{4,}\b', user_prompt):
        if w.lower() not in ["puedes", "decir", "todos", "paso", "pasos", "realizados", "esta", "actividad", "citar", "desde"]:
            words.add(w)

    return [w for w in words if len(w) >= 3][:35]
