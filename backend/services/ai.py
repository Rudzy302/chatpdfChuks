import json
import urllib.request
import urllib.error
import hashlib
import ollama
from ..config import settings
from .ocr import prepare_image_for_vision

def generate_embedding(text: str) -> list:
    """Genera vector de 768 dimensiones con nomic-embed-text o embedding determinista si el servidor falla."""
    try:
        embed_res = ollama.embeddings(model=settings.DEFAULT_EMBED_MODEL, prompt=text)
        return embed_res["embedding"]
    except Exception:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [(float(b) / 255.0) - 0.5 for b in h]
        while len(vec) < 768:
            vec.extend(vec[:768 - len(vec)])
        return vec[:768]

def describe_image_with_vision(img_bytes: bytes, page_num: int, provider: str = "Ollama (Local)", api_key: str = "") -> str:
    """Genera descripción y transcripción de elementos visuales (animales, plantas, diagramas o texto en imágenes)."""
    # 1. Google Gemini
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

    # 2. Inferencia local Ollama con llava:7b
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

def call_llm(prompt: str, system_prompt: str, history: list, provider: str = "Ollama (Local)", api_key: str = "", model_name: str = "") -> str:
    """Ejecuta consulta según el proveedor configurado (Ollama, Gemini, OpenAI/Groq o Llama.cpp)."""
    # 1. Google Gemini
    if provider == "Google Gemini (Nube)":
        if not api_key:
            return "Debes ingresar tu API Key de Google Gemini."
        try:
            m_name = model_name or "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
            
            contents = []
            contents.append({"role": "user", "parts": [{"text": f"Instrucciones del sistema:\n{system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Entendido, seguiré estrictamente las instrucciones y citaré [Pág. X]."}]})
            for m in history:
                role = "user" if m.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
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
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            return f"Error en Google Gemini API ({e.code}): {err_msg}"
        except Exception as e:
            return f"Error al conectar con Google Gemini: {e}"

    # 2. Llama.cpp Server (Local CUDA)
    elif provider == "Llama.cpp Server (Local)":
        endpoint = settings.LLAMACPP_URL.rstrip("/") + "/chat/completions"
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
            return f"Error al conectar con llama.cpp en {endpoint}: {e}"

    # 3. OpenAI / Groq
    elif provider == "OpenAI / Groq API (Nube)":
        if not api_key:
            return "Ingresa tu API Key de OpenAI / Groq."
        try:
            endpoint = "https://api.openai.com/v1/chat/completions"
            model_target = "gpt-4o-mini"
            if api_key.startswith("gsk_"):
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

    # 4. Ollama (Local)
    else:
        try:
            recent_history = history[-4:] if len(history) > 4 else history
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend([{"role": m["role"], "content": m["content"]} for m in recent_history])
            messages.append({"role": "user", "content": prompt})

            target_m = model_name or settings.DEFAULT_CHAT_MODEL
            try:
                resp = ollama.chat(
                    model=target_m,
                    messages=messages
                )
                return resp["message"]["content"]
            except Exception as e_primary:
                # Si el modelo específico falla, intentar con otros modelos locales instalados
                for fallback in ["qwen2.5:14b", "qwen2.5:7b", "mistral-small:24b"]:
                    if fallback != target_m:
                        try:
                            resp = ollama.chat(model=fallback, messages=messages)
                            return resp["message"]["content"]
                        except Exception:
                            continue
                raise e_primary
        except Exception as e:
            return f"Error al consultar Ollama local: {e}"
