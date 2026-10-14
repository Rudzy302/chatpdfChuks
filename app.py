import streamlit as st
import streamlit.components.v1 as components
import pg8000.native
import pymupdf  # Extracción rápida de texto e imágenes integradas
from langchain_text_splitters import RecursiveCharacterTextSplitter
import ollama
import io
import os
import re
import json
import base64
import urllib.request
import urllib.error
from PIL import Image

try:
    from rapidocr_onnxruntime import RapidOCR
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

@st.cache_resource
def get_ocr_engine():
    if OCR_AVAILABLE:
        try:
            return RapidOCR()
        except Exception:
            return None
    return None

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Document Studio",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_DIR = os.path.dirname(__file__)
UPLOADS_DIR = os.path.join(APP_DIR, "uploads")
CUSTOM_THEMES_FILE = os.path.join(APP_DIR, "custom_themes.json")
CONFIG_FILE = os.path.join(APP_DIR, "studio_config.json")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# --- DEFINICIÓN DE TEMAS BASE ---
DEFAULT_THEMES = {
    "Minimal Dark (Grafito)": {
        "bg_base": "#0f1115",
        "bg_card": "#161920",
        "bg_sidebar": "#12141a",
        "border": "#232733",
        "border_hover": "#363d4f",
        "accent": "#4f6bf5",
        "accent_light": "rgba(79, 107, 245, 0.15)",
        "text": "#f1f3f7",
        "text_muted": "#8d95a5"
    },
    "Minimal Light (Papel & Lino)": {
        "bg_base": "#f8f9fa",
        "bg_card": "#ffffff",
        "bg_sidebar": "#f1f3f5",
        "border": "#e5e7eb",
        "border_hover": "#d1d5db",
        "accent": "#2563eb",
        "accent_light": "rgba(37, 99, 235, 0.12)",
        "text": "#111827",
        "text_muted": "#6b7280"
    },
    "Nordic Slate (Pizarra)": {
        "bg_base": "#181d24",
        "bg_card": "#1e242d",
        "bg_sidebar": "#15191f",
        "border": "#2a323e",
        "border_hover": "#3d4858",
        "accent": "#0ea5e9",
        "accent_light": "rgba(14, 165, 233, 0.15)",
        "text": "#eef2f6",
        "text_muted": "#94a3b8"
    },
    "Monochrome (Noir)": {
        "bg_base": "#000000",
        "bg_card": "#0d0d0d",
        "bg_sidebar": "#080808",
        "border": "#222222",
        "border_hover": "#444444",
        "accent": "#e5e5e5",
        "accent_light": "rgba(229, 229, 229, 0.15)",
        "text": "#ffffff",
        "text_muted": "#a3a3a3"
    },
    "Matcha Olive (Calmo)": {
        "bg_base": "#121614",
        "bg_card": "#181e1b",
        "bg_sidebar": "#101412",
        "border": "#252f2a",
        "border_hover": "#37453e",
        "accent": "#10b981",
        "accent_light": "rgba(16, 185, 129, 0.15)",
        "text": "#ecfdf5",
        "text_muted": "#86efac"
    }
}

def load_custom_themes():
    if os.path.exists(CUSTOM_THEMES_FILE):
        try:
            with open(CUSTOM_THEMES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_custom_themes(themes_dict):
    try:
        with open(CUSTOM_THEMES_FILE, "w", encoding="utf-8") as f:
            json.dump(themes_dict, f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error guardando tema: {e}")

if "saved_custom_themes" not in st.session_state:
    st.session_state.saved_custom_themes = load_custom_themes()

ALL_THEMES = dict(DEFAULT_THEMES)
ALL_THEMES.update(st.session_state.saved_custom_themes)

# --- ESTADOS DE SESIÓN ---
if "app_theme" not in st.session_state:
    st.session_state.app_theme = "Minimal Dark (Grafito)"
if "show_chat" not in st.session_state:
    st.session_state.show_chat = True
if "show_pdf" not in st.session_state:
    st.session_state.show_pdf = True
if "show_summary" not in st.session_state:
    st.session_state.show_summary = False
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola. Document Studio está listo para responder consultas sobre tus PDFs. Toda respuesta citará la página exacta con acceso directo y resaltado en el documento."}
    ]
if "active_doc" not in st.session_state:
    st.session_state.active_doc = ""
if "file_name" not in st.session_state:
    st.session_state.file_name = ""
if "file_bytes" not in st.session_state:
    st.session_state.file_bytes = None
if "full_doc_text" not in st.session_state:
    st.session_state.full_doc_text = ""
if "active_page" not in st.session_state:
    st.session_state.active_page = 1
if "highlight_words" not in st.session_state:
    st.session_state.highlight_words = []
if "summary" not in st.session_state:
    st.session_state.summary = ""

# Parámetros RAG y Modelo (Ajustables debajo del chat)
if "chunk_size" not in st.session_state:
    st.session_state.chunk_size = 550
if "chunk_overlap" not in st.session_state:
    st.session_state.chunk_overlap = 80
if "top_k_chunks" not in st.session_state:
    st.session_state.top_k_chunks = 6
if "ai_provider" not in st.session_state:
    st.session_state.ai_provider = "Ollama (Local)"  # "Ollama (Local)", "Llama.cpp Server (Local)", "Google Gemini (Nube)", "OpenAI / Groq API (Nube)"
if "local_model" not in st.session_state:
    st.session_state.local_model = "qwen2.5:7b"
if "cloud_api_key" not in st.session_state:
    st.session_state.cloud_api_key = os.environ.get("GEMINI_API_KEY", "")
if "cloud_model_name" not in st.session_state:
    st.session_state.cloud_model_name = "gemini-1.5-flash"
if "llamacpp_url" not in st.session_state:
    st.session_state.llamacpp_url = "http://localhost:8080/v1"

# Paleta viva
if "live_custom" not in st.session_state:
    st.session_state.live_custom = {
        "bg_base": "#12141a",
        "bg_card": "#181b22",
        "bg_sidebar": "#101217",
        "border": "#272b38",
        "border_hover": "#3a4154",
        "accent": "#3b82f6",
        "accent_light": "rgba(59, 130, 246, 0.15)",
        "text": "#f3f4f6",
        "text_muted": "#9ca3af"
    }

if st.session_state.app_theme == "🎨 Personalizado":
    current_theme = st.session_state.live_custom
else:
    current_theme = ALL_THEMES.get(st.session_state.app_theme, DEFAULT_THEMES["Minimal Dark (Grafito)"])

# Estilos CSS Minimalistas
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    :root {{
        --bg-base: {current_theme['bg_base']};
        --bg-card: {current_theme['bg_card']};
        --bg-sidebar: {current_theme['bg_sidebar']};
        --border: {current_theme['border']};
        --border-hover: {current_theme['border_hover']};
        --accent: {current_theme['accent']};
        --accent-light: {current_theme['accent_light']};
        --text: {current_theme['text']};
        --text-muted: {current_theme['text_muted']};
    }}

    html, body, [data-testid="stAppViewContainer"] {{
        background-color: var(--bg-base) !important;
        color: var(--text) !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        height: 100vh !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border) !important;
    }}

    header[data-testid="stHeader"] {{
        display: none !important;
    }}

    section.main > .block-container {{
        padding: 0.5rem 1.1rem !important;
        max-width: 100% !important;
        min-height: 100vh !important;
        display: flex !important;
        flex-direction: column !important;
    }}

    /* Estabilidad de scroll en el chat sin rebotes o saltos */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        overflow-anchor: none !important;
    }}
    div[data-testid="stVerticalBlock"] > div[style*="overflow-y"] {{
        scroll-behavior: smooth !important;
        overscroll-behavior-y: contain !important;
    }}

    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: transparent;
    }}
    ::-webkit-scrollbar-thumb {{
        background: var(--border);
        border-radius: 4px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: var(--border-hover);
    }}

    /* Botones limpios */
    div.stButton > button {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 6px !important;
        font-size: 0.83rem !important;
        font-weight: 500 !important;
        padding: 5px 11px !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
    }}
    div.stButton > button:hover {{
        border-color: var(--border-hover) !important;
        background-color: rgba(255, 255, 255, 0.04) !important;
    }}

    /* Botón activo */
    div.stButton > button[kind="primary"] {{
        background-color: var(--accent) !important;
        border: 1px solid var(--accent) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }}
    div.stButton > button[kind="primary"]:hover {{
        filter: brightness(1.1);
    }}

    /* Mensajes de conversación */
    [data-testid="stChatMessage"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 0.9rem 1.1rem !important;
        margin-bottom: 0.55rem !important;
        font-size: 0.91rem !important;
        line-height: 1.58 !important;
        box-shadow: none !important;
    }}
    [data-testid="stChatMessage"]:hover {{
        border-color: var(--border-hover) !important;
    }}

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {{
        border-left: 3px solid var(--accent) !important;
    }}

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
        background-color: var(--accent-light) !important;
        border-color: var(--border) !important;
    }}

    /* Entrada de Chat */
    [data-testid="stChatInput"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 4px !important;
        box-shadow: none !important;
    }}
    [data-testid="stChatInput"]:focus-within {{
        border-color: var(--accent) !important;
    }}

    /* Barra inferior estilo ChatGPT para parámetros */
    .chat-settings-bar {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 8px;
        font-size: 0.78rem;
        color: var(--text-muted);
        border-top: 1px solid var(--border);
        margin-top: 4px;
    }}

    .summary-box {{
        background-color: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 18px;
        height: 720px;
        overflow-y: auto;
        font-size: 0.91rem;
        line-height: 1.62;
        color: var(--text);
    }}

    /* Enlaces a citas clickeables en markdown */
    a.doc-cite-link {{
        color: var(--accent) !important;
        font-weight: 600;
        text-decoration: underline;
        cursor: pointer;
        background-color: var(--accent-light);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.85rem;
    }}
</style>
""", unsafe_allow_html=True)


# --- CONEXIÓN PG8000 & BASE DE DATOS ---
def get_db():
    return pg8000.native.Connection(
        user="admin", password="admin", host="localhost", port=5433, database="rag_db", timeout=5
    )

@st.cache_resource
def setup_database_cached():
    try:
        con = get_db()
        con.run("CREATE EXTENSION IF NOT EXISTS vector;")
        con.run("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                filename TEXT,
                page_number INT DEFAULT 1,
                chunk_index INT,
                chunk_type TEXT DEFAULT 'text',
                content TEXT,
                embedding vector(768)
            );
        """)
        con.run("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS chunk_type TEXT DEFAULT 'text';")
        con.run("CREATE INDEX IF NOT EXISTS idx_doc_chunks_filename ON document_chunks (filename);")
        con.close()
        return True
    except Exception:
        return False

@st.cache_data(ttl=15)
def get_indexed_documents():
    try:
        con = get_db()
        rows = con.run("""
            SELECT filename, count(*), min(page_number), max(page_number)
            FROM document_chunks
            GROUP BY filename
            ORDER BY filename;
        """)
        con.close()
        return [{"filename": r[0], "chunks": r[1], "min_page": r[2] or 1, "max_page": r[3] or 1} for r in rows]
    except Exception:
        return []

def delete_document_from_db(filename):
    try:
        con = get_db()
        con.run("DELETE FROM document_chunks WHERE filename = :fname;", fname=filename)
        con.close()
        pdf_file = os.path.join(UPLOADS_DIR, filename)
        if os.path.exists(pdf_file):
            os.remove(pdf_file)
        get_indexed_documents.clear()
        load_pdf_data.clear()
        return True
    except Exception:
        return False

@st.cache_data(max_entries=10)
def load_pdf_data(filename):
    pdf_path = os.path.join(UPLOADS_DIR, filename)
    file_bytes = None
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()

    full_text = ""
    try:
        con = get_db()
        rows = con.run("""
            SELECT page_number, content, chunk_type
            FROM document_chunks
            WHERE filename = :fname
            ORDER BY page_number ASC, chunk_index ASC;
        """, fname=filename)
        con.close()
        for pnum, content, ctype in rows:
            prefix = "[IMAGEN PÁG." if ctype == "image" else "[PÁGINA"
            full_text += f"\n{prefix} {pnum}]:\n" + content + "\n"
    except Exception:
        pass

    return file_bytes, full_text

# --- EXTRACCIÓN AVANZADA: TEXTO + IMÁGENES EMBEBIDAS CON PYMUPDF ---
def extract_images_from_pdf(doc, page_num):
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
        # Filtrar logos o iconos minúsculos (< 90x90)
        if w >= 90 and h >= 90:
            images.append({
                "format": base_img.get("ext", "png"),
                "bytes": img_bytes,
                "width": w,
                "height": h
            })
    return images

def prepare_image_for_vision(img_bytes: bytes, max_dim: int = 512) -> str:
    """Redimensiona y optimiza imagen en memoria para inferencia visual ultrarrápida."""
    try:
        im = Image.open(io.BytesIO(img_bytes))
        im.thumbnail((max_dim, max_dim))
        if im.mode in ("RGBA", "P"):
            im = im.convert("RGB")
        out_buf = io.BytesIO()
        im.save(out_buf, format="JPEG", quality=82, optimize=True)
        return base64.b64encode(out_buf.getvalue()).decode("utf-8")
    except Exception:
        return base64.b64encode(img_bytes).decode("utf-8")

def extract_ocr_text_from_pixmap(pix) -> str:
    """Extrae texto literal y matemático de una página o imagen usando RapidOCR."""
    engine = get_ocr_engine()
    if not engine:
        return ""
    try:
        img_bytes = pix.tobytes("png")
        result, _ = engine(img_bytes)
        if result:
            lines = [line[1].strip() for line in result if len(line[1].strip()) > 0]
            return "\n".join(lines)
    except Exception:
        pass
    return ""

def describe_image_with_vision(img_bytes, page_num, provider="Ollama (Local)", api_key=""):
    """Genera descripción o transcripción de elementos visuales (animales, plantas, diagramas o texto en imágenes)."""
    # 1. Google Gemini (si está activo el provider o configurado)
    if "Gemini" in provider and api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            b64_data = prepare_image_for_vision(img_bytes, max_dim=800)
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Analiza esta imagen con precisión. Si contiene texto, ejercicios, fracciones o fórmulas matemáticas, transcríbelas todas literalmente con su formato. Si muestra animales o plantas, indica la raza, tipo y colores. En español."},
                        {"inline_data": {"mime_type": "image/jpeg", "data": b64_data}}
                    ]
                }],
                "generationConfig": {"maxOutputTokens": 350, "temperature": 0.1}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    # 2. Inferencia local Ollama
    b64_data = prepare_image_for_vision(img_bytes, max_dim=768)
    vision_prompt = (
        "Analyze this image carefully. If it contains text, worksheets, questions or math fractions, "
        "transcribe all the headings, letters (a, b, c...), equations and fractions you see. "
        "If it is a picture of an animal or plant, identify the breed or subject and colors."
    )

    try:
        res = ollama.generate(
            model="llava:7b",
            prompt=vision_prompt,
            images=[b64_data],
            options={"num_predict": 180, "temperature": 0.1}
        )
        ans = res.get("response", "").strip()
        if ans and len(ans) > 5:
            return ans
    except Exception:
        pass

    return f"Fotografía o ilustración en la página {page_num}."

def process_pdf(file_bytes, filename, chunk_size=550, chunk_overlap=80, provider="Ollama (Local)", api_key="", analyze_images=True, progress_cb=None):
    """Procesa el PDF extrayendo texto digital, texto OCR e ilustraciones visuales (hasta 30 páginas)."""
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    if len(doc) > 30:
        return None, f"El documento supera el límite de 30 páginas ({len(doc)} páginas)."

    pdf_save_path = os.path.join(UPLOADS_DIR, filename)
    with open(pdf_save_path, "wb") as f:
        f.write(file_bytes)

    chunks = []
    full_text = ""
    total_pages = len(doc)

    for idx in range(total_pages):
        pnum = idx + 1
        if progress_cb:
            progress_cb((idx + 1) / (total_pages + 1), f"Procesando página {pnum} de {total_pages}...")

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
                # Si no hay imágenes individuales embebidas pero la página no tiene texto digital, evaluar la página como imagen
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

        # Guardar 1 chunk por página
        chunk_type = "hybrid" if (clean_t or ocr_text) and img_descriptions else ("image" if img_descriptions else "text")
        chunks.append({
            "text": page_combined_content,
            "page": pnum,
            "type": chunk_type
        })

        # Acumular para el documento completo
        full_text += f"\n[PÁGINA {pnum}]:\n" + page_combined_content + "\n"

    if not chunks:
        chunks.append({
            "text": f"Documento '{filename}' con {len(doc)} páginas.",
            "page": 1,
            "type": "text"
        })

    return chunks, full_text


# --- MOTORES DE INFERENCIA: LOCAL & NUBE ---
def generate_embedding(text: str) -> list:
    """Genera vector de 768 dimensiones con nomic-embed-text o embedding sintético normalizado si el servidor no responde."""
    try:
        embed_res = ollama.embeddings(model="nomic-embed-text", prompt=text)
        return embed_res["embedding"]
    except Exception:
        # Vector determinista normalizado basado en hash para evitar romper el flujo si Ollama local está apagado
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [(float(b) / 255.0) - 0.5 for b in h]
        while len(vec) < 768:
            vec.extend(vec[:768 - len(vec)])
        return vec[:768]

def call_llm(prompt: str, system_prompt: str, history: list) -> str:
    """Ejecuta consulta según el proveedor configurado (Ollama, Llama.cpp o Nube/Gemini/OpenAI)."""
    provider = st.session_state.ai_provider
    api_key = st.session_state.cloud_api_key.strip()

    # 1. Google Gemini (Nube)
    if provider == "Google Gemini (Nube)":
        if not api_key:
            return "⚠️ Debes ingresar tu API Key de Google Gemini en el panel de configuración inferior (debajo del chat)."
        try:
            model_name = st.session_state.cloud_model_name or "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            # Estructurar historial
            contents = []
            contents.append({"role": "user", "parts": [{"text": f"Instrucciones del sistema:\n{system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Entendido, seguiré estrictamente las instrucciones y citaré [Pág. X]."}]})
            for m in history:
                role = "user" if m["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m["content"]}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            payload = {
                "contents": contents,
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            return f"Error en Google Gemini API ({e.code}): {err_msg}"
        except Exception as e:
            return f"Error al conectar con Google Gemini: {e}"

    # 2. Llama.cpp Server (API Compatible OpenAI)
    elif provider == "Llama.cpp Server (Local)":
        endpoint = st.session_state.llamacpp_url.rstrip("/") + "/chat/completions"
        try:
            recent_history = history[-4:] if len(history) > 4 else history
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend([{"role": m["role"], "content": m["content"]} for m in recent_history])
            messages.append({"role": "user", "content": prompt})

            payload = {
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 800
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Error al conectar con llama.cpp en {endpoint}. Asegúrate de haber iniciado 'llama-server': {e}"

    # 3. OpenAI / Groq / APIs compatibles (Nube)
    elif provider == "OpenAI / Groq API (Nube)":
        if not api_key:
            return "⚠️ Ingresa tu API Key de OpenAI / Groq en el menú de configuración inferior."
        try:
            endpoint = "https://api.openai.com/v1/chat/completions"
            model_target = "gpt-4o-mini"
            if api_key.startswith("gsk_"):  # Detección automática de Groq
                endpoint = "https://api.groq.com/openai/v1/chat/completions"
                model_target = "llama-3.1-8b-instant"

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend([{"role": m["role"], "content": m["content"]} for m in history])
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": model_target,
                "messages": messages,
                "temperature": 0.2
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Error en API Cloud: {e}"

    # 4. Ollama (Local por defecto)
    else:
        try:
            recent_history = history[-4:] if len(history) > 4 else history
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend([{"role": m["role"], "content": m["content"]} for m in recent_history])
            messages.append({"role": "user", "content": prompt})

            resp = ollama.chat(
                model=st.session_state.local_model,
                messages=messages
            )
            return resp["message"]["content"]
        except Exception as e:
            return f"Error al consultar Ollama local: {e}. Comprueba que el servicio de Ollama esté ejecutándose (`ollama serve`)."


# --- RECUPERACIÓN RAG INTELIGENTE ---
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

def retrieve_rag_context(user_prompt: str, active_filename: str):
    es_global = is_global_query(user_prompt)
    con = get_db()

    embedding_list = generate_embedding(user_prompt)
    query_vector = json.dumps(embedding_list)
    limit_chunks = st.session_state.top_k_chunks

    if active_filename and active_filename != ALL_DOCS_OPTION:
        sql = """
            SELECT filename, page_number, chunk_index, content, chunk_type, (embedding <=> :emb::vector) AS dist
            FROM document_chunks
            WHERE filename = :fname
            ORDER BY dist ASC
            LIMIT :lim;
        """
        top_chunks = con.run(sql, emb=query_vector, fname=active_filename, lim=limit_chunks)
    else:
        sql = """
            SELECT filename, page_number, chunk_index, content, chunk_type, (embedding <=> :emb::vector) AS dist
            FROM document_chunks
            ORDER BY dist ASC
            LIMIT :lim;
        """
        top_chunks = con.run(sql, emb=query_vector, lim=limit_chunks)
    con.close()

    target_file = ""
    target_page = 1
    target_content = ""

    if top_chunks:
        target_file = top_chunks[0][0]
        target_page = top_chunks[0][1]
        target_content = top_chunks[0][3]

    context_str = ""
    if es_global:
        if active_filename and active_filename != ALL_DOCS_OPTION and st.session_state.full_doc_text:
            context_str += f"=== TEXTO COMPLETO ('{active_filename}') ===\n"
            context_str += st.session_state.full_doc_text[:18000] + "\n\n"
        else:
            context_str += "=== CONTEXTO MULTI-DOCUMENTO ===\n"

        for r in top_chunks:
            p_prefix = "[Imagen en Pág." if r[4] == "image" else "[Pág."
            context_str += f"{p_prefix} {r[1]}]:\n{r[3]}\n\n"
    else:
        for r in top_chunks:
            p_prefix = "[Imagen en Pág." if r[4] == "image" else "[Pág."
            context_str += f"{p_prefix} {r[1]}]:\n{r[3]}\n\n"

    return context_str, target_file, target_page, target_content

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


# --- VISOR DOCUMENTAL MINIMALISTA (PDF.JS EMBEBIDO) ---
@st.cache_data(max_entries=5)
def render_continuous_pdf_viewer_html(file_bytes: bytes, target_page: int, highlight_words: list, theme: dict) -> str:
    b64_pdf = base64.b64encode(file_bytes).decode("utf-8")
    words_json = json.dumps(highlight_words)
    v_bg_base = theme.get("bg_base", "#12141a")
    v_bg_card = theme.get("bg_card", "#181b22")
    v_border = theme.get("border", "#272b38")
    v_accent = theme.get("accent", "#3b82f6")
    v_text = theme.get("text", "#f3f4f6")
    v_text_muted = theme.get("text_muted", "#9ca3af")

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf_viewer.min.css">
      <style>
        * {{ box-sizing: border-box; }}
        body, html {{
          margin: 0;
          padding: 0;
          width: 100%;
          height: 100%;
          background: {v_bg_base};
          color: {v_text};
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          overflow: hidden;
        }}
        #pdf-toolbar {{
          height: 38px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 14px;
          background: {v_bg_card};
          border-bottom: 1px solid {v_border};
          font-size: 12px;
        }}
        .btn {{
          background: transparent;
          border: 1px solid {v_border};
          color: {v_text};
          padding: 3px 9px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 500;
          transition: background 0.15s ease;
        }}
        .btn:hover {{
          background: rgba(255, 255, 255, 0.08);
          border-color: {v_accent};
        }}
        #scroll-viewport {{
          height: calc(100% - 38px);
          overflow-y: auto;
          overflow-x: auto;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 20px 10px;
          gap: 20px;
          background: {v_bg_base};
          scroll-behavior: smooth;
        }}
        .page-card {{
          position: relative;
          background: #ffffff;
          box-shadow: 0 4px 14px rgba(0,0,0,0.4);
          border-radius: 4px;
          display: inline-block;
          margin: 0 auto;
        }}
        .page-card-header {{
          position: absolute;
          top: -10px;
          right: 12px;
          background: {v_bg_card};
          color: {v_text_muted};
          font-size: 11px;
          font-weight: 600;
          padding: 2px 8px;
          border-radius: 4px;
          border: 1px solid {v_border};
          z-index: 10;
        }}
        canvas {{
          display: block;
          border-radius: 4px;
        }}
        .textLayer {{
          position: absolute;
          left: 0;
          top: 0;
          right: 0;
          bottom: 0;
          overflow: hidden;
          opacity: 1 !important;
          line-height: 1.0;
        }}
        .textLayer span {{
          color: transparent !important;
          position: absolute;
          white-space: pre;
          cursor: text;
          transform-origin: 0% 0%;
        }}
        /* SUBRAYADO CON MARCADOR FLUORESCENTE EN EL PDF */
        .pdf-highlight-mark {{
          background-color: rgba(254, 240, 138, 0.78) !important;
          outline: 2px solid rgba(234, 179, 8, 0.9) !important;
          border-radius: 2px !important;
          box-shadow: 0 0 6px rgba(234, 179, 8, 0.5) !important;
        }}
      </style>
    </head>
    <body>
      <div id="pdf-toolbar">
        <div style="font-size: 12px; font-weight: 500; color: {v_text_muted}; display: flex; align-items: center; gap: 6px;">
          <span>Documento Original</span>
        </div>
        <div style="display: flex; align-items: center; gap: 6px;">
          <button class="btn" id="btn-zoom-out" title="Reducir">-</button>
          <span id="zoom-text" style="font-size: 11px; color: {v_text_muted}; min-width: 36px; text-align: center;">105%</span>
          <button class="btn" id="btn-zoom-in" title="Aumentar">+</button>
        </div>
      </div>

      <div id="scroll-viewport">
        <div id="loading-msg" style="color: {v_text_muted}; font-size: 13px; margin-top: 40px;">
          Cargando documento...
        </div>
      </div>

      <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

        const pdfBase64 = "{b64_pdf}";
        const targetPageNum = {target_page} || 1;
        const highlightWords = {words_json};

        let pdfDoc = null;
        let scale = 1.05;
        let pagesRenderedCount = 0;
        let totalPages = 0;
        let targetFirstMatch = null;

        const scrollContainer = document.getElementById('scroll-viewport');

        function renderAllPages() {{
          scrollContainer.innerHTML = '';
          pagesRenderedCount = 0;
          targetFirstMatch = null;
          totalPages = pdfDoc.numPages;

          for (let p = 1; p <= totalPages; p++) {{
            const pageCard = document.createElement('div');
            pageCard.className = 'page-card';
            pageCard.id = `page-card-${{p}}`;

            const badge = document.createElement('div');
            badge.className = 'page-card-header';
            badge.textContent = `Pág. ${{p}} de ${{totalPages}}`;
            pageCard.appendChild(badge);

            const canvas = document.createElement('canvas');
            canvas.id = `canvas-${{p}}`;
            pageCard.appendChild(canvas);

            const textLayer = document.createElement('div');
            textLayer.className = 'textLayer';
            textLayer.id = `text-layer-${{p}}`;
            pageCard.appendChild(textLayer);

            scrollContainer.appendChild(pageCard);
            renderPage(p, canvas, textLayer, pageCard);
          }}
        }}

        function renderPage(num, canvas, textLayer, pageCard) {{
          pdfDoc.getPage(num).then(function(page) {{
            const viewport = page.getViewport({{ scale: scale }});
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            pageCard.style.width = viewport.width + 'px';
            textLayer.style.width = viewport.width + 'px';
            textLayer.style.height = viewport.height + 'px';

            const ctx = canvas.getContext('2d');
            const renderTask = page.render({{
              canvasContext: ctx,
              viewport: viewport
            }});

            renderTask.promise.then(function() {{
              return page.getTextContent();
            }}).then(function(textContent) {{
              pdfjsLib.renderTextLayer({{
                textContentSource: textContent,
                container: textLayer,
                viewport: viewport,
                textDivs: []
              }}).promise.then(function() {{
                applyHighlights(textLayer, num);
                pagesRenderedCount++;
                if (pagesRenderedCount === totalPages) {{
                  scrollToTargetPage();
                }}
              }});
            }});
          }});
        }}

        function applyHighlights(textLayer, pageNum) {{
          if (!highlightWords || highlightWords.length === 0) return;
          const spans = textLayer.getElementsByTagName('span');
          const terms = highlightWords
            .map(w => w.trim().toLowerCase())
            .filter(w => w.length >= 3);

          if (terms.length === 0) return;

          for (let i = 0; i < spans.length; i++) {{
            const sText = spans[i].textContent.toLowerCase();
            let matched = false;
            for (let t of terms) {{
              if (sText.includes(t) || (sText.length >= 3 && t.includes(sText))) {{
                matched = true;
                break;
              }}
            }}
            if (matched) {{
              spans[i].classList.add('pdf-highlight-mark');
              if (pageNum === targetPageNum && !targetFirstMatch) {{
                targetFirstMatch = spans[i];
              }}
            }}
          }}
        }}

        function scrollToTargetPage() {{
          setTimeout(() => {{
            if (targetFirstMatch) {{
              targetFirstMatch.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            }} else {{
              const card = document.getElementById(`page-card-${{targetPageNum}}`);
              if (card) {{
                card.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
              }}
            }}
          }}, 160);
        }}

        document.getElementById('btn-zoom-in').onclick = () => {{
          scale = Math.min(scale + 0.15, 2.0);
          document.getElementById('zoom-text').textContent = Math.round(scale * 100) + '%';
          renderAllPages();
        }};

        document.getElementById('btn-zoom-out').onclick = () => {{
          scale = Math.max(scale - 0.15, 0.7);
          document.getElementById('zoom-text').textContent = Math.round(scale * 100) + '%';
          renderAllPages();
        }};

        const raw = atob(pdfBase64);
        const uint8 = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; i++) uint8[i] = raw.charCodeAt(i);

        pdfjsLib.getDocument({{ data: uint8 }}).promise.then(function(doc) {{
          pdfDoc = doc;
          renderAllPages();
        }}).catch(function(err) {{
          scrollContainer.innerHTML = '<div style="color: #ef4444; padding: 20px;">Error al cargar el archivo.</div>';
          console.error(err);
        }});
      </script>
    </body>
    </html>
    """
    return html_code


# --- BARRA LATERAL (MINIMALISTA) ---
with st.sidebar:
    st.markdown("""
        <div style="margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border);">
            <div style="font-weight: 600; font-size: 1.05rem; letter-spacing: -0.01em; color: var(--text);">Document Studio</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">Consultas y navegación textual + visual</div>
        </div>
    """, unsafe_allow_html=True)

    setup_database_cached()
    indexed_docs = get_indexed_documents()
    doc_names = [d["filename"] for d in indexed_docs]

    # Carga automática del primer documento
    if doc_names and (not st.session_state.file_bytes or not st.session_state.active_doc):
        first_doc = doc_names[0]
        st.session_state.active_doc = first_doc
        st.session_state.file_name = first_doc
        b, txt = load_pdf_data(first_doc)
        st.session_state.file_bytes = b
        st.session_state.full_doc_text = txt
        st.session_state.active_page = 1

    st.markdown("<div style='font-size: 0.78rem; font-weight: 600; color: var(--text-muted); margin-bottom: 4px;'>DOCUMENTO ACTIVO</div>", unsafe_allow_html=True)
    if doc_names:
        options = [ALL_DOCS_OPTION] + doc_names
        curr_idx = options.index(st.session_state.active_doc) if st.session_state.active_doc in options else 1

        selected_doc = st.selectbox(
            "Documento:",
            options=options,
            index=curr_idx,
            label_visibility="collapsed"
        )

        if selected_doc == ALL_DOCS_OPTION:
            if st.session_state.active_doc != ALL_DOCS_OPTION:
                st.session_state.active_doc = ALL_DOCS_OPTION
        else:
            if selected_doc != st.session_state.active_doc or not st.session_state.file_bytes:
                st.session_state.active_doc = selected_doc
                st.session_state.file_name = selected_doc
                b, txt = load_pdf_data(selected_doc)
                st.session_state.file_bytes = b
                st.session_state.full_doc_text = txt
                st.session_state.active_page = 1

        if selected_doc != ALL_DOCS_OPTION:
            if st.button("Eliminar documento", use_container_width=True):
                delete_document_from_db(selected_doc)
                st.session_state.active_doc = ALL_DOCS_OPTION
                st.session_state.file_name = ""
                st.session_state.file_bytes = None
                st.session_state.full_doc_text = ""
                st.rerun()
    else:
        st.caption("No hay documentos indexados.")

    st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)

    # Subida de archivo
    st.markdown("<div style='font-size: 0.78rem; font-weight: 600; color: var(--text-muted); margin-bottom: 4px;'>CARGAR PDF (HASTA 30 PÁGS)</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "PDF:",
        type=["pdf"],
        label_visibility="collapsed"
    )

    analyze_imgs_opt = st.checkbox("Analizar imágenes con IA de visión", value=True, help="Desactiva si el PDF solo contiene texto para indexar en menos de 2 segundos.")

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        if st.button("Procesar e indexar", use_container_width=True):
            prog_bar = st.progress(0, text="Iniciando procesamiento...")
            def update_prog(pct, msg):
                prog_bar.progress(min(pct, 0.95), text=msg)

            chunks_res, full_text_res = process_pdf(
                file_bytes=file_bytes,
                filename=uploaded_file.name,
                chunk_size=st.session_state.chunk_size,
                chunk_overlap=st.session_state.chunk_overlap,
                provider=st.session_state.ai_provider,
                api_key=st.session_state.cloud_api_key,
                analyze_images=analyze_imgs_opt,
                progress_cb=update_prog
            )

            if chunks_res is None:
                st.error(full_text_res)
            else:
                try:
                    prog_bar.progress(0.96, text="Guardando vectores en base de datos...")
                    con = get_db()
                    con.run("DELETE FROM document_chunks WHERE filename = :fname;", fname=uploaded_file.name)
                    
                    # Generar embeddings e insertar
                    for idx, item in enumerate(chunks_res):
                        emb_vec = generate_embedding(item["text"])
                        con.run(
                            """
                            INSERT INTO document_chunks (filename, page_number, chunk_index, chunk_type, content, embedding)
                            VALUES (:fname, :pnum, :cidx, :ctype, :cont, :emb::vector);
                            """,
                            fname=uploaded_file.name,
                            pnum=item["page"],
                            cidx=idx,
                            ctype=item.get("type", "text"),
                            cont=item["text"],
                            emb=json.dumps(emb_vec)
                        )
                    con.close()

                    # Resumen diferido (bajo demanda en el panel de resumen para máxima velocidad de subida)
                    st.session_state.summary = ""

                    # Limpiar caches para reflejar el nuevo documento inmediatamente
                    get_indexed_documents.clear()
                    load_pdf_data.clear()
                    render_continuous_pdf_viewer_html.clear()

                    st.session_state.file_bytes = file_bytes
                    st.session_state.file_name = uploaded_file.name
                    st.session_state.active_doc = uploaded_file.name
                    st.session_state.full_doc_text = full_text_res
                    st.session_state.active_page = 1
                    prog_bar.progress(1.0, text="¡Completado!")
                    st.success("¡Documento indexado con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Acciones de sesión
    st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
    if st.button("Limpiar conversación", use_container_width=True):
        st.session_state.messages = [
            {"role": "assistant", "content": "Conversación reiniciada. ¿Qué consulta deseas realizar?"}
        ]
        st.session_state.highlight_words = []
        st.rerun()

    # --- SECCIÓN DE TEMAS Y PERSONALIZACIÓN COMPLETA ---
    st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.78rem; font-weight: 600; color: var(--text-muted); margin-bottom: 6px;'>APARIENCIA & TEMAS</div>", unsafe_allow_html=True)

    theme_options = list(ALL_THEMES.keys()) + ["🎨 Personalizado"]
    current_selected_idx = theme_options.index(st.session_state.app_theme) if st.session_state.app_theme in theme_options else 0

    theme_pick = st.selectbox(
        "Tema:",
        options=theme_options,
        index=current_selected_idx,
        label_visibility="collapsed"
    )

    if theme_pick != st.session_state.app_theme:
        st.session_state.app_theme = theme_pick
        if theme_pick in ALL_THEMES:
            st.session_state.live_custom = dict(ALL_THEMES[theme_pick])
        st.rerun()

    # Panel de personalización interactiva
    if st.session_state.app_theme == "🎨 Personalizado":
        with st.expander("🛠️ Personalizador de Paleta", expanded=True):
            st.caption("Selecciona con el cuentagotas/paleta los colores exactos para cada elemento:")

            c_col1, c_col2 = st.columns(2)
            with c_col1:
                new_bg_base = st.color_picker("Fondo principal", st.session_state.live_custom["bg_base"])
                new_bg_card = st.color_picker("Tarjetas / Bloques", st.session_state.live_custom["bg_card"])
                new_bg_sidebar = st.color_picker("Barra lateral", st.session_state.live_custom["bg_sidebar"])
                new_border = st.color_picker("Bordes", st.session_state.live_custom["border"])

            with c_col2:
                new_text = st.color_picker("Texto principal", st.session_state.live_custom["text"])
                new_text_muted = st.color_picker("Texto secundario", st.session_state.live_custom["text_muted"])
                new_accent = st.color_picker("Color de acento", st.session_state.live_custom["accent"])
                new_border_hover = st.color_picker("Bordes al pasar mouse", st.session_state.live_custom["border_hover"])

            changed = False
            for k, val in [
                ("bg_base", new_bg_base),
                ("bg_card", new_bg_card),
                ("bg_sidebar", new_bg_sidebar),
                ("border", new_border),
                ("border_hover", new_border_hover),
                ("accent", new_accent),
                ("text", new_text),
                ("text_muted", new_text_muted)
            ]:
                if st.session_state.live_custom[k] != val:
                    st.session_state.live_custom[k] = val
                    changed = True

            if changed:
                st.session_state.live_custom["accent_light"] = f"{new_accent}26"
                st.rerun()

            st.markdown("<div style='font-size: 0.75rem; font-weight: 600; color: var(--text-muted); margin-top: 10px;'>GUARDAR COMBINACIÓN</div>", unsafe_allow_html=True)
            theme_name_input = st.text_input("Nombre del nuevo tema:", placeholder="Ej. Mi Azul Índigo", label_visibility="collapsed")
            if st.button("💾 Guardar este tema", use_container_width=True):
                t_name = theme_name_input.strip()
                if t_name:
                    st.session_state.saved_custom_themes[t_name] = dict(st.session_state.live_custom)
                    save_custom_themes(st.session_state.saved_custom_themes)
                    st.session_state.app_theme = t_name
                    st.success(f"Tema '{t_name}' guardado correctamente.")
                    st.rerun()
                else:
                    st.warning("Introduce un nombre para guardar el tema.")

    if st.session_state.app_theme in st.session_state.saved_custom_themes:
        st.markdown(f"<div style='font-size: 0.75rem; color: var(--text-muted); margin-top: 6px;'>Gestionar tema '{st.session_state.app_theme}':</div>", unsafe_allow_html=True)
        if st.button(f"🗑️ Eliminar tema '{st.session_state.app_theme}'", use_container_width=True):
            deleted_name = st.session_state.app_theme
            del st.session_state.saved_custom_themes[deleted_name]
            save_custom_themes(st.session_state.saved_custom_themes)
            st.session_state.app_theme = "Minimal Dark (Grafito)"
            st.success(f"Tema '{deleted_name}' eliminado.")
            st.rerun()


# --- BARRA SUPERIOR: VISTAS INDEPENDIENTES ---
col_h_brand, col_btn_chat, col_btn_pdf, col_btn_sum = st.columns([0.46, 0.18, 0.18, 0.18], gap="small")

with col_h_brand:
    active_label = st.session_state.file_name if st.session_state.file_name else "Todos los documentos"
    st.markdown(f"""
        <div style="padding-top: 4px; display: flex; align-items: baseline; gap: 8px;">
            <span style="font-weight: 700; font-size: 1.05rem; letter-spacing: -0.02em; color: var(--text);">Document Studio</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);">/ {active_label[:34]}</span>
        </div>
    """, unsafe_allow_html=True)

with col_btn_chat:
    chat_status = "Activo" if st.session_state.show_chat else "Oculto"
    if st.button(f"Chat ({chat_status})", key="toggle_chat", type="primary" if st.session_state.show_chat else "secondary", use_container_width=True):
        st.session_state.show_chat = not st.session_state.show_chat
        st.rerun()

with col_btn_pdf:
    pdf_status = "Activo" if st.session_state.show_pdf else "Oculto"
    if st.button(f"Documento ({pdf_status})", key="toggle_pdf", type="primary" if st.session_state.show_pdf else "secondary", use_container_width=True):
        st.session_state.show_pdf = not st.session_state.show_pdf
        st.rerun()

with col_btn_sum:
    sum_status = "Activo" if st.session_state.show_summary else "Oculto"
    if st.button(f"Resumen ({sum_status})", key="toggle_sum", type="primary" if st.session_state.show_summary else "secondary", use_container_width=True):
        st.session_state.show_summary = not st.session_state.show_summary
        st.rerun()


# --- COMPONENTES PRINCIPALES ---

def render_chat(is_full=False):
    """Panel de conversación con citas directas y menú inferior orgánico estilo ChatGPT."""
    feed_h = 720 if is_full else 660
    chat_box = st.container(height=feed_h)

    with chat_box:
        for idx_m, m in enumerate(st.session_state.messages):
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

                # Botones de salto directo a la fuente citada
                if m["role"] == "assistant":
                    cites = re.findall(r'\[(?:Pág\.|Página|Imagen en Pág\.)\s*(\d+)\]', m["content"], re.IGNORECASE)
                    if cites:
                        seen = set()
                        pills = [int(p) for p in cites if p not in seen and not seen.add(p)]
                        c_p = st.columns(min(len(pills) + 1, 6))
                        c_p[0].caption("Ir a la fuente:")
                        for p_i, p_num in enumerate(pills[:5]):
                            with c_p[(p_i + 1) % len(c_p)]:
                                if st.button(f"📍 Pág. {p_num}", key=f"btn_p_{idx_m}_{p_num}"):
                                    st.session_state.active_page = int(p_num)
                                    st.session_state.highlight_words = [w for w in re.findall(r'\b[A-Za-z0-9_áéíóúÁÉÍÓÚñÑ]{3,}\b', m["content"]) if len(w) >= 3][:30]
                                    st.session_state.show_pdf = True
                                    st.rerun()

    # Input del chat
    prompt = st.chat_input("Escribe tu consulta sobre el contenido o imágenes...")

    # --- BARRA INFERIOR DE CONFIGURACIÓN ORGÁNICA (ESTILO CHATGPT) ---
    with st.expander("⚙️ Parámetros de Modelo, Chunks y Vectores (Local / Nube)", expanded=False):
        c_mod, c_chunk, c_topk = st.columns([0.40, 0.35, 0.25], gap="small")

        with c_mod:
            provider_list = ["Ollama (Local)", "Llama.cpp Server (Local)", "Google Gemini (Nube)", "OpenAI / Groq API (Nube)"]
            selected_provider = st.selectbox(
                "Motor de Inferencia:",
                options=provider_list,
                index=provider_list.index(st.session_state.ai_provider),
                help="Elige si deseas procesar con tu servidor local (Ollama/Llama.cpp) o mediante API en la nube (Gemini / Groq / OpenAI)."
            )
            if selected_provider != st.session_state.ai_provider:
                st.session_state.ai_provider = selected_provider
                st.rerun()

            # Opciones según el proveedor
            if selected_provider == "Ollama (Local)":
                st.session_state.local_model = st.text_input("Modelo Ollama:", value=st.session_state.local_model, help="Ej: qwen2.5:7b, llama3:8b, mistral, llava")
            elif selected_provider == "Llama.cpp Server (Local)":
                st.session_state.llamacpp_url = st.text_input("URL Llama.cpp Server:", value=st.session_state.llamacpp_url, help="Servidor ejecutado con llama-server (puerto 8080)")
            elif "Gemini" in selected_provider:
                st.session_state.cloud_api_key = st.text_input("Gemini API Key:", value=st.session_state.cloud_api_key, type="password", help="Tu API Key gratuita de Google AI Studio (aistudio.google.com)")
                st.session_state.cloud_model_name = st.selectbox("Modelo Gemini:", ["gemini-1.5-flash", "gemini-1.5-pro"])
            elif "OpenAI" in selected_provider:
                st.session_state.cloud_api_key = st.text_input("API Key (OpenAI o Groq):", value=st.session_state.cloud_api_key, type="password")

        with c_chunk:
            st.session_state.chunk_size = st.slider("Tamaño de Chunk (caracteres):", min_value=250, max_value=1200, value=st.session_state.chunk_size, step=50, help="Longitud de texto para cada fragmento vectorial al indexar.")
            st.session_state.chunk_overlap = st.slider("Solapamiento (Overlap):", min_value=20, max_value=200, value=st.session_state.chunk_overlap, step=10, help="Caracteres compartidos entre chunks consecutivos para mantener contexto.")

        with c_topk:
            st.session_state.top_k_chunks = st.slider("Top K Chunks recuperados:", min_value=2, max_value=12, value=st.session_state.top_k_chunks, step=1, help="Número de fragmentos más relevantes enviados al modelo.")

    # Procesar consulta
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Vía 1: Consultas ultrarrápidas de cortesía y saludo (sin RAG ni carga en GPU)
        clean_p = prompt.strip().lower()
        if clean_p in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "que tal", "hola!", "holaa", "saludos"]:
            fast_ans = "¡Hola! Estoy listo para responder consultas técnicas sobre tu documento. Puedes preguntarme sobre el texto, pasos o sobre cualquier imagen que contenga."
            st.session_state.messages.append({"role": "assistant", "content": fast_ans})
            st.rerun()
        elif clean_p in ["gracias", "muchas gracias", "ok gracias", "vale gracias", "perfecto gracias"]:
            fast_ans = "¡Con gusto! Quedo a tu disposición si necesitas verificar cualquier otro dato o página."
            st.session_state.messages.append({"role": "assistant", "content": fast_ans})
            st.rerun()

        # Vía 2: Consulta Documental RAG
        context_rag, t_file, t_page, t_content = retrieve_rag_context(prompt, st.session_state.active_doc)

        st.session_state.active_page = t_page
        if t_file and t_file != st.session_state.file_name:
            st.session_state.file_name = t_file
            b, txt = load_pdf_data(t_file)
            st.session_state.file_bytes = b
            st.session_state.full_doc_text = txt

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
{context_rag}
"""
        with st.spinner("Consultando información citada..."):
            ans = call_llm(prompt, sys_prompt, st.session_state.messages[:-1])

        # Sanitizador de texto: Limpiar cualquier comando crudo de LaTeX a texto plano legible (a/b)
        ans = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', ans)
        ans = re.sub(r'\(?\\frac\{([^}]+)\}\{([^}]+)\}\)?', r'\1/\2', ans)
        ans = ans.replace(r'\(', '').replace(r'\)', '').replace(r'\[', '[').replace(r'\]', ']')

        found_cites = re.findall(r'\[(?:Pág\.|Página|Imagen en Pág\.)\s*(\d+)\]', ans, re.IGNORECASE)
        if found_cites:
            st.session_state.active_page = int(found_cites[0])
        else:
            st.session_state.active_page = t_page

        st.session_state.highlight_words = extract_highlight_words(prompt, ans, t_content)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()


def render_pdf_viewer(is_full=False):
    """Visor continuo de documento."""
    if st.session_state.file_bytes:
        viewer_height = 800 if is_full else 740
        pdf_html = render_continuous_pdf_viewer_html(
            file_bytes=st.session_state.file_bytes,
            target_page=st.session_state.active_page,
            highlight_words=st.session_state.highlight_words,
            theme=current_theme
        )
        components.html(pdf_html, height=viewer_height, scrolling=False)
    else:
        st.info("Selecciona o sube un documento PDF en el panel lateral.")


def render_summary(is_full=False):
    """Panel de síntesis documental."""
    st.markdown(f"""
        <div style="font-weight: 600; font-size: 0.88rem; color: var(--text-muted); margin-bottom: 6px;">
            Síntesis • {st.session_state.file_name or 'Documento'}
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.summary:
        st.markdown(f"""
            <div class="summary-box">
                {st.session_state.summary}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Aún no se ha generado la síntesis de este documento.")
        if st.button("Generar síntesis del documento", use_container_width=True):
            with st.spinner("Generando síntesis..."):
                try:
                    p = f"Elabora una síntesis estructurada por puntos clave del documento '{st.session_state.file_name}':\n\n{st.session_state.full_doc_text[:12000]}"
                    r = call_llm(p, "Eres un analista documental experto.", [])
                    st.session_state.summary = r
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# --- DISTRIBUCIÓN DINÁMICA DE PANTALLA ---
active_views = []
if st.session_state.show_chat:
    active_views.append("chat")
if st.session_state.show_pdf:
    active_views.append("pdf")
if st.session_state.show_summary:
    active_views.append("summary")

if not active_views:
    st.session_state.show_chat = True
    active_views = ["chat"]

if len(active_views) == 1:
    v = active_views[0]
    if v == "chat":
        render_chat(is_full=True)
    elif v == "pdf":
        render_pdf_viewer(is_full=True)
    elif v == "summary":
        render_summary(is_full=True)

elif len(active_views) == 2:
    col_1, col_2 = st.columns([0.50, 0.50], gap="medium")
    for idx, v in enumerate(active_views):
        with (col_1 if idx == 0 else col_2):
            if v == "chat":
                render_chat()
            elif v == "pdf":
                render_pdf_viewer()
            elif v == "summary":
                render_summary()

elif len(active_views) == 3:
    col_1, col_2, col_3 = st.columns([0.34, 0.36, 0.30], gap="medium")
    for idx, v in enumerate(active_views):
        with (col_1 if idx == 0 else (col_2 if idx == 1 else col_3)):
            if v == "chat":
                render_chat()
            elif v == "pdf":
                render_pdf_viewer()
            elif v == "summary":
                render_summary()