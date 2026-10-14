# Document Studio: visión general

## ¿Qué es?

**Document Studio** es una aplicación web local construida con Python y Streamlit para cargar documentos PDF, extraer su contenido y realizar consultas conversacionales sobre ellos. Combina texto digital, OCR y descripciones de imágenes, y usa recuperación de información (RAG) para proporcionar contexto a un modelo de lenguaje.

Su propósito es facilitar la lectura y exploración de PDFs: en lugar de buscar manualmente una respuesta, la persona usuaria pregunta en lenguaje natural, recibe una respuesta con referencias de página y puede saltar a la ubicación correspondiente en un visor integrado.

## Problema que aborda

Leer documentos extensos, escaneados o con contenido visual requiere localizar información entre páginas y alternar entre herramientas. Document Studio integra en una sola interfaz la extracción, búsqueda contextual, conversación, síntesis y consulta visual del PDF.

## Características clave

1. **Preguntas y respuestas sobre documentos:** recupera fragmentos relevantes y genera una respuesta usando el proveedor de IA seleccionado.
2. **Referencias a páginas:** solicita al modelo citas del tipo `[Pág. X]` y crea botones para navegar a esas páginas.
3. **Comprensión de contenido mixto:** procesa texto digital, texto OCR y descripciones de ilustraciones o imágenes.
4. **Visor PDF integrado:** muestra las páginas en una vista continua, permite acercar o alejar y resalta términos asociados con la respuesta.
5. **Síntesis bajo demanda:** crea una síntesis estructurada a partir del contenido textual indexado.
6. **Selección de varios documentos:** permite consultar un PDF específico o recuperar fragmentos de todos los documentos indexados.
7. **Motores locales o en la nube:** admite Ollama, un servidor compatible con llama.cpp, Gemini y APIs compatibles con OpenAI/Groq.
8. **Interfaz personalizable:** ofrece temas predefinidos y paletas personalizadas que se pueden guardar.

## ¿Cómo se usa?

1. Se inicia la aplicación y se selecciona o configura la conexión a PostgreSQL y al motor de IA.
2. Se carga un PDF (límite actual: 30 páginas) y se inicia su procesamiento.
3. La aplicación extrae texto y, según la configuración, ejecuta OCR y análisis visual; después guarda el contenido por página y sus vectores en PostgreSQL.
4. Se selecciona el documento y se escribe una pregunta en el chat.
5. El sistema busca páginas relevantes, envía el contexto al modelo y presenta una respuesta con citas.
6. Los controles de la interfaz abren el visor en la página citada; opcionalmente se puede pedir una síntesis.

## Componentes visibles

- **Chat:** preguntas, respuestas y enlaces de salto a páginas citadas.
- **Documento:** visor continuo del PDF original con zoom y resaltado aproximado de palabras.
- **Resumen:** panel donde se solicita una síntesis textual del documento.
- **Barra lateral:** selector y eliminación de documentos, carga/procesamiento, ajuste de apariencia y limpieza de conversación.
- **Parámetros de modelo:** selector de proveedor/modelo y controles de recuperación RAG.

Las vistas Chat, Documento y Resumen se pueden mostrar u ocultar, en columnas o individualmente.

## Alcance

Document Studio es una herramienta de consulta y apoyo a la lectura, no un sistema de verificación factual ni un sustituto de la revisión del PDF original. Las respuestas dependen de la calidad de extracción, OCR, recuperación y generación. Se recomienda validar las citas y los datos importantes directamente en la fuente.
