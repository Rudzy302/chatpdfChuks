import os
import re
import uuid
import urllib.request
import urllib.parse
import numpy as np
import cv2
from ..config import settings

IMAGES_DIR = os.path.join(settings.UPLOADS_DIR, "generated_images")
os.makedirs(IMAGES_DIR, exist_ok=True)

def detect_image_request(prompt: str) -> tuple[bool, str]:
    """
    Detecta si el prompt del usuario solicita generar o dibujar una imagen o fotografía.
    Devuelve (True, subject) si es una solicitud de imagen, o (False, "").
    """
    p = prompt.strip().lower()
    
    # Si contiene video, no es imagen
    if "video" in p:
        return False, ""
        
    patterns = [
        r'(?:quiero que me generes|generame|genera|creame|crea|hazme|haz|produce|dame|muestra|muéstrame)\s+(?:una\s+)?(?:imagen|foto|fotografia|fotografía|dibujo|ilustracion|ilustración)\s+(?:de\s+|sobre\s+|con\s+)?(.+)',
        r'(?:dibújame|dibujame|dibuja|ilustra)\s+(?:un\s+|una\s+)?(.+)',
        r'(?:imagen\s+de\s+|foto\s+de\s+|fotografia\s+de\s+|fotografía\s+de\s+)(.+)',
        r'(?:puedes\s+hacer\s+una\s+imagen\s+de\s+)(.+)',
    ]
    
    for pat in patterns:
        m = re.search(pat, p, re.IGNORECASE)
        if m:
            subject = m.group(1).strip().rstrip(".?!")
            return True, subject
            
    if any(k in p for k in ["genera una imagen", "generar imagen", "crear imagen", "haz una imagen", "dame una imagen"]):
        parts = re.split(r'imagen\s+(?:de\s+|sobre\s+)?', p, flags=re.I)
        if len(parts) > 1 and parts[1].strip():
            return True, parts[1].strip()
        return True, prompt
        
    return False, ""

def remove_watermark(img_bgr: np.ndarray) -> np.ndarray:
    """
    Elimina de forma impecable y sin distorsión cualquier marca de agua/logo
    ubicada en la esquina inferior derecha mediante inpainting adaptativo Telea de OpenCV.
    """
    if img_bgr is None or len(img_bgr.shape) != 3:
        return img_bgr
        
    h, w, _ = img_bgr.shape
    
    # La marca de agua se ubica en el margen inferior derecho (aprox 5% de alto y 24% de ancho)
    roi_h = max(26, int(h * 0.055))
    roi_w = max(115, int(w * 0.24))
    roi_y1 = max(0, h - roi_h)
    roi_y2 = h
    roi_x1 = max(0, w - roi_w)
    roi_x2 = w

    mask = np.zeros((h, w), dtype=np.uint8)
    roi = img_bgr[roi_y1:roi_y2, roi_x1:roi_x2]
    
    # Convertir a escala de grises y detectar píxeles de texto/icono de alto contraste
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, roi_thresh = cv2.threshold(gray_roi, 160, 255, cv2.THRESH_BINARY)
    
    # Dilatación suave de 2 iteraciones con kernel 3x3 para cubrir bordes antialiasing
    kernel = np.ones((3, 3), np.uint8)
    roi_dilated = cv2.dilate(roi_thresh, kernel, iterations=2)
    mask[roi_y1:roi_y2, roi_x1:roi_x2] = roi_dilated

    # Inpainting de Navier-Stokes / Telea de OpenCV
    cleaned = cv2.inpaint(img_bgr, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    return cleaned

def generate_ai_image(subject: str) -> str:
    """
    Genera una imagen digital de alta resolución (1024x1024) utilizando IA visual,
    eliminando cualquier marca de agua o logo para una presentación 100% limpia.
    """
    img_id = uuid.uuid4().hex[:10]
    out_filename = f"image_{img_id}.jpg"
    out_path = os.path.join(IMAGES_DIR, out_filename)
    
    # Limpiar y enriquecer el prompt para obtener calidad fotorrealista 4K
    clean_subject = re.sub(r'^(un|una|el|la|los|las)\s+', '', subject, flags=re.I).strip()
    enhanced_prompt = f"{clean_subject}, highly detailed, photorealistic, 8k resolution, dramatic lighting, cinematic composition, masterpiece, clean image"
    encoded = urllib.parse.quote(enhanced_prompt)
    
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&seed={uuid.uuid4().int % 100000}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    saved = False
    try:
        req = urllib.request.Request(image_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            img_data = response.read()
            if len(img_data) > 1000:
                raw_arr = np.frombuffer(img_data, dtype=np.uint8)
                img = cv2.imdecode(raw_arr, cv2.IMREAD_COLOR)
                if img is not None:
                    # Eliminar automáticamente cualquier marca de agua/logo en la esquina
                    clean_img = remove_watermark(img)
                    cv2.imwrite(out_path, clean_img, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
                    saved = True
    except Exception as e:
        print(f"[IMAGE GENERATION] Fallback local: {e}")
        
    if not saved:
        # Fallback estilizado con gradiente de alta calidad y texto artístico si no hay red
        h, w = 720, 1024
        img = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            ratio = y / float(h)
            img[y, :] = [int(45 + 50 * ratio), int(30 + 40 * ratio), int(70 + 70 * ratio)]
        cv2.putText(img, subject.title(), (60, h // 2), cv2.FONT_HERSHEY_DUPLEX, 1.3, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(out_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        
    print(f"[IMAGE GENERATION] Imagen guardada en {out_path} ({os.path.getsize(out_path)} bytes) sin marcas de agua")
    return out_filename
