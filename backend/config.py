import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "Document Studio API"
    APP_VERSION: str = "2.0.0"
    
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOADS_DIR: str = os.path.join(BASE_DIR, "uploads")
    
    DB_USER: str = os.environ.get("DB_USER", "admin")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "admin")
    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_PORT: int = int(os.environ.get("DB_PORT", "5433"))
    DB_NAME: str = os.environ.get("DB_NAME", "rag_db")
    
    OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    DEFAULT_EMBED_MODEL: str = "nomic-embed-text"
    DEFAULT_CHAT_MODEL: str = "qwen2.5:7b"
    LLAMACPP_URL: str = os.environ.get("LLAMACPP_URL", "http://localhost:8080/v1")
    
    MAX_PDF_PAGES: int = int(os.environ.get("MAX_PDF_PAGES", "150"))

settings = Settings()
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
