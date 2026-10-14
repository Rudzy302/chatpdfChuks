# Documentación técnica

## 1. Arquitectura

La aplicación sigue una arquitectura monolítica sencilla: la interfaz, lógica de procesamiento, acceso a datos e integración con modelos están implementados en `app.py`.

```text
Navegador
  └─ Streamlit (interfaz y estado de sesión)
      ├─ PyMuPDF ── texto, páginas e imágenes del PDF
      ├─ RapidOCR (opcional) ── texto en páginas renderizadas
      ├─ Ollama / Gemini Vision ── descripción de imágenes
      ├─ PostgreSQL + pgvector ── texto por página y embeddings
      ├─ Ollama / llama.cpp / Gemini / OpenAI-Groq ── respuestas y síntesis
      └─ PDF.js ── visor web embebido en el navegador
```

El procesamiento y la interfaz corren en el proceso de Streamlit. PostgreSQL es un servicio externo local; los proveedores en la nube son servicios externos opcionales.

## 2. Tecnologías y dependencias observadas

- Python y **Streamlit**: interfaz web reactiva y estado de sesión.
- **pg8000**: conexión PostgreSQL desde Python.
- **PostgreSQL** con extensión **pgvector**: almacenamiento y búsqueda vectorial.
- **PyMuPDF** (`pymupdf`): lectura de páginas, extracción de texto e imágenes y renderizado para OCR.
- **RapidOCR ONNX Runtime**: OCR opcional; su ausencia no impide iniciar la aplicación, aunque deshabilita esa extracción.
- **Pillow**: redimensionamiento y conversión de imágenes antes del análisis visual.
- **Ollama Python**: generación local de texto, embeddings y análisis visual con LLaVA.
- **PDF.js 3.11.174**: renderizado del visor en HTML/JavaScript, cargado desde CDN.
- `langchain_text_splitters` está importado, pero no participa en el flujo actual de indexación.

No hay archivo de dependencias ni manifiesto de despliegue en el repositorio revisado. Las dependencias mencionadas deben instalarse y validarse en el entorno de ejecución.

## 3. Módulos lógicos de `app.py`

### 3.1 Configuración, temas y estado (aprox. líneas 1–360)

- Configura la página de Streamlit y estilos CSS.
- Define cinco temas integrados y permite editar/guardar/eliminar temas personalizados en `custom_themes.json`.
- Mantiene en `st.session_state` la selección de documento, mensajes, página activa, términos resaltados, proveedor, parámetros RAG y visibilidad de paneles.
- Lee inicialmente la clave Gemini desde `GEMINI_API_KEY`; la clave y otros valores editados en la interfaz se mantienen en el estado de sesión, no en un almacén seguro persistente.

### 3.2 Persistencia y catálogo de documentos (aprox. líneas 361–444)

- `get_db()` conecta a `localhost:5433`, base `rag_db`, usuario `admin`.
- `setup_database_cached()` crea la extensión `vector` y la tabla `document_chunks` si no existen.
- `get_indexed_documents()` resume documentos indexados por nombre y cantidad de filas.
- `load_pdf_data()` carga el PDF desde `uploads/` y reconstruye texto desde la base de datos.
- `delete_document_from_db()` borra los fragmentos y el PDF local con ese nombre.

La conexión está codificada directamente en el código; los valores de usuario, contraseña, host, puerto y base de datos deben configurarse antes de usarla en otro entorno.

### 3.3 Extracción de PDF, OCR e imágenes (aprox. líneas 445–632)

`process_pdf()` realiza el procesamiento inicial:

1. Abre los bytes del archivo con PyMuPDF y rechaza documentos de más de 30 páginas.
2. Guarda el PDF original en `uploads/<nombre>`.
3. Por página, extrae texto digital y normaliza algunos saltos de línea y espacios.
4. Si la página tiene poco texto o está activado el análisis de imágenes, renderiza la página y, si RapidOCR está disponible, extrae texto OCR.
5. Si se activó el análisis de imágenes, obtiene imágenes embebidas (descarta las menores de 90×90 px) y analiza hasta dos por página. Para páginas escaneadas sin texto ni imágenes embebidas puede analizar una imagen de la página completa.
6. Combina texto digital, OCR y descripciones visuales. Clasifica el registro como `text`, `image` o `hybrid`.

Cada página produce **un registro**, conservando el número de página. Aunque `chunk_size` y `chunk_overlap` se pasan a la función, no se usan para dividir el contenido. La importación de `RecursiveCharacterTextSplitter` tampoco se utiliza.

El análisis visual intenta usar Gemini Vision cuando el proveedor seleccionado contiene “Gemini” y hay clave; en caso contrario intenta Ollama con `llava:7b`. Si no se puede analizar una imagen, produce una descripción genérica. OCR solo está disponible si RapidOCR se instaló correctamente.

### 3.4 Embeddings y acceso a motores de generación (aprox. líneas 635–761)

- `generate_embedding()` solicita a Ollama un embedding de `nomic-embed-text`, pensado para 768 dimensiones.
- Si Ollama falla, crea un vector determinista a partir del hash SHA-256 del texto, repetido hasta 768 valores. Esto evita interrumpir el flujo, pero **no es un embedding semántico** y la búsqueda por similitud puede perder utilidad.
- `call_llm()` realiza generación usando uno de cuatro proveedores:
  - Ollama local con el modelo configurable (por defecto `qwen2.5:7b`).
  - Servidor llama.cpp mediante endpoint compatible con `/v1/chat/completions`.
  - Google Gemini API con modelo seleccionable.
  - OpenAI; si la clave empieza con `gsk_`, cambia a Groq y un modelo Llama configurado en código.
- Todas las llamadas de red tienen timeout y errores se convierten en mensajes para la interfaz.

Los embeddings se intentan generar con Ollama en todos los casos: elegir un modelo de generación en nube no cambia el motor de embeddings.

### 3.5 Recuperación RAG (aprox. líneas 763–829)

1. Convierte la consulta en embedding.
2. Busca filas ordenadas por distancia coseno (`embedding <=> vector`) en pgvector.
3. Si se eligió un documento concreto, filtra por nombre; si se seleccionó “Todos los documentos”, busca entre todos.
4. Recupera el número configurable de resultados (`top_k_chunks`, por defecto 6).
5. Prepara contexto con referencias de página. Para algunas consultas detectadas por palabras clave como “resumen”, “proceso” o “conclusiones”, marca la consulta como global y añade el texto completo del documento activo (hasta 18.000 caracteres), además de los resultados recuperados.

La detección de consultas globales es una heurística por términos, no un clasificador semántico. Al consultar todos los documentos, el encabezado multi-documento se agrega, pero no se carga de forma completa el texto de cada PDF.

### 3.6 Chat, citas y resaltado (aprox. líneas 831–849 y 1391–1513)

- Saludos y agradecimientos predefinidos obtienen una respuesta rápida sin RAG.
- Las demás consultas recuperan contexto y llaman al modelo con instrucciones para responder con fidelidad y citar páginas.
- Un sanitizador transforma fracciones LaTeX básicas a texto plano.
- Se extraen referencias `[Pág. X]`, `[Página X]` e `[Imagen en Pág. X]` para crear botones de navegación.
- Los términos candidatos al resaltado se estiman a partir de la consulta, la respuesta y el contenido recuperado. Es un resaltado aproximado por coincidencias textuales; no representa una anotación persistente del PDF.

### 3.7 Visor PDF (aprox. líneas 850–1134 y 1516–1529)

`render_continuous_pdf_viewer_html()` genera una página HTML que:

- Inserta el PDF codificado en Base64 y lo renderiza con PDF.js.
- Renderiza todas las páginas en una secuencia vertical, con capa de texto transparente.
- Resalta spans de texto que coinciden parcialmente con las palabras candidatas.
- Hace scroll a la página objetivo o al primer término coincidente en ella.
- Ofrece zoom entre 70 % y 200 %.

El resaltado depende de que PDF.js pueda extraer texto de la página; texto que solo existe como imagen no se resaltará en esta capa.

### 3.8 Resumen, carga y presentación de paneles (aprox. líneas 1136–1600)

- La barra lateral permite seleccionar/eliminar documentos y subir un PDF.
- Al subirlo, se reemplazan los registros anteriores con el mismo nombre, se generan embeddings y se insertan registros en PostgreSQL.
- El panel Resumen envía al modelo los primeros 12.000 caracteres del texto reconstruido cuando se solicita. El resumen se conserva solo en el estado de sesión y se borra al volver a indexar el archivo.
- Chat, Documento y Resumen pueden mostrarse juntos o en vistas individuales.
- La conversación también reside en estado de sesión; no hay tabla de historial persistente.

## 4. Esquema de datos

Tabla creada automáticamente:

| Campo | Tipo | Uso |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | Identificador de fila. |
| `filename` | `TEXT` | Nombre del PDF y clave lógica para filtrar/borrar. |
| `page_number` | `INT` | Página de origen. |
| `chunk_index` | `INT` | Orden del registro dentro del documento (en el flujo actual, orden de página). |
| `chunk_type` | `TEXT` | `text`, `image` o `hybrid`. |
| `content` | `TEXT` | Texto digital, OCR y/o descripción visual combinados. |
| `embedding` | `vector(768)` | Vector utilizado para ordenar por similitud. |

Se crea un índice B-tree para `filename`. El código no crea explícitamente un índice vectorial HNSW/IVFFlat.

## 5. Archivos y datos generados

- `app.py`: aplicación y lógica.
- `uploads/`: PDFs cargados.
- `custom_themes.json`: temas personalizados, creado al guardar uno.
- `studio_config.json`: se declara una ruta, pero no se usa en el código observado.
- PostgreSQL: texto, tipo, página y vector de cada registro.

No existe actualmente una configuración independiente que externalice secretos ni un sistema de usuarios/autenticación visible en el código.

## 6. Ejecución y requisitos operativos

El repositorio no contiene `requirements.txt`, `pyproject.toml`, Dockerfile ni instrucciones completas de instalación. A nivel general, para ejecutar se requiere:

1. Un entorno Python con las dependencias usadas por `app.py` instaladas.
2. PostgreSQL accesible con pgvector habilitado y base/credenciales coincidentes con `get_db()`.
3. `streamlit run app.py` desde el directorio del proyecto.
4. Para IA local, Ollama activo con los modelos necesarios descargados (`nomic-embed-text`, modelo de chat elegido y, para visión, `llava:7b`); o un servidor llama.cpp activo.
5. Para proveedores en la nube, clave de API válida. La visualización PDF requiere acceso al CDN de PDF.js.

La lista anterior describe prerequisitos inferidos del código, no una receta de instalación probada para todos los sistemas.

## 7. Parámetros y limitaciones importantes

- Límite de procesamiento: 30 páginas por PDF.
- Análisis de imágenes: como máximo dos imágenes embebidas por página.
- OCR es opcional y silenciosamente puede no estar disponible si falta la dependencia o falla su inicialización.
- `chunk_size` y `chunk_overlap` aparecen como sliders pero no afectan a la indexación actual; el diseño implementado es un registro por página.
- La generación de embeddings sintéticos es una contingencia, no una alternativa semántica equivalente.
- El resumen considera un máximo de 12.000 caracteres del texto reconstruido.
- Consultas globales sobre un documento añaden como máximo 18.000 caracteres de texto completo.
- La búsqueda entre todos los documentos devuelve hasta `top_k_chunks` filas totales, no esa cantidad por archivo.
- La API de OpenAI/Groq usa modelo y endpoint definidos en código; no hay selector de modelo para esa opción.
- El modelo de visión de Gemini está fijado en el código de descripción de imágenes (`gemini-1.5-flash`), independiente del modelo de chat seleccionado.
- Los datos de chat y resumen no se guardan de forma persistente.
- Las excepciones de OCR/visión y algunos accesos a la base de datos se silencian, lo que puede hacer que una función falle sin diagnóstico detallado.

## 8. Privacidad y seguridad

- Los PDFs se guardan en `uploads/` y su contenido procesado en PostgreSQL. Borrar desde la interfaz elimina los registros y el archivo asociado por nombre.
- Con Gemini, OpenAI o Groq, el contexto recuperado (y para resúmenes, texto del documento) se transmite al proveedor correspondiente. El usuario debe evaluar si tiene autorización para procesar esos datos externamente.
- La clave API se introduce en la interfaz; no se almacena mediante un gestor de secretos. En una instalación real, se recomienda usar variables de entorno/secretos protegidos y evitar exponerlos en logs o capturas.
- Las credenciales de PostgreSQL están escritas en el código y son de ejemplo inseguro para un despliegue. Deben externalizarse y rotarse.
- El nombre original se usa como nombre del archivo en `uploads`; conviene validar nombres, restringir acceso y tratar colisiones antes de exponer el servicio.
- No se observa autenticación ni autorización por usuario. No debe publicarse como servicio multiusuario sin controles adicionales.
- Las citas generadas por un LLM no garantizan que la afirmación esté respaldada. Se debe confirmar la información en el documento original.

## 9. Mantenimiento sugerido

Como posibles mejoras (no funcionalidades ya implementadas): definir dependencias y configuración de despliegue; mover secretos a variables seguras; agregar autenticación y validación de archivos; añadir logs y pruebas; aplicar realmente segmentación configurable; usar embeddings reales también en fallos controlados; crear un índice vectorial adecuado; soportar documentos grandes con procesamiento incremental; y separar interfaz, extracción, recuperación y proveedores en módulos independientes.
