import os
import json
import math
import sqlite3
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

db = DatabaseClient()
