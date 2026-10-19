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
        "bg_base": "#f3f6f5",
        "bg_card": "#ffffff",
        "bg_sidebar": "#e9efed",
        "border": "#d9e2df",
        "border_hover": "#b9cac4",
        "accent": "#287a70",
        "accent_light": "rgba(40, 122, 112, 0.12)",
        "text": "#192b29",
        "text_muted": "#536560"
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
    st.session_state.app_theme = "Minimal Light (Papel & Lino)"
if "show_chat" not in st.session_state:
    st.session_state.show_chat = True
if "show_pdf" not in st.session_state:
    st.session_state.show_pdf = True
if "show_summary" not in st.session_state:
    st.session_state.show_summary = False
if "sidebar_module" not in st.session_state:
    st.session_state.sidebar_module = "library"
if "sidebar_collapsed" not in st.session_state:
    st.session_state.sidebar_collapsed = False
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
    current_theme = ALL_THEMES.get(st.session_state.app_theme, DEFAULT_THEMES["Minimal Light (Papel & Lino)"])

# Contrast-aware ink for primary controls across built-in and custom themes.
def relative_luminance(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(color_a, color_b):
    luminance_a = relative_luminance(color_a)
    luminance_b = relative_luminance(color_b)
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


accent_ink = max(("#ffffff", "#10201e"), key=lambda color: contrast_ratio(color, current_theme["accent"]))
color_scheme = "light" if relative_luminance(current_theme["bg_base"]) > 0.45 else "dark"

# Estilos de la aplicación. Los selectores apuntan a los test IDs reales de Streamlit 1.66.
st.markdown(f"""
<style>
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
        --accent-ink: {accent_ink};
        --sidebar-width: {"4.75rem" if st.session_state.sidebar_collapsed else "22rem"};
        --background-color: {current_theme['bg_base']};
        --secondary-background-color: {current_theme['bg_card']};
        --text-color: {current_theme['text']};
        --primary-color: {current_theme['accent']};
        color-scheme: {color_scheme};
    }}

    html, body, [data-testid="stAppViewContainer"] {{
        min-height: 100dvh !important;
        height: 100dvh !important;
        margin: 0 !important;
        padding: 0 !important;
        background: var(--bg-base) !important;
        color: var(--text) !important;
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI Variable", sans-serif !important;
    }}

    [data-testid="stAppViewContainer"] {{
        overflow: hidden !important;
    }}

    [data-testid="stMain"] {{
        height: 100dvh !important;
        overflow-x: hidden !important;
        overflow-y: auto !important;
        background: var(--bg-base) !important;
    }}

    [data-testid="stMainBlockContainer"] {{
        box-sizing: border-box !important;
        width: 100% !important;
        max-width: none !important;
        min-height: 100dvh !important;
        padding: 0.75rem 4.75rem 1rem clamp(0.75rem, 1.8vw, 1.75rem) !important;
    }}

    header[data-testid="stHeader"] {{
        display: none !important;
        height: 0 !important;
    }}

    [data-testid="stSidebarCollapseButton"],
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarResizeHandle"] {{
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }}

    [data-testid="stSidebar"] {{
        box-sizing: border-box !important;
        width: var(--sidebar-width) !important;
        min-width: var(--sidebar-width) !important;
        max-width: var(--sidebar-width) !important;
        flex: 0 0 var(--sidebar-width) !important;
        height: 100dvh !important;
        overflow: hidden !important;
        background: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border) !important;
        transform: none !important;
        transition: width 180ms ease, min-width 180ms ease, max-width 180ms ease, flex-basis 180ms ease !important;
    }}

    [data-testid="stSidebarContent"] {{
        width: 100% !important;
        box-sizing: border-box !important;
        padding: 0.7rem 0.55rem 1rem !important;
        color: var(--text) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
        color: var(--text) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
        color: var(--text-muted) !important;
    }}

    [data-testid="stSidebar"] hr {{
        margin: 0.8rem 0 !important;
        border-color: var(--border) !important;
    }}

    .sidebar-brand {{
        display: flex;
        align-items: center;
        gap: 0.7rem;
        min-height: 46px;
        padding: 0 0 0.8rem;
        margin-bottom: 0.8rem;
        border-bottom: 1px solid var(--border);
    }}

    .brand-mark {{
        display: grid;
        place-items: center;
        width: 44px;
        height: 44px;
        flex: 0 0 44px;
        border-radius: 12px;
        background: var(--accent);
        color: var(--accent-ink);
        font-size: 1rem;
        font-weight: 800;
    }}

    .brand-name {{
        color: var(--text);
        font-size: 0.95rem;
        font-weight: 720;
        letter-spacing: -0.025em;
        line-height: 1.2;
    }}

    .brand-caption, .sidebar-section-label {{
        color: var(--text-muted);
        font-size: 0.63rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        line-height: 1.4;
    }}

    .brand-caption {{
        margin-top: 0.2rem;
        font-size: 0.56rem;
        letter-spacing: 0.12em;
    }}

    .sidebar-rail-mark {{
        display: grid;
        place-items: center;
        width: 44px;
        height: 44px;
        margin: 0 auto 0.55rem;
        border-radius: 12px;
        background: var(--accent);
        color: var(--accent-ink);
        font-size: 0.95rem;
        font-weight: 800;
    }}

    .sidebar-panel-brand {{
        min-height: 40px;
        padding: 0.65rem 0 0.55rem;
        color: var(--text);
        font-size: 0.91rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }}

    .sidebar-section-label {{
        margin: 0.15rem 0 0.55rem;
        font-size: 0.62rem;
    }}

    .workspace-heading {{
        display: flex;
        min-height: 44px;
        flex-direction: column;
        justify-content: center;
        gap: 0.14rem;
        min-width: 0;
    }}

    .workspace-eyebrow {{
        color: var(--text-muted);
        font-size: 0.58rem;
        font-weight: 700;
        letter-spacing: 0.12em;
    }}

    .workspace-title {{
        overflow: hidden;
        color: var(--text);
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        line-height: 1.2;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}

    /* Sticky header begins at the top of the actual Streamlit scroll root. */
    .st-key-workspace_header {{
        position: sticky !important;
        top: 0 !important;
        z-index: 40 !important;
        display: block !important;
        margin: -0.75rem 0 0.65rem !important;
        padding: 0.45rem 0.55rem 0.5rem !important;
        border-bottom: 1px solid var(--border) !important;
        background: var(--bg-base) !important;
    }}

    .st-key-workspace_header [data-testid="stHorizontalBlock"] {{
        align-items: center !important;
    }}

    .st-key-view_switcher {{
        position: fixed !important;
        top: 50% !important;
        right: 0.75rem !important;
        z-index: 55 !important;
        display: flex !important;
        width: 60px !important;
        margin: 0 !important;
        padding: 0.4rem !important;
        transform: translateY(-50%) !important;
        flex-direction: column !important;
        align-items: center !important;
        gap: 0.45rem !important;
        border: 1px solid var(--border) !important;
        border-radius: 15px !important;
        background: var(--bg-sidebar) !important;
        box-shadow: 0 8px 22px color-mix(in srgb, var(--text) 8%, transparent) !important;
    }}

    /* Streamlit 1.66 renders button widgets under data-testid, not .stButton. */
    [data-testid="stButton"] button {{
        box-sizing: border-box !important;
        min-height: 42px !important;
        padding: 0.5rem 0.75rem !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        box-shadow: none !important;
        transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease, opacity 150ms ease !important;
    }}

    [data-testid="stButton"] button:hover {{
        border-color: var(--accent) !important;
        background: var(--accent-light) !important;
    }}

    [data-testid="stButton"] button:focus-visible {{
        outline: 2px solid var(--accent) !important;
        outline-offset: 2px !important;
    }}

    [data-testid="stBaseButton-primary"] {{
        border-color: var(--accent) !important;
        background: var(--accent) !important;
        color: var(--accent-ink) !important;
    }}

    [data-testid="stButton"] [data-testid="stBaseButton-primary"] {{
        border-color: var(--accent) !important;
        background: var(--accent) !important;
        color: var(--accent-ink) !important;
    }}

    [data-testid="stBaseButton-secondary"] {{
        border-color: var(--border) !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
    }}

    [data-testid="stBaseButton-secondary"]:hover {{
        border-color: var(--accent) !important;
        background: var(--accent-light) !important;
        color: var(--text) !important;
    }}

    .st-key-sidebar_rail {{
        display: flex !important;
        width: 48px !important;
        flex-direction: column !important;
        align-items: center !important;
        gap: 0.45rem !important;
    }}

    .st-key-sidebar_nav [data-testid="stButton"],
    .st-key-sidebar_toggle [data-testid="stButton"] {{
        width: 46px !important;
        min-width: 46px !important;
        margin: 0.14rem 0 !important;
    }}

    .st-key-sidebar_nav [data-testid="stButton"] button,
    .st-key-sidebar_toggle [data-testid="stButton"] button {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 44px !important;
        min-width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 !important;
        border-radius: 12px !important;
    }}

    .st-key-sidebar_nav [data-testid="stMarkdownContainer"],
    .st-key-sidebar_toggle [data-testid="stMarkdownContainer"] {{
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        clip-path: inset(50%) !important;
        white-space: nowrap !important;
    }}

    .st-key-sidebar_nav [data-testid="stMarkdownContainer"] p,
    .st-key-sidebar_toggle [data-testid="stMarkdownContainer"] p {{
        margin: 0 !important;
        line-height: 1.05 !important;
    }}

    .st-key-sidebar_rail > [data-testid="stElementContainer"] {{
        width: 44px !important;
        margin: 0 auto !important;
    }}

    .st-key-sidebar_rail hr {{
        width: 100%;
        margin: 0.35rem 0 !important;
    }}

    .st-key-sidebar_toggle [data-testid="stButton"] button {{
        background: transparent !important;
        color: var(--text-muted) !important;
    }}

    .st-key-sidebar_toggle {{
        box-sizing: border-box !important;
        width: 46px !important;
        height: 44px !important;
        min-height: 44px !important;
        flex: 0 0 44px !important;
        margin: 0.1rem 0 !important;
    }}

    .st-key-toggle_sidebar_width {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        position: fixed !important;
        top: 8.875rem !important;
        left: calc(var(--sidebar-width) - 24px) !important;
        z-index: 90 !important;
        width: 48px !important;
        height: 48px !important;
        transition: left 180ms ease !important;
    }}

    .st-key-toggle_sidebar_width [data-testid="stButton"] {{
        width: 44px !important;
        min-width: 44px !important;
        margin: 0 !important;
    }}

    .st-key-view_switcher [data-testid="stButton"] button {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 44px !important;
        min-width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 !important;
        justify-content: center !important;
        border-radius: 11px !important;
        opacity: 0.56 !important;
        background: transparent !important;
        color: var(--text-muted) !important;
    }}

    .st-key-view_switcher [data-testid="stButton"] button:hover {{
        opacity: 1 !important;
        background: var(--bg-card) !important;
    }}

    .st-key-view_switcher [data-testid="stBaseButton-primary"] {{
        opacity: 1 !important;
        border-color: var(--accent) !important;
        background: var(--accent-light) !important;
        color: var(--accent) !important;
    }}

    .st-key-view_switcher [data-testid="stButton"] [data-testid="stBaseButton-primary"] {{
        opacity: 1 !important;
        border-color: var(--accent) !important;
        background: var(--accent-light) !important;
        color: var(--accent) !important;
    }}

    /* Keep accessible button names while reserving their visible space for icons. */
    .st-key-view_switcher [data-testid="stMarkdownContainer"] {{
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        clip-path: inset(50%) !important;
        white-space: nowrap !important;
    }}

    :is(
        .st-key-sidebar_nav_library,
        .st-key-sidebar_nav_upload,
        .st-key-sidebar_nav_appearance,
        .st-key-sidebar_nav_session,
        .st-key-toggle_chat,
        .st-key-toggle_pdf,
        .st-key-toggle_sum
    ) {{
        position: relative !important;
        z-index: 1;
    }}

    :is(
        .st-key-sidebar_nav_library,
        .st-key-sidebar_nav_upload,
        .st-key-sidebar_nav_appearance,
        .st-key-sidebar_nav_session,
        .st-key-toggle_sidebar_width,
        .st-key-toggle_chat,
        .st-key-toggle_pdf,
        .st-key-toggle_sum
    )::after {{
        position: absolute;
        z-index: 1000;
        top: 50%;
        left: calc(100% + 0.55rem);
        display: block;
        width: max-content;
        max-width: min(12rem, calc(100vw - 2rem));
        padding: 0.42rem 0.65rem;
        transform: translateY(-50%);
        border: 1px solid var(--border);
        border-radius: 9px;
        background: var(--bg-card);
        color: var(--text);
        font-size: 0.74rem;
        font-weight: 600;
        line-height: 1.25;
        white-space: nowrap;
        box-shadow: 0 7px 18px rgba(15, 23, 42, 0.14);
        opacity: 0;
        visibility: hidden;
        pointer-events: none;
        transition: opacity 120ms ease, visibility 0s linear 120ms;
    }}

    .st-key-sidebar_nav_library::after {{ content: "Biblioteca"; }}
    .st-key-sidebar_nav_upload::after {{ content: "Añadir PDF"; }}
    .st-key-sidebar_nav_appearance::after {{ content: "Apariencia"; }}
    .st-key-sidebar_nav_session::after {{ content: "Sesión"; }}
    .st-key-toggle_sidebar_width::after {{ content: "Contraer"; }}
    [data-testid="stSidebar"]:has(#sidebar_compact_marker) .st-key-toggle_sidebar_width::after {{ content: "Expandir"; }}

    :is(
        .st-key-sidebar_nav_library,
        .st-key-sidebar_nav_upload,
        .st-key-sidebar_nav_appearance,
        .st-key-sidebar_nav_session,
        .st-key-toggle_sidebar_width,
        .st-key-toggle_chat,
        .st-key-toggle_pdf,
        .st-key-toggle_sum
    ):hover::after,
    :is(
        .st-key-sidebar_nav_library,
        .st-key-sidebar_nav_upload,
        .st-key-sidebar_nav_appearance,
        .st-key-sidebar_nav_session,
        .st-key-toggle_sidebar_width,
        .st-key-toggle_chat,
        .st-key-toggle_pdf,
        .st-key-toggle_sum
    ):focus-within::after {{
        opacity: 1;
        visibility: visible;
        transition: opacity 120ms ease;
    }}

    :is(.st-key-toggle_chat, .st-key-toggle_pdf, .st-key-toggle_sum)::after {{
        right: calc(100% + 0.55rem);
        left: auto;
    }}

    .st-key-toggle_chat::after {{ content: "Chat"; }}
    .st-key-toggle_pdf::after {{ content: "PDF"; }}
    .st-key-toggle_sum::after {{ content: "Resumen"; }}

    .st-key-sidebar_nav_library:hover,
    .st-key-sidebar_nav_upload:hover,
    .st-key-sidebar_nav_appearance:hover,
    .st-key-sidebar_nav_session:hover,
    .st-key-toggle_sidebar_width:hover,
    .st-key-toggle_chat:hover,
    .st-key-toggle_pdf:hover,
    .st-key-toggle_sum:hover,
    .st-key-sidebar_nav_library:focus-within,
    .st-key-sidebar_nav_upload:focus-within,
    .st-key-sidebar_nav_appearance:focus-within,
    .st-key-sidebar_nav_session:focus-within,
    .st-key-toggle_sidebar_width:focus-within,
    .st-key-toggle_chat:focus-within,
    .st-key-toggle_pdf:focus-within,
    .st-key-toggle_sum:focus-within {{
        z-index: 1001 !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) {{
        overflow: visible !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) [data-testid="stSidebarContent"] {{
        overflow: visible !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) {{
        width: 4.75rem !important;
        min-width: 4.75rem !important;
        max-width: 4.75rem !important;
        flex-basis: 4.75rem !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) [data-testid="stSidebarContent"] {{
        padding-right: 0.4rem !important;
        padding-left: 0.4rem !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) .sidebar-brand {{
        justify-content: center !important;
        padding-bottom: 0.7rem !important;
        margin-bottom: 0.65rem !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) .sidebar-brand > div:not(.brand-mark) {{
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        clip-path: inset(50%) !important;
        white-space: nowrap !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) .st-key-sidebar_nav [data-testid="stButton"],
    [data-testid="stSidebar"]:has(#sidebar_compact_marker) .st-key-sidebar_toggle [data-testid="stButton"] {{
        width: 48px !important;
        min-width: 48px !important;
        margin: 0.12rem auto !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) .st-key-sidebar_nav button,
    [data-testid="stSidebar"]:has(#sidebar_compact_marker) .st-key-sidebar_toggle button {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 44px !important;
        min-width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) .st-key-sidebar_toggle button {{
        background: transparent !important;
        color: var(--text-muted) !important;
    }}

    [data-testid="stSidebar"]:has(#sidebar_compact_marker) .st-key-toggle_sidebar_width [data-testid="stButton"] {{
        width: 44px !important;
        min-width: 44px !important;
        margin: 0 !important;
    }}

    .panel-heading {{
        padding: 0.15rem 0 0.65rem;
        margin-bottom: 0.55rem;
        border-bottom: 1px solid var(--border);
    }}

    .panel-kicker {{
        color: var(--text-muted);
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.1em;
    }}

    .panel-title {{
        margin-top: 0.18rem;
        color: var(--text);
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }}

    .panel-description {{
        margin-top: 0.15rem;
        color: var(--text-muted);
        font-size: 0.78rem;
        line-height: 1.45;
    }}

    [data-testid="stChatMessage"] {{
        margin-bottom: 0.55rem !important;
        padding: 0.8rem 0.95rem !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
        box-shadow: none !important;
    }}

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"] li {{
        color: var(--text) !important;
        line-height: 1.62 !important;
    }}

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
        background: var(--accent-light) !important;
    }}

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {{
        border-color: var(--border) !important;
    }}

    .st-key-chat_feed [data-testid="stVerticalBlockBorderWrapper"] {{
        overflow-anchor: none !important;
        overscroll-behavior: contain !important;
        scrollbar-color: var(--border-hover) transparent;
    }}

    .st-key-chat_panel {{
        box-sizing: border-box !important;
        display: flex !important;
        flex-direction: column !important;
        flex: 0 0 auto !important;
        height: calc(100dvh - 7rem) !important;
        min-height: 28rem !important;
        overflow: hidden !important;
    }}

    .st-key-chat_panel > [data-testid="stElementContainer"],
    .st-key-chat_panel > .st-key-chat_feed,
    .st-key-chat_panel > .st-key-chat_composer {{
        flex-shrink: 0;
    }}

    .st-key-chat_panel > [data-testid="stLayoutWrapper"]:has(.st-key-chat_feed) {{
        flex: 1 1 0 !important;
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
    }}

    .st-key-chat_panel .st-key-chat_feed {{
        box-sizing: border-box !important;
        height: 100% !important;
        min-height: 0 !important;
        overflow: auto !important;
    }}

    .st-key-chat_feed > [data-testid="stLayoutWrapper"] {{
        flex: 1 1 0 !important;
        height: auto !important;
        min-height: 0 !important;
    }}

    .st-key-chat_feed > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlockBorderWrapper"] {{
        height: 100% !important;
        min-height: 0 !important;
    }}

    .st-key-chat_composer {{
        position: sticky !important;
        bottom: 0 !important;
        z-index: 20 !important;
        flex: 0 0 auto !important;
        margin-top: auto !important;
        padding: 0.45rem 0 0.25rem !important;
        background: var(--bg-base) !important;
    }}

    [data-testid="stChatInput"] {{
        position: relative !important;
        width: 100% !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
        box-shadow: 0 4px 14px color-mix(in srgb, var(--text) 7%, transparent) !important;
    }}

    [data-testid="stChatInput"] > div {{
        border-color: var(--border) !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
    }}

    [data-testid="stChatInput"] textarea {{
        color: var(--text) !important;
    }}

    [data-testid="stChatInput"] textarea::placeholder {{
        color: var(--text-muted) !important;
        opacity: 1 !important;
    }}

    [data-testid="stChatInputSubmitButton"] {{
        background: var(--accent-light) !important;
        color: var(--accent) !important;
    }}

    [data-testid="stChatInputSubmitButton"]:disabled {{
        background: var(--border) !important;
        color: var(--text-muted) !important;
        opacity: 0.8 !important;
    }}

    [data-testid="stChatInput"]:focus-within {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px var(--accent-light) !important;
    }}

    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] p,
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label p,
    [data-testid="stFileUploader"] label,
    [data-testid="stSelectbox"] label,
    [data-testid="stTextInput"] label,
    [data-testid="stSlider"] label {{
        color: var(--text) !important;
    }}

    [data-testid="stBaseButton-primary"] [data-testid="stMarkdownContainer"],
    [data-testid="stBaseButton-primary"] [data-testid="stMarkdownContainer"] p {{
        color: var(--accent-ink) !important;
    }}

    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    [data-testid="stHelp"] {{
        color: var(--text-muted) !important;
    }}

    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stTextInput"] [data-baseweb="input"] > div,
    [data-testid="stTextArea"] [data-baseweb="textarea"] > div {{
        border-color: var(--border) !important;
        border-radius: 9px !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
    }}

    [data-testid="stSelectbox"] [data-baseweb="select"] *,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {{
        color: var(--text) !important;
    }}

    [data-baseweb="select"] > div {{
        border: 1px solid var(--border) !important;
        border-radius: 9px !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
    }}

    [data-baseweb="select"] [role="combobox"],
    [data-baseweb="select"] [role="combobox"] * {{
        background-color: transparent !important;
        color: var(--text) !important;
    }}

    [data-testid="stSelectbox"] [role="group"] {{
        min-height: 42px !important;
        border: 1px solid var(--border) !important;
        border-radius: 9px !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
    }}

    [data-testid="stSelectbox"] input[role="combobox"] {{
        background: transparent !important;
        color: var(--text) !important;
        caret-color: var(--accent) !important;
    }}

    [data-testid="stSelectbox"] button[aria-haspopup="listbox"] {{
        background: transparent !important;
        color: var(--text) !important;
    }}

    [role="listbox"],
    [role="option"] {{
        background: var(--bg-card) !important;
        color: var(--text) !important;
    }}

    [role="option"][aria-selected="true"],
    [role="option"]:hover {{
        background: var(--accent-light) !important;
        color: var(--text) !important;
    }}

    [data-baseweb="popover"] [role="listbox"],
    [data-baseweb="popover"] [role="option"] {{
        background: var(--bg-card) !important;
        color: var(--text) !important;
    }}

    [data-baseweb="popover"] [role="option"]:hover,
    [data-baseweb="popover"] [aria-selected="true"] {{
        background: var(--accent-light) !important;
    }}

    [data-testid="stCheckbox"] input {{
        accent-color: var(--accent) !important;
    }}

    [data-testid="stFileUploader"] {{
        color: var(--text) !important;
    }}

    [data-testid="stFileUploader"] section {{
        border: 1px dashed var(--border-hover) !important;
        border-radius: 12px !important;
        background: var(--bg-card) !important;
    }}

    [data-testid="stFileUploader"] button {{
        border: 1px solid var(--border) !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
    }}

    [data-testid="stExpander"] {{
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        background: var(--bg-card) !important;
    }}

    [data-testid="stToast"] {{
        box-sizing: border-box !important;
        max-width: min(270px, calc(100vw - 1.5rem)) !important;
        padding: 0.35rem 0.55rem !important;
        border: 1px solid var(--border) !important;
        border-radius: 11px !important;
        background: var(--bg-card) !important;
        color: var(--text) !important;
        font-size: 0.74rem !important;
        box-shadow: 0 8px 22px color-mix(in srgb, var(--text) 12%, transparent) !important;
    }}

    [data-testid="stToast"] [data-testid="stMarkdownContainer"],
    [data-testid="stToast"] [data-testid="stMarkdownContainer"] p {{
        color: var(--text) !important;
    }}

    .summary-box {{
        box-sizing: border-box;
        min-height: min(55dvh, 42rem);
        padding: 1.2rem;
        overflow: auto;
        border: 1px solid var(--border);
        border-radius: 12px;
        background: var(--bg-card);
        color: var(--text);
        line-height: 1.7;
    }}

    .empty-document {{
        display: grid;
        min-height: 340px;
        align-content: center;
        justify-items: center;
        padding: 1.5rem;
        border: 1px dashed var(--border-hover);
        border-radius: 14px;
        background: var(--bg-card);
        text-align: center;
    }}

    .empty-document-mark {{
        display: grid;
        place-items: center;
        width: 52px;
        height: 60px;
        margin-bottom: 0.9rem;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-base);
        color: var(--accent);
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.08em;
    }}

    .empty-document-title {{
        color: var(--text);
        font-size: 1rem;
        font-weight: 700;
    }}

    .empty-document-copy {{
        max-width: 34ch;
        margin-top: 0.4rem;
        color: var(--text-muted);
        font-size: 0.82rem;
        line-height: 1.55;
    }}

    a.doc-cite-link {{
        color: var(--accent) !important;
        text-decoration: underline;
        text-underline-offset: 0.15em;
        background: var(--accent-light);
    }}

    :is(button, input, textarea, [role="combobox"], [tabindex]):focus-visible {{
        outline: 2px solid var(--accent) !important;
        outline-offset: 2px !important;
    }}

    ::selection {{
        background: var(--accent-light);
        color: var(--text);
    }}

    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: transparent;
    }}

    ::-webkit-scrollbar-thumb {{
        border: 2px solid transparent;
        border-radius: 8px;
        background: var(--border-hover);
        background-clip: padding-box;
    }}

    @media (min-width: 641px) and (max-width: 900px) {{
        [data-testid="stAppViewContainer"] [data-testid="stMain"] {{
            position: relative !important;
            inset: auto !important;
            width: auto !important;
            min-width: 0 !important;
            flex: 1 1 auto !important;
        }}
    }}

    @media (max-width: 1100px) {{
        .stHorizontalBlock:has(> [data-testid="stColumn"] [data-testid="stChatMessage"]) {{
            flex-wrap: wrap !important;
        }}

        .stHorizontalBlock:has(> [data-testid="stColumn"] [data-testid="stChatMessage"]) > [data-testid="stColumn"] {{
            flex: 1 1 340px !important;
            min-width: min(100%, 340px) !important;
        }}
    }}

    @media (max-width: 900px) {{
        [data-testid="stMainBlockContainer"] {{
            padding-right: 4.75rem !important;
            padding-left: 0.85rem !important;
        }}

        [data-testid="stAppViewContainer"]:has(#sidebar_compact_marker) [data-testid="stMain"] {{
            position: relative !important;
            inset: auto !important;
            width: auto !important;
            min-width: 0 !important;
            flex: 1 1 auto !important;
        }}

        .stHorizontalBlock:has(> [data-testid="stColumn"] [data-testid="stChatMessage"]) {{
            flex-wrap: wrap !important;
        }}

        .stHorizontalBlock:has(> [data-testid="stColumn"] [data-testid="stChatMessage"]) > [data-testid="stColumn"] {{
            flex: 1 1 340px !important;
            min-width: min(100%, 340px) !important;
        }}
    }}

    @media (max-width: 640px) {{
        [data-testid="stSidebar"] {{
            width: min(var(--sidebar-width), 82vw) !important;
            min-width: min(var(--sidebar-width), 82vw) !important;
            flex-basis: min(var(--sidebar-width), 82vw) !important;
        }}

        [data-testid="stSidebar"] .st-key-toggle_sidebar_width {{
            left: calc(min(var(--sidebar-width), 82vw) - 24px) !important;
        }}

        [data-testid="stAppViewContainer"]:has(#sidebar_compact_marker) [data-testid="stMain"] {{
            position: relative !important;
            inset: auto !important;
            width: auto !important;
            min-width: 0 !important;
            flex: 1 1 auto !important;
        }}

        [data-testid="stMainBlockContainer"] {{
            padding-right: 0.85rem !important;
        }}

        .st-key-view_switcher {{
            position: static !important;
            top: auto !important;
            right: auto !important;
            width: 100% !important;
            max-width: 100% !important;
            margin: 0.2rem 0 0.75rem !important;
            padding: 0.25rem !important;
            transform: none !important;
            flex-direction: row !important;
            justify-content: stretch !important;
            gap: 0.25rem !important;
            box-shadow: none !important;
        }}

        .st-key-view_switcher [data-testid="stButton"] {{
            width: auto !important;
            min-width: 0 !important;
            flex: 1 1 0 !important;
        }}

        .st-key-workspace_header {{
            padding-right: 0.2rem !important;
            padding-left: 0.2rem !important;
        }}

        .st-key-view_switcher [data-testid="stButton"] button {{
            width: 100% !important;
            min-width: 0 !important;
            height: 44px !important;
            min-height: 44px !important;
            justify-content: center !important;
            gap: 0.2rem !important;
            padding: 0.3rem 0.25rem !important;
        }}

        .st-key-view_switcher [data-testid="stMarkdownContainer"] {{
            font-size: 0.65rem !important;
        }}

        .st-key-toggle_chat::after,
        .st-key-toggle_pdf::after,
        .st-key-toggle_sum::after {{
            top: calc(100% + 0.45rem);
            right: auto;
            left: 50%;
            transform: translateX(-50%);
        }}

        .st-key-chat_panel {{
            height: calc(100dvh - 6rem) !important;
            min-height: 24rem !important;
        }}

        [data-testid="stChatMessage"] {{
            padding: 0.7rem 0.8rem !important;
        }}

        .empty-document {{
            min-height: 260px;
        }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        [data-testid="stSidebar"],
        .st-key-view_switcher [data-testid="stButton"] button {{
            transition: none !important;
        }}

        :is(
            .st-key-sidebar_nav_library,
            .st-key-sidebar_nav_upload,
            .st-key-sidebar_nav_appearance,
            .st-key-sidebar_nav_session,
            .st-key-toggle_sidebar_width,
            .st-key-toggle_chat,
            .st-key-toggle_pdf,
            .st-key-toggle_sum
        )::after {{
            transition: none !important;
        }}
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
          font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI Variable", sans-serif;
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


# --- NAVEGACIÓN MODULAR DE LA BARRA LATERAL ---
SIDEBAR_MODULES = [
    ("library", "Biblioteca", ":material/folder_open:", "Documentos indexados"),
    ("upload", "Añadir PDF", ":material/upload_file:", "Cargar e indexar un PDF"),
    ("appearance", "Apariencia", ":material/palette:", "Temas y colores"),
    ("session", "Sesión", ":material/tune:", "Conversación y opciones de sesión"),
]

def render_sidebar_rail():
    st.markdown('<div class="sidebar-rail-mark">D</div>', unsafe_allow_html=True)
    with st.container(key="sidebar_toggle"):
        toggle_label = "Mostrar panel" if st.session_state.sidebar_collapsed else "Contraer panel"
        if st.button(
            toggle_label,
            icon=":material/chevron_right:" if st.session_state.sidebar_collapsed else ":material/chevron_left:",
            use_container_width=True,
            key="toggle_sidebar_width",
        ):
            st.session_state.sidebar_collapsed = not st.session_state.sidebar_collapsed
            st.rerun()

    with st.container(key="sidebar_nav"):
        for module_key, module_label, module_icon, module_help in SIDEBAR_MODULES:
            if st.button(
                module_label,
                icon=module_icon,
                type="primary" if st.session_state.sidebar_module == module_key else "secondary",
                use_container_width=True,
                key=f"sidebar_nav_{module_key}",
            ):
                st.session_state.sidebar_module = module_key
                if st.session_state.sidebar_collapsed:
                    st.session_state.sidebar_collapsed = False
                st.toast(f"{module_label} abierto", icon=module_icon)
                st.rerun()


with st.sidebar:
    db_ready = setup_database_cached()
    indexed_docs = get_indexed_documents()
    doc_names = [d["filename"] for d in indexed_docs]

    if doc_names and (not st.session_state.file_bytes or not st.session_state.active_doc):
        first_doc = doc_names[0]
        st.session_state.active_doc = first_doc
        st.session_state.file_name = first_doc
        b, txt = load_pdf_data(first_doc)
        st.session_state.file_bytes = b
        st.session_state.full_doc_text = txt
        st.session_state.active_page = 1

    if not st.session_state.get("ui_mount_notified"):
        st.session_state.ui_mount_notified = True
        if db_ready:
            st.toast("Document Studio listo", icon=":material/description:")
        else:
            st.toast("Modo vista: sin PostgreSQL", icon=":material/info:")

    if st.session_state.sidebar_collapsed:
        st.markdown('<div id="sidebar_compact_marker" aria-hidden="true"></div>', unsafe_allow_html=True)
        with st.container(key="sidebar_rail"):
            render_sidebar_rail()
    else:
        rail_column, module_column = st.columns([0.19, 0.81], gap="small")
        with rail_column:
            with st.container(key="sidebar_rail"):
                render_sidebar_rail()
        with module_column:
            st.markdown('<div class="sidebar-panel-brand">Document Studio</div>', unsafe_allow_html=True)
            st.markdown("<hr style='margin: 8px 0 14px; border: none; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
            if st.session_state.sidebar_module == "library":
                st.markdown('<div class="sidebar-section-label">BIBLIOTECA</div>', unsafe_allow_html=True)
                if doc_names:
                    options = [ALL_DOCS_OPTION] + doc_names
                    curr_idx = options.index(st.session_state.active_doc) if st.session_state.active_doc in options else 1
                    selected_doc = st.selectbox(
                        "Documento:",
                        options=options,
                        index=curr_idx,
                        label_visibility="collapsed",
                        key="library_document_selector",
                    )

                    if selected_doc == ALL_DOCS_OPTION:
                        if st.session_state.active_doc != ALL_DOCS_OPTION:
                            st.session_state.active_doc = ALL_DOCS_OPTION
                            st.toast("Mostrando todos los documentos", icon=":material/library_books:")
                    elif selected_doc != st.session_state.active_doc or not st.session_state.file_bytes:
                        st.session_state.active_doc = selected_doc
                        st.session_state.file_name = selected_doc
                        b, txt = load_pdf_data(selected_doc)
                        st.session_state.file_bytes = b
                        st.session_state.full_doc_text = txt
                        st.session_state.active_page = 1
                        st.toast("Documento seleccionado", icon=":material/article:")

                    if selected_doc != ALL_DOCS_OPTION:
                        if st.button("Eliminar documento", icon=":material/delete:", use_container_width=True, key="delete_document"):
                            deleted = delete_document_from_db(selected_doc)
                            st.session_state.active_doc = ALL_DOCS_OPTION
                            st.session_state.file_name = ""
                            st.session_state.file_bytes = None
                            st.session_state.full_doc_text = ""
                            if deleted:
                                st.toast("Documento eliminado", icon=":material/delete:")
                            else:
                                st.toast("No se pudo eliminar el documento", icon=":material/error:")
                            st.rerun()
                else:
                    st.caption("No hay documentos indexados. Carga un PDF para empezar.")

            elif st.session_state.sidebar_module == "upload":
                st.markdown('<div class="sidebar-section-label">AÑADIR DOCUMENTO</div>', unsafe_allow_html=True)
                st.caption("PDF de hasta 30 páginas")
                uploaded_file = st.file_uploader(
                    "Selecciona un PDF",
                    type=["pdf"],
                    label_visibility="collapsed",
                    key="document_pdf_upload",
                )
                analyze_imgs_opt = st.checkbox(
                    "Analizar imágenes con IA de visión",
                    value=True,
                    key="analyze_images_option",
                )
                st.caption("Desactívalo si el PDF solo contiene texto; así se indexa más rápido.")

                if uploaded_file is not None:
                    file_bytes = uploaded_file.read()
                    if st.button("Procesar e indexar", icon=":material/drive_file_move:", use_container_width=True, key="process_pdf"):
                        st.toast("Preparando el documento", icon=":material/hourglass_top:")
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
                            progress_cb=update_prog,
                        )

                        if chunks_res is None:
                            st.error(full_text_res)
                            st.toast("No se pudo procesar el PDF", icon=":material/error:")
                        else:
                            try:
                                prog_bar.progress(0.96, text="Guardando vectores en base de datos...")
                                con = get_db()
                                con.run("DELETE FROM document_chunks WHERE filename = :fname;", fname=uploaded_file.name)
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
                                        emb=json.dumps(emb_vec),
                                    )
                                con.close()

                                st.session_state.summary = ""
                                get_indexed_documents.clear()
                                load_pdf_data.clear()
                                render_continuous_pdf_viewer_html.clear()
                                st.session_state.file_bytes = file_bytes
                                st.session_state.file_name = uploaded_file.name
                                st.session_state.active_doc = uploaded_file.name
                                st.session_state.full_doc_text = full_text_res
                                st.session_state.active_page = 1
                                prog_bar.progress(1.0, text="Completado")
                                st.toast("PDF indexado correctamente", icon=":material/check_circle:")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                                st.toast("Falló el guardado del documento", icon=":material/error:")

            elif st.session_state.sidebar_module == "appearance":
                st.markdown('<div class="sidebar-section-label">APARIENCIA</div>', unsafe_allow_html=True)
                theme_options = list(ALL_THEMES.keys()) + ["🎨 Personalizado"]
                current_selected_idx = theme_options.index(st.session_state.app_theme) if st.session_state.app_theme in theme_options else 0
                theme_pick = st.selectbox(
                    "Tema:",
                    options=theme_options,
                    index=current_selected_idx,
                    label_visibility="collapsed",
                    key="appearance_theme_selector",
                )

                if theme_pick != st.session_state.app_theme:
                    st.session_state.app_theme = theme_pick
                    if theme_pick in ALL_THEMES:
                        st.session_state.live_custom = dict(ALL_THEMES[theme_pick])
                    st.toast(f"Tema {theme_pick} aplicado", icon=":material/palette:")
                    st.rerun()

                if st.session_state.app_theme == "🎨 Personalizado":
                    with st.expander("Personalizar paleta", expanded=True):
                        st.caption("Ajusta los colores de la interfaz.")
                        c_col1, c_col2 = st.columns(2)
                        with c_col1:
                            new_bg_base = st.color_picker("Fondo principal", st.session_state.live_custom["bg_base"])
                            new_bg_card = st.color_picker("Paneles", st.session_state.live_custom["bg_card"])
                            new_bg_sidebar = st.color_picker("Barra lateral", st.session_state.live_custom["bg_sidebar"])
                            new_border = st.color_picker("Bordes", st.session_state.live_custom["border"])
                        with c_col2:
                            new_text = st.color_picker("Texto principal", st.session_state.live_custom["text"])
                            new_text_muted = st.color_picker("Texto secundario", st.session_state.live_custom["text_muted"])
                            new_accent = st.color_picker("Acento", st.session_state.live_custom["accent"])
                            new_border_hover = st.color_picker("Borde al pasar", st.session_state.live_custom["border_hover"])

                        changed = False
                        for k, val in [
                            ("bg_base", new_bg_base), ("bg_card", new_bg_card),
                            ("bg_sidebar", new_bg_sidebar), ("border", new_border),
                            ("border_hover", new_border_hover), ("accent", new_accent),
                            ("text", new_text), ("text_muted", new_text_muted),
                        ]:
                            if st.session_state.live_custom[k] != val:
                                st.session_state.live_custom[k] = val
                                changed = True
                        if changed:
                            st.session_state.live_custom["accent_light"] = f"{new_accent}26"
                            st.rerun()

                        theme_name_input = st.text_input("Nombre del tema", placeholder="Ej. Mi tema")
                        if st.button("Guardar tema", icon=":material/save:", use_container_width=True, key="save_custom_theme"):
                            t_name = theme_name_input.strip()
                            if t_name:
                                st.session_state.saved_custom_themes[t_name] = dict(st.session_state.live_custom)
                                save_custom_themes(st.session_state.saved_custom_themes)
                                st.session_state.app_theme = t_name
                                st.toast("Tema guardado", icon=":material/check_circle:")
                                st.rerun()
                            else:
                                st.toast("Escribe un nombre para guardar el tema", icon=":material/warning:")

                if st.session_state.app_theme in st.session_state.saved_custom_themes:
                    st.caption(f"Tema personalizado: {st.session_state.app_theme}")
                    if st.button("Eliminar tema personalizado", icon=":material/delete:", use_container_width=True, key="delete_custom_theme"):
                        deleted_name = st.session_state.app_theme
                        del st.session_state.saved_custom_themes[deleted_name]
                        save_custom_themes(st.session_state.saved_custom_themes)
                        st.session_state.app_theme = "Minimal Light (Papel & Lino)"
                        st.toast("Tema personalizado eliminado", icon=":material/check_circle:")
                        st.rerun()

            elif st.session_state.sidebar_module == "session":
                st.markdown('<div class="sidebar-section-label">SESIÓN</div>', unsafe_allow_html=True)
                st.caption(f"{len(st.session_state.messages)} mensajes en esta conversación")
                if st.button("Limpiar conversación", icon=":material/mop:", use_container_width=True, key="clear_conversation"):
                    st.session_state.messages = [
                        {"role": "assistant", "content": "Conversación reiniciada. ¿Qué consulta deseas realizar?"}
                    ]
                    st.session_state.highlight_words = []
                    st.toast("Conversación limpiada", icon=":material/check_circle:")
                    st.rerun()
                st.caption("El historial se conserva solo durante esta sesión.")

# --- CABECERA STICKY Y SELECTOR DE PANELES ---
with st.container(key="workspace_header"):
    active_label = st.session_state.file_name if st.session_state.file_name else "Todos los documentos"
    st.markdown(f"""
        <div class="workspace-heading">
            <div class="workspace-eyebrow">DOCUMENT STUDIO</div>
            <div class="workspace-title">{active_label[:48]}</div>
        </div>
    """, unsafe_allow_html=True)

with st.container(key="view_switcher"):
    if st.button("Chat", icon=":material/chat_bubble_outline:", key="toggle_chat", type="primary" if st.session_state.show_chat else "secondary", use_container_width=True):
        st.session_state.show_chat = not st.session_state.show_chat
        st.toast("Chat activado" if st.session_state.show_chat else "Chat ocultado", icon=":material/chat_bubble_outline:")
        st.rerun()
    if st.button("Documento", icon=":material/menu_book:", key="toggle_pdf", type="primary" if st.session_state.show_pdf else "secondary", use_container_width=True):
        st.session_state.show_pdf = not st.session_state.show_pdf
        st.toast("Visor PDF activado" if st.session_state.show_pdf else "Visor PDF ocultado", icon=":material/menu_book:")
        st.rerun()
    if st.button("Resumen", icon=":material/subject:", key="toggle_sum", type="primary" if st.session_state.show_summary else "secondary", use_container_width=True):
        st.session_state.show_summary = not st.session_state.show_summary
        st.toast("Síntesis activada" if st.session_state.show_summary else "Síntesis ocultada", icon=":material/subject:")
        st.rerun()


# --- COMPONENTES PRINCIPALES ---

def render_chat(is_full=False):
    with st.container(key="chat_panel"):
        _render_chat_content(is_full)


def _render_chat_content(is_full=False):
    """Panel de conversación con citas directas y menú inferior orgánico estilo ChatGPT."""
    st.markdown("""
        <div class="panel-heading">
            <div class="panel-kicker">CONSULTA DOCUMENTAL</div>
            <div class="panel-title">Chat con el documento</div>
            <div class="panel-description">Pregunta y sigue cada referencia hasta su página.</div>
        </div>
    """, unsafe_allow_html=True)
    feed_h = 420
    chat_box = st.container(height=feed_h, key="chat_feed")

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
                                    st.toast(f"Navegando a la página {p_num}", icon=":material/menu_book:")
                                    st.rerun()

    # --- BARRA INFERIOR DE CONFIGURACIÓN ORGÁNICA (ESTILO CHATGPT) ---
    with st.expander("⚙️ Parámetros de Modelo, Chunks y Vectores (Local / Nube)", expanded=False):
        c_mod, c_chunk, c_topk = st.columns([0.40, 0.35, 0.25], gap="small")

        with c_mod:
            provider_list = ["Ollama (Local)", "Llama.cpp Server (Local)", "Google Gemini (Nube)", "OpenAI / Groq API (Nube)"]
            selected_provider = st.selectbox(
                "Motor de Inferencia:",
                options=provider_list,
                index=provider_list.index(st.session_state.ai_provider),
            )
            st.caption("Elige un modelo local o un proveedor de IA en la nube.")
            if selected_provider != st.session_state.ai_provider:
                st.session_state.ai_provider = selected_provider
                st.rerun()

            # Opciones según el proveedor
            if selected_provider == "Ollama (Local)":
                st.session_state.local_model = st.text_input("Modelo Ollama:", value=st.session_state.local_model)
                st.caption("Ejemplos: qwen2.5:7b, llama3:8b, mistral o llava.")
            elif selected_provider == "Llama.cpp Server (Local)":
                st.session_state.llamacpp_url = st.text_input("URL Llama.cpp Server:", value=st.session_state.llamacpp_url)
                st.caption("Usa la URL del servidor llama-server (puerto 8080 por defecto).")
            elif "Gemini" in selected_provider:
                st.session_state.cloud_api_key = st.text_input("Gemini API Key:", value=st.session_state.cloud_api_key, type="password")
                st.caption("Obtén tu clave en Google AI Studio.")
                st.session_state.cloud_model_name = st.selectbox("Modelo Gemini:", ["gemini-1.5-flash", "gemini-1.5-pro"])
            elif "OpenAI" in selected_provider:
                st.session_state.cloud_api_key = st.text_input("API Key (OpenAI o Groq):", value=st.session_state.cloud_api_key, type="password")

        with c_chunk:
            st.session_state.chunk_size = st.slider("Tamaño del fragmento (caracteres):", min_value=250, max_value=1200, value=st.session_state.chunk_size, step=50)
            st.session_state.chunk_overlap = st.slider("Solapamiento entre fragmentos:", min_value=20, max_value=200, value=st.session_state.chunk_overlap, step=10)

        with c_topk:
            st.session_state.top_k_chunks = st.slider("Fragmentos relevantes para la respuesta:", min_value=2, max_value=12, value=st.session_state.top_k_chunks, step=1)

    # El composer es el último elemento del panel para que permanezca anclado abajo.
    with st.container(key="chat_composer"):
        prompt = st.chat_input(
            "Escribe tu consulta sobre el contenido o imágenes...",
            key="document_chat_input",
        )

    # Procesar consulta
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Vía 1: Consultas ultrarrápidas de cortesía y saludo (sin RAG ni carga en GPU)
        clean_p = prompt.strip().lower()
        if clean_p in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "que tal", "hola!", "holaa", "saludos"]:
            fast_ans = "¡Hola! Estoy listo para responder consultas técnicas sobre tu documento. Puedes preguntarme sobre el texto, pasos o sobre cualquier imagen que contenga."
            st.session_state.messages.append({"role": "assistant", "content": fast_ans})
            st.toast("Respuesta rápida lista", icon=":material/check_circle:")
            st.rerun()
        elif clean_p in ["gracias", "muchas gracias", "ok gracias", "vale gracias", "perfecto gracias"]:
            fast_ans = "¡Con gusto! Quedo a tu disposición si necesitas verificar cualquier otro dato o página."
            st.session_state.messages.append({"role": "assistant", "content": fast_ans})
            st.toast("Conversación actualizada", icon=":material/check_circle:")
            st.rerun()

        # Vía 2: Consulta Documental RAG
        st.toast("Buscando referencias en el documento", icon=":material/search:")
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

        if ans.lstrip().startswith("Error"):
            st.toast("No se pudo completar la consulta. Revisa el proveedor seleccionado.", icon=":material/error:")

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
        if not ans.lstrip().startswith("Error"):
            st.toast("Respuesta lista con referencias", icon=":material/check_circle:")
        st.rerun()


def render_pdf_viewer(is_full=False):
    """Visor continuo de documento."""
    st.markdown("""
        <div class="panel-heading">
            <div class="panel-kicker">FUENTE ORIGINAL</div>
            <div class="panel-title">Lectura del PDF</div>
            <div class="panel-description">Navega por las páginas y revisa las citas.</div>
        </div>
    """, unsafe_allow_html=True)
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
        st.markdown("""
            <div class="empty-document">
                <div class="empty-document-mark">PDF</div>
                <div class="empty-document-title">Tu documento aparecerá aquí</div>
                <div class="empty-document-copy">Selecciona un archivo de tu biblioteca o carga un PDF desde el panel lateral para comenzar.</div>
            </div>
        """, unsafe_allow_html=True)


def render_summary(is_full=False):
    """Panel de síntesis documental."""
    st.markdown(f"""
        <div class="panel-heading">
            <div class="panel-kicker">LECTURA RÁPIDA</div>
            <div class="panel-title">Síntesis del documento</div>
            <div class="panel-description">{st.session_state.file_name or 'Selecciona un documento para empezar.'}</div>
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
            st.toast("Preparando la síntesis", icon=":material/hourglass_top:")
            with st.spinner("Generando síntesis..."):
                try:
                    p = f"Elabora una síntesis estructurada por puntos clave del documento '{st.session_state.file_name}':\n\n{st.session_state.full_doc_text[:12000]}"
                    r = call_llm(p, "Eres un analista documental experto.", [])
                    st.session_state.summary = r
                    if r.lstrip().startswith("Error"):
                        st.toast("No se pudo generar la síntesis", icon=":material/error:")
                    else:
                        st.toast("Síntesis lista", icon=":material/check_circle:")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.toast("Falló la generación de la síntesis", icon=":material/error:")


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
