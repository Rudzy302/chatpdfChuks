import os
import json
import math
import sqlite3
import datetime
from .config import settings

SQLITE_PATH = os.path.join(settings.BASE_DIR, "rag_local.db")

def cosine_distance(vec_a: list, vec_b: list) -> float:
    """Calcula la distancia coseno entre dos vectores (1 - similitud coseno)."""
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    sim = dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
    return 1.0 - sim

class DatabaseClient:
    """Cliente robusto: conecta directamente a PostgreSQL (pgvector en puerto 5433); si Docker está temporalmente offline, conmuta a SQLite."""
    def __init__(self):
        self.mode = "sqlite"
        try:
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                timeout=3
            )
            con.close()
            self.mode = "postgres"
            print(f"[DB] Conectado exitosamente a PostgreSQL (pgvector) en {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
        except Exception as e:
            self.mode = "sqlite"
            print(f"[DB] PostgreSQL no disponible ({e}). Usando fallback SQLite.")
        
        try:
            self.init_schema()
        except Exception as e:
            print(f"[DB] Error inicializando esquema: {e}")

    def init_schema(self):
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
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

            # Tablas de sesiones e historial persistente
            con.run("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    active_doc TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            con.run("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    role TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            con.run("CREATE INDEX IF NOT EXISTS idx_chat_msgs_session ON chat_messages(session_id);")
            con.close()
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    page_number INTEGER DEFAULT 1,
                    chunk_index INTEGER,
                    chunk_type TEXT DEFAULT 'text',
                    content TEXT,
                    embedding TEXT
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_fn ON document_chunks (filename);")

            # Tablas de sesiones e historial persistente en SQLite
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    active_doc TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_msgs_session ON chat_messages(session_id);")
            con.commit()
            con.close()

    def get_indexed_documents(self):
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
            rows = con.run("""
                SELECT filename, count(*), min(page_number), max(page_number)
                FROM document_chunks
                GROUP BY filename
                ORDER BY filename;
            """)
            con.close()
            return [{"filename": r[0], "chunks": r[1], "min_page": r[2] or 1, "max_page": r[3] or 1} for r in rows]
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            cur.execute("""
                SELECT filename, count(*), min(page_number), max(page_number)
                FROM document_chunks
                GROUP BY filename
                ORDER BY filename;
            """)
            rows = cur.fetchall()
            con.close()
            return [{"filename": r[0], "chunks": r[1], "min_page": r[2] or 1, "max_page": r[3] or 1} for r in rows]

    def delete_document(self, filename: str):
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
            con.run("DELETE FROM document_chunks WHERE filename = :fname;", fname=filename)
            con.close()
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            cur.execute("DELETE FROM document_chunks WHERE filename = ?", (filename,))
            con.commit()
            con.close()

    def insert_chunks(self, filename: str, chunks_with_embeddings: list):
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=10
            )
            con.run("DELETE FROM document_chunks WHERE filename = :fname;", fname=filename)
            for item in chunks_with_embeddings:
                con.run(
                    """
                    INSERT INTO document_chunks (filename, page_number, chunk_index, chunk_type, content, embedding)
                    VALUES (:fname, :pnum, :cidx, :ctype, :cont, :emb::vector);
                    """,
                    fname=filename,
                    pnum=item["page"],
                    cidx=item["index"],
                    ctype=item["type"],
                    cont=item["text"],
                    emb=json.dumps(item["embedding"])
                )
            con.close()
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            cur.execute("DELETE FROM document_chunks WHERE filename = ?", (filename,))
            for item in chunks_with_embeddings:
                cur.execute(
                    """
                    INSERT INTO document_chunks (filename, page_number, chunk_index, chunk_type, content, embedding)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (filename, item["page"], item["index"], item["type"], item["text"], json.dumps(item["embedding"]))
                )
            con.commit()
            con.close()

    def get_document_full_text(self, filename: str) -> str:
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
            rows = con.run("""
                SELECT page_number, content, chunk_type
                FROM document_chunks
                WHERE filename = :fname
                ORDER BY page_number ASC, chunk_index ASC;
            """, fname=filename)
            con.close()
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            cur.execute("""
                SELECT page_number, content, chunk_type
                FROM document_chunks
                WHERE filename = ?
                ORDER BY page_number ASC, chunk_index ASC;
            """, (filename,))
            rows = cur.fetchall()
            con.close()

        full_text = ""
        for pnum, content, ctype in rows:
            prefix = "[IMAGEN PÁG." if ctype == "image" else "[PÁGINA"
            full_text += f"\n{prefix} {pnum}]:\n" + content + "\n"
        return full_text

    def search_similar_chunks(self, query_embedding: list, filename: str = "", limit: int = 6):
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
            q_vec = json.dumps(query_embedding)
            if filename and filename != "Todos los documentos":
                sql = """
                    SELECT filename, page_number, chunk_index, content, chunk_type, (embedding <=> :emb::vector) AS dist
                    FROM document_chunks
                    WHERE filename = :fname
                    ORDER BY dist ASC
                    LIMIT :lim;
                """
                rows = con.run(sql, emb=q_vec, fname=filename, lim=limit)
            else:
                sql = """
                    SELECT filename, page_number, chunk_index, content, chunk_type, (embedding <=> :emb::vector) AS dist
                    FROM document_chunks
                    ORDER BY dist ASC
                    LIMIT :lim;
                """
                rows = con.run(sql, emb=q_vec, lim=limit)
            con.close()
            return rows
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            if filename and filename != "Todos los documentos":
                cur.execute("SELECT filename, page_number, chunk_index, content, chunk_type, embedding FROM document_chunks WHERE filename = ?", (filename,))
            else:
                cur.execute("SELECT filename, page_number, chunk_index, content, chunk_type, embedding FROM document_chunks")
            rows = cur.fetchall()
            con.close()

            scored = []
            for r in rows:
                try:
                    vec = json.loads(r[5])
                    dist = cosine_distance(query_embedding, vec)
                    scored.append((r[0], r[1], r[2], r[3], r[4], dist))
                except Exception:
                    continue

            scored.sort(key=lambda x: x[5])
            return scored[:limit]

    # --- MÉTODOS DE HISTORIAL Y SESIONES PERSISTENTES ---

    def create_chat_session(self, session_id: str, title: str = "Nuevo Chat", active_doc: str = "") -> dict:
        now_str = datetime.datetime.now().isoformat()
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
            con.run("""
                INSERT INTO chat_sessions (id, title, active_doc, created_at, updated_at)
                VALUES (:sid, :title, :adoc, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, active_doc = EXCLUDED.active_doc, updated_at = NOW();
            """, sid=session_id, title=title, adoc=active_doc)
            con.close()
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            cur.execute("""
                INSERT INTO chat_sessions (id, title, active_doc, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title, active_doc=excluded.active_doc, updated_at=excluded.updated_at;
            """, (session_id, title, active_doc, now_str, now_str))
            con.commit()
            con.close()
        return {"id": session_id, "title": title, "active_doc": active_doc, "updated_at": now_str}

    def list_chat_sessions(self) -> list:
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
            rows = con.run("""
                SELECT s.id, s.title, s.active_doc, s.updated_at,
                       COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON m.session_id = s.id
                GROUP BY s.id, s.title, s.active_doc, s.updated_at
                ORDER BY s.updated_at DESC;
            """)
            con.close()
            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "active_doc": r[2] or "",
                    "updated_at": str(r[3]),
                    "message_count": r[4]
                }
                for r in rows
            ]
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            cur.execute("""
                SELECT s.id, s.title, s.active_doc, s.updated_at,
                       COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON m.session_id = s.id
                GROUP BY s.id, s.title, s.active_doc, s.updated_at
                ORDER BY s.updated_at DESC;
            """)
            rows = cur.fetchall()
            con.close()
            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "active_doc": r[2] or "",
                    "updated_at": str(r[3]),
                    "message_count": r[4]
                }
                for r in rows
            ]

    def get_session_messages(self, session_id: str) -> list:
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
            rows = con.run("""
                SELECT role, content, created_at
                FROM chat_messages
                WHERE session_id = :sid
                ORDER BY id ASC;
            """, sid=session_id)
            con.close()
            return [{"role": r[0], "content": r[1], "created_at": str(r[2])} for r in rows]
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            cur.execute("""
                SELECT role, content, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC;
            """, (session_id,))
            rows = cur.fetchall()
            con.close()
            return [{"role": r[0], "content": r[1], "created_at": str(r[2])} for r in rows]

    def add_chat_message(self, session_id: str, role: str, content: str, active_doc: str = "", auto_title: bool = True):
        now_str = datetime.datetime.now().isoformat()
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
            # Asegurar que la sesión exista
            con.run("""
                INSERT INTO chat_sessions (id, title, active_doc, created_at, updated_at)
                VALUES (:sid, 'Nuevo Chat', :adoc, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET active_doc = CASE WHEN EXCLUDED.active_doc != '' THEN EXCLUDED.active_doc ELSE chat_sessions.active_doc END, updated_at = NOW();
            """, sid=session_id, adoc=active_doc)

            # Insertar mensaje
            con.run("""
                INSERT INTO chat_messages (session_id, role, content, created_at)
                VALUES (:sid, :role, :cont, NOW());
            """, sid=session_id, role=role, cont=content)

            # Auto actualizar título si era 'Nuevo Chat' y el mensaje es del usuario
            if auto_title and role == "user":
                t_snippet = content.strip().replace("\n", " ")[:40]
                if t_snippet:
                    con.run("""
                        UPDATE chat_sessions
                        SET title = :title
                        WHERE id = :sid AND (title = 'Nuevo Chat' OR title = '' OR title IS NULL);
                    """, title=t_snippet, sid=session_id)
            con.close()
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            # Asegurar que la sesión exista
            cur.execute("""
                INSERT INTO chat_sessions (id, title, active_doc, created_at, updated_at)
                VALUES (?, 'Nuevo Chat', ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET active_doc = CASE WHEN excluded.active_doc != '' THEN excluded.active_doc ELSE chat_sessions.active_doc END, updated_at = excluded.updated_at;
            """, (session_id, active_doc, now_str, now_str))

            # Insertar mensaje
            cur.execute("""
                INSERT INTO chat_messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?);
            """, (session_id, role, content, now_str))

            # Auto actualizar título si era 'Nuevo Chat' y el mensaje es del usuario
            if auto_title and role == "user":
                t_snippet = content.strip().replace("\n", " ")[:40]
                if t_snippet:
                    cur.execute("""
                        UPDATE chat_sessions
                        SET title = ?
                        WHERE id = ? AND (title = 'Nuevo Chat' OR title = '' OR title IS NULL);
                    """, (t_snippet, session_id))

            con.commit()
            con.close()

    def delete_chat_session(self, session_id: str):
        if self.mode == "postgres":
            import pg8000.native
            con = pg8000.native.Connection(
                user=settings.DB_USER, password=settings.DB_PASSWORD, host=settings.DB_HOST,
                port=settings.DB_PORT, database=settings.DB_NAME, timeout=5
            )
            con.run("DELETE FROM chat_messages WHERE session_id = :sid;", sid=session_id)
            con.run("DELETE FROM chat_sessions WHERE id = :sid;", sid=session_id)
            con.close()
        else:
            con = sqlite3.connect(SQLITE_PATH)
            cur = con.cursor()
            cur.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            cur.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            con.commit()
            con.close()

db = DatabaseClient()

