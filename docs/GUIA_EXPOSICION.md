# Guía para exponer Document Studio

## Mensaje principal

> Document Studio permite conversar con documentos PDF y seguir las respuestas hasta la página de origen, combinando extracción de texto, OCR/análisis visual, búsqueda vectorial y modelos de lenguaje.

## Guion sugerido (5–7 minutos)

### 1. Introducción (30–45 s)

“Cuando un documento es largo o está escaneado, encontrar un dato y comprobar dónde aparece puede tomar mucho tiempo. Document Studio reúne la consulta conversacional, la síntesis y el visor del PDF en una sola aplicación.”

### 2. Problema y objetivo (45 s)

- **Problema:** localizar y comprender información dispersa entre páginas y formatos.
- **Objetivo:** permitir preguntas en lenguaje natural y devolver respuestas contextualizadas con referencias de página.
- **Usuarios potenciales:** estudiantes, docentes, investigadores o profesionales que revisan documentos, siempre verificando la respuesta en la fuente.

### 3. ¿Cómo funciona? (1–2 min)

Explicar el flujo con una diapositiva:

```text
PDF → extracción de texto/OCR/visión → contenido por página
    → embeddings en PostgreSQL/pgvector
Pregunta → recuperación de páginas relevantes → modelo de lenguaje
         → respuesta con cita → visor en la página correspondiente
```

Definir brevemente RAG: primero se busca información del documento y luego se entrega ese contexto al modelo para generar la respuesta.

### 4. Demostración (2–3 min)

1. Mostrar la barra lateral y cargar un PDF de prueba de hasta 30 páginas.
2. Iniciar el procesamiento; mencionar extracción, indexación y almacenamiento.
3. Preguntar algo concreto cuya respuesta esté claramente en una página.
4. Mostrar la cita y pulsar el botón “Pág.” para saltar al PDF.
5. Enseñar el resaltado y el zoom del visor.
6. Mostrar el panel Resumen y cómo se genera bajo demanda.
7. Si hay tiempo, mostrar selección de motor local/nube o temas.

**Preparación:** comprobar antes de exponer PostgreSQL/pgvector, Streamlit y el proveedor elegido; usar un PDF con texto legible y una respuesta fácil de comprobar. El OCR requiere RapidOCR instalado. El análisis visual puede tardar más.

### 5. Características clave (45 s)

- Consulta conversacional con recuperación RAG.
- Citas y navegación integrada por página.
- OCR opcional y descripción de imágenes.
- Chat, visor y síntesis en paneles combinables.
- Motores locales o nube y temas personalizables.

### 6. Cierre y límites (30–45 s)

“La aplicación acelera la exploración, pero no sustituye la revisión. La precisión depende del PDF, el OCR, la recuperación y el modelo. En esta versión la indexación es de un fragmento por página; y si falla Ollama para embeddings, el vector alternativo no es semántico. El trabajo futuro puede incluir mejores pruebas, configuración segura y segmentación configurable.”

## Preguntas frecuentes

### ¿Qué significa RAG?

Retrieval-Augmented Generation: el sistema recupera contenido relacionado desde documentos y lo proporciona como contexto a un modelo antes de generar su respuesta.

### ¿Cómo puede citar páginas?

Los registros guardan el número de página; la recuperación incluye ese número en el contexto y el modelo recibe instrucciones para citarlo. La aplicación convierte las citas reconocidas en controles de navegación. Deben verificarse en el PDF.

### ¿Qué pasa con un PDF escaneado?

Se renderiza la página y se intenta extraer texto mediante RapidOCR. La disponibilidad depende de que esa dependencia esté instalada y funcione. El modelo de visión puede complementar con una descripción, pero no reemplaza una transcripción perfecta.

### ¿Los datos salen del equipo?

Con motores locales, la inferencia se realiza contra los servicios locales configurados. Si se selecciona Gemini, OpenAI o Groq, el contexto enviado para generar puede salir al proveedor externo. El PDF y su texto también se guardan localmente en `uploads/` y PostgreSQL. La configuración real debe revisarse antes de procesar material sensible.

### ¿El tamaño de chunk se puede cambiar?

La interfaz muestra controles de tamaño y solapamiento, pero el código actual indexa un registro por página y no aplica esos valores. Es una limitación conocida, no debe presentarse como segmentación configurable efectiva.

### ¿El modelo siempre responde correctamente?

No. Puede equivocarse, omitir contexto o generar una cita incorrecta. La página citada ayuda a verificar, pero la persona usuaria debe contrastar la afirmación con el original.

## Estructura sugerida de diapositivas

1. Título y propósito.
2. Problema y usuarios.
3. Objetivos y características principales.
4. Arquitectura/flujo RAG.
5. Demostración de consulta y cita.
6. Tecnologías utilizadas.
7. Limitaciones, privacidad y trabajo futuro.
