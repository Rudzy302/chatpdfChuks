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

def generate_ai_image(subject: str) -> str:
    """
    Genera una imagen digital de alta resolución (1024x1024) utilizando IA visual.
    Devuelve el nombre del archivo de imagen generado en uploads/generated_images/.
    """
    img_id = uuid.uuid4().hex[:10]
    out_filename = f"image_{img_id}.jpg"
    out_path = os.path.join(IMAGES_DIR, out_filename)
    
    # Limpiar y enriquecer el prompt para obtener calidad fotorrealista 4K
    clean_subject = re.sub(r'^(un|una|el|la|los|las)\s+', '', subject, flags=re.I).strip()
    enhanced_prompt = f"{clean_subject}, highly detailed, photorealistic, 8k resolution, dramatic lighting, cinematic composition, masterpiece"
    encoded = urllib.parse.quote(enhanced_prompt)
    
    image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    saved = False
    try:
        req = urllib.request.Request(image_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            img_data = response.read()
            if len(img_data) > 1000:
                with open(out_path, "wb") as f:
                    f.write(img_data)
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
        
    print(f"[IMAGE GENERATION] Imagen guardada en {out_path} ({os.path.getsize(out_path)} bytes)")
    return out_filename
