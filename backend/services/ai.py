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
    """Ejecuta consulta según el proveedor configurado (OpenRouter, DeepSeek, Gemini, OpenAI/Groq, Llama.cpp o Ollama)."""
    clean_provider = provider.lower()

    # 1. OpenRouter (Conector Universal: DeepSeek, GPT-4o, Claude, Gemini)
    if "openrouter" in clean_provider:
        if not api_key:
            return "Debes ingresar tu API Key de OpenRouter (puedes obtener una 100% gratis en openrouter.ai con tu cuenta de Google)."
        try:
            endpoint = "https://openrouter.ai/api/v1/chat/completions"
            m_target = model_name or "deepseek/deepseek-r1:free"

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend([{"role": m["role"], "content": m["content"]} for m in history[-6:]])
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": m_target,
                "messages": messages,
                "temperature": 0.2
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "http://127.0.0.1:4173",
                    "X-Title": "Document Studio RAG"
                }
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            return f"Error en OpenRouter API ({e.code}): {err_msg}"
        except Exception as e:
            return f"Error al conectar con OpenRouter: {e}"

    # 2. DeepSeek API (Oficial)
    elif "deepseek" in clean_provider:
        if not api_key:
            return "Debes ingresar tu API Key oficial de DeepSeek."
        try:
            endpoint = "https://api.deepseek.com/chat/completions"
            m_target = model_name or "deepseek-chat"

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend([{"role": m["role"], "content": m["content"]} for m in history[-6:]])
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": m_target,
                "messages": messages,
                "temperature": 0.2
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            return f"Error en DeepSeek API ({e.code}): {err_msg}"
        except Exception as e:
            return f"Error al conectar con DeepSeek: {e}"

    # 3. Google Gemini
    elif "gemini" in clean_provider:
        if not api_key:
            return "Debes ingresar tu API Key de Google Gemini (gratuita en aistudio.google.com)."
        try:
            m_name = model_name or "gemini-2.0-flash"
            if m_name.startswith("models/"):
                m_name = m_name.replace("models/", "")
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

    # 4. OpenAI / Groq
    elif "openai" in clean_provider or "groq" in clean_provider:
        if not api_key:
            return "Ingresa tu API Key de OpenAI / Groq."
        try:
            endpoint = "https://api.openai.com/v1/chat/completions"
            model_target = model_name or "gpt-4o"
            if api_key.startswith("gsk_"):
                endpoint = "https://api.groq.com/openai/v1/chat/completions"
                model_target = model_name or "llama-3.1-8b-instant"

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

    # 5. Llama.cpp Server (Local CUDA)
    elif "llama.cpp" in clean_provider:
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

    # 6. Ollama (Local)
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

def detect_account_models(provider: str, api_key: str = "") -> dict:
    """
    Detecta automáticamente en vivo el plan de la cuenta y los modelos disponibles
    del proveedor seleccionado (OpenRouter, Gemini, DeepSeek, OpenAI u Ollama).
    """
    clean_provider = provider.lower()
    headers_user_agent = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # 1. OpenRouter (Universal)
    if "openrouter" in clean_provider:
        plan_label = "Cuenta OpenRouter Gratuita"
        is_free_tier = True
        limit_desc = "Sin límite de tarjeta (Modelos :free ilimitados)"

        if api_key:
            try:
                auth_req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {api_key}", **headers_user_agent}
                )
                with urllib.request.urlopen(auth_req, timeout=8) as auth_res:
                    k_data = json.loads(auth_res.read().decode("utf-8")).get("data", {})
                    is_free_tier = k_data.get("is_free_tier", True)
                    usage = k_data.get("usage", 0.0)
                    limit = k_data.get("limit")
                    lbl = k_data.get("label", "")
                    if is_free_tier:
                        plan_label = f"Plan Gratuito Activo ({lbl or 'OpenRouter'})"
                        limit_desc = f"Consumo: ${usage:.3f} • Modelos :free ilimitados"
                    else:
                        plan_label = f"Plan con Saldo / Suscripción ({lbl or 'OpenRouter'})"
                        limit_desc = f"Límite: ${limit if limit else 'Ilimitado'} • Consumo: ${usage:.2f}"
            except Exception:
                pass

        # Obtener lista completa de modelos de OpenRouter
        models = []
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers=headers_user_agent)
            with urllib.request.urlopen(req, timeout=10) as res:
                all_models = json.loads(res.read().decode("utf-8")).get("data", [])
                
                # Modelos populares de alta prioridad a destacar
                curated_priorities = [
                    "deepseek/deepseek-r1:free",
                    "deepseek/deepseek-chat:free",
                    "google/gemini-2.0-flash-exp:free",
                    "google/gemini-2.0-flash-thinking-exp:free",
                    "meta-llama/llama-3.3-70b-instruct:free",
                    "qwen/qwen-2.5-coder-32b-instruct:free",
                    "mistralai/mistral-small-24b-instruct-2501:free",
                    "openai/gpt-4o",
                    "openai/gpt-4o-mini",
                    "openai/o1",
                    "openai/o3-mini",
                    "anthropic/claude-3.5-sonnet",
                    "anthropic/claude-3-opus",
                    "deepseek/deepseek-r1",
                    "google/gemini-2.0-flash-001",
                    "google/gemini-pro-1.5"
                ]

                # 1. Agregar los modelos prioritarios si existen en la respuesta
                seen_ids = set()
                for prio in curated_priorities:
                    m_match = next((m for m in all_models if m.get("id") == prio), None)
                    if m_match:
                        is_free = ":free" in m_match["id"]
                        models.append({
                            "id": m_match["id"],
                            "name": m_match.get("name", m_match["id"]),
                            "category": "🟢 Gratuito Ilimitado" if is_free else "🟣 Avanzado / Razonamiento",
                            "is_free": is_free,
                            "context_length": m_match.get("context_length", 32768)
                        })
                        seen_ids.add(m_match["id"])

                # 2. Agregar el resto de modelos :free disponibles
                for m in all_models:
                    if ":free" in m.get("id", "") and m["id"] not in seen_ids:
                        models.append({
                            "id": m["id"],
                            "name": m.get("name", m["id"]),
                            "category": "🟢 Gratuito Ilimitado",
                            "is_free": True,
                            "context_length": m.get("context_length", 32768)
                        })
                        seen_ids.add(m["id"])
        except Exception as e:
            # Fallback predeterminado de alta disponibilidad si la red falla
            models = [
                {"id": "deepseek/deepseek-r1:free", "name": "DeepSeek R1 Reasoning (Gratis)", "category": "🟢 Gratuito Ilimitado", "is_free": True},
                {"id": "deepseek/deepseek-chat:free", "name": "DeepSeek V3 Chat (Gratis)", "category": "🟢 Gratuito Ilimitado", "is_free": True},
                {"id": "google/gemini-2.0-flash-exp:free", "name": "Google Gemini 2.0 Flash (Gratis)", "category": "🟢 Gratuito Ilimitado", "is_free": True},
                {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Meta Llama 3.3 70B (Gratis)", "category": "🟢 Gratuito Ilimitado", "is_free": True},
                {"id": "openai/gpt-4o", "name": "OpenAI GPT-4o (Avanzado)", "category": "🟣 Avanzado / Razonamiento", "is_free": False},
                {"id": "anthropic/claude-3.5-sonnet", "name": "Anthropic Claude 3.5 Sonnet (Avanzado)", "category": "🟣 Avanzado / Razonamiento", "is_free": False},
            ]

        return {
            "status": "ok",
            "provider": "OpenRouter",
            "plan_info": {
                "name": plan_label,
                "is_free_tier": is_free_tier,
                "description": limit_desc
            },
            "models": models
        }

    # 2. Google Gemini
    elif "gemini" in clean_provider:
        models = []
        plan_desc = "Plan Google AI Studio (Nivel Gratuito: 15 req/min sin costo)"
        if api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                req = urllib.request.Request(url, headers=headers_user_agent)
                with urllib.request.urlopen(req, timeout=8) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    raw_models = []
                    for m in data.get("models", []):
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            mid = m["name"].replace("models/", "")
                            display_n = m.get("displayName", mid)
                            
                            # Prioridad de ordenación: gemini-2.5, gemini-2.0, gemini-1.5 al inicio
                            priority = 99
                            if "gemini-2.5-flash" in mid:
                                priority = 1
                            elif "gemini-2.0-flash" in mid:
                                priority = 2
                            elif "gemini-1.5-pro" in mid:
                                priority = 3
                            elif "gemini-1.5-flash" in mid:
                                priority = 4
                            elif mid.startswith("gemini-"):
                                priority = 10
                            elif "deep-research" in mid:
                                priority = 30
                                display_n = f"Google Deep Research ({display_n})"

                            raw_models.append((priority, {
                                "id": mid,
                                "name": display_n,
                                "category": "Google Gemini",
                                "is_free": True,
                                "context_length": m.get("inputTokenLimit", 1000000)
                            }))
                    
                    raw_models.sort(key=lambda x: (x[0], x[1]["name"]))
                    models = [m[1] for m in raw_models]
            except Exception:
                pass

        if not models:
            models = [
                {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Ultrarrápido - Recomendado)", "category": "Google Gemini", "is_free": True},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro (Razonamiento y Contexto Largo)", "category": "Google Gemini", "is_free": True},
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash (Ligero y Eficiente)", "category": "Google Gemini", "is_free": True},
            ]

        return {
            "status": "ok",
            "provider": "Google Gemini",
            "plan_info": {"name": "Google AI Studio", "is_free_tier": True, "description": plan_desc},
            "models": models
        }

    # 3. DeepSeek API (Oficial)
    elif "deepseek" in clean_provider:
        models = [
            {"id": "deepseek-chat", "name": "DeepSeek-V3 (Chat Rápido y Versátil)", "category": "DeepSeek Oficial", "is_free": False},
            {"id": "deepseek-reasoner", "name": "DeepSeek-R1 (Razonamiento Matemático y Lógica)", "category": "DeepSeek Oficial", "is_free": False},
        ]
        return {
            "status": "ok",
            "provider": "DeepSeek API",
            "plan_info": {"name": "DeepSeek Platform Oficial", "is_free_tier": False, "description": "Conexión directa por API token"},
            "models": models
        }

    # 4. OpenAI
    elif "openai" in clean_provider:
        models = [
            {"id": "gpt-4o", "name": "GPT-4o (Omni Multimodal)", "category": "OpenAI Oficial", "is_free": False},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Económico y Rápido)", "category": "OpenAI Oficial", "is_free": False},
            {"id": "o1-mini", "name": "OpenAI o1-mini (Razonamiento STEM)", "category": "OpenAI Oficial", "is_free": False},
            {"id": "o3-mini", "name": "OpenAI o3-mini (Alta Eficiencia)", "category": "OpenAI Oficial", "is_free": False},
        ]
        return {
            "status": "ok",
            "provider": "OpenAI",
            "plan_info": {"name": "OpenAI Platform", "is_free_tier": False, "description": "Modelos oficiales de OpenAI"},
            "models": models
        }

    # 5. Ollama (Local)
    else:
        models = []
        try:
            tags_resp = ollama.list()
            for m in tags_resp.get("models", []):
                m_name = m.get("name", m.get("model", ""))
                if m_name:
                    models.append({
                        "id": m_name,
                        "name": f"{m_name} (Local en tu PC)",
                        "category": "🟢 Local sin Límites",
                        "is_free": True
                    })
        except Exception:
            pass

        if not models:
            models = [
                {"id": "qwen2.5:14b", "name": "qwen2.5:14b (Local)", "category": "🟢 Local sin Límites", "is_free": True},
                {"id": "qwen2.5:7b", "name": "qwen2.5:7b (Local)", "category": "🟢 Local sin Límites", "is_free": True},
                {"id": "mistral-small:24b", "name": "mistral-small:24b (Local)", "category": "🟢 Local sin Límites", "is_free": True},
            ]

        return {
            "status": "ok",
            "provider": "Ollama (Local)",
            "plan_info": {"name": "Ollama Local GPU/CPU", "is_free_tier": True, "description": "100% privado, ilimitado y sin costo de red"},
            "models": models
        }
