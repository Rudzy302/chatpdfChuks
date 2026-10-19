import io
import base64
from PIL import Image

try:
    from rapidocr_onnxruntime import RapidOCR
    _ocr_engine = RapidOCR()
except Exception:
    _ocr_engine = None

def get_ocr_engine():
    return _ocr_engine

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

def prepare_image_for_vision(img_bytes: bytes, max_dim: int = 768) -> str:
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
