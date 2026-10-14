# Documentación académica

## Título

**Document Studio: sistema de consulta y análisis asistido de documentos PDF mediante recuperación aumentada y modelos de inteligencia artificial.**

## Resumen

Document Studio es una aplicación web que integra procesamiento de documentos PDF, recuperación de información y modelos de lenguaje para apoyar la consulta documental. Extrae texto digital, puede aplicar reconocimiento óptico de caracteres a páginas renderizadas y genera descripciones de imágenes cuando se habilita el análisis visual. Organiza el contenido por página, lo almacena junto con representaciones vectoriales en PostgreSQL con pgvector y recupera fragmentos relacionados con preguntas en lenguaje natural. Un modelo genera respuestas contextualizadas, con referencias de página que se conectan con un visor PDF interactivo. La aplicación también ofrece síntesis bajo demanda y selección de motores locales o en la nube. Su finalidad es mejorar la accesibilidad y eficiencia de la exploración documental; sus resultados deben verificarse con la fuente original.

**Palabras clave:** procesamiento de documentos, PDF, RAG, búsqueda semántica, OCR, modelos de lenguaje, pgvector.

## Planteamiento del problema

La información de interés suele estar distribuida entre distintas páginas y puede presentarse como texto digital, imagen escaneada, tabla o ilustración. La búsqueda manual demanda tiempo y obliga a alternar entre lectura, localización y síntesis. Un sistema de consulta que combine recuperación contextual, referencias a la fuente y navegación integrada puede reducir ese esfuerzo y facilitar la revisión.

## Justificación

La propuesta reúne tecnologías de extracción documental, bases de datos vectoriales e inteligencia artificial generativa en una herramienta de uso interactivo. La asociación de respuestas con páginas tiene valor práctico porque facilita contrastar la generación con el documento original. La posibilidad de seleccionar motores locales o remotos también permite adaptar la ejecución a los recursos disponibles, aunque las opciones remotas implican consideraciones de privacidad.

## Objetivo general

Desarrollar una aplicación que permita consultar documentos PDF en lenguaje natural, recuperar contenido pertinente y presentar respuestas vinculadas a páginas del documento fuente.

## Objetivos específicos

1. Extraer y organizar texto digital de documentos PDF por página.
2. Incorporar OCR opcional y análisis visual para ampliar la cobertura de documentos escaneados o con imágenes.
3. Representar el contenido mediante vectores y almacenarlo para recuperar fragmentos similares a una consulta.
4. Integrar varios motores de generación de lenguaje para responder preguntas y elaborar síntesis.
5. Facilitar la verificación mediante citas de página, navegación directa y resaltado visual aproximado.
6. Proporcionar una interfaz que permita gestionar documentos, parámetros de consulta y apariencia.

## Metodología de funcionamiento

El sistema sigue un flujo de procesamiento en dos etapas:

### A. Preparación e indexación

1. **Entrada:** el usuario carga un archivo PDF.
2. **Extracción:** PyMuPDF obtiene el texto digital, las imágenes y la representación de las páginas.
3. **Enriquecimiento:** RapidOCR puede transcribir contenido visual; un modelo de visión puede describir imágenes.
4. **Integración:** el contenido extraído se reúne en un registro por página.
5. **Vectorización:** Ollama intenta producir un embedding de 768 dimensiones para cada registro.
6. **Persistencia:** se guardan nombre, página, tipo de contenido, texto y vector en PostgreSQL/pgvector; el PDF se mantiene en `uploads/`.

### B. Consulta y respuesta

1. El usuario formula una pregunta.
2. La consulta se convierte en embedding y se buscan registros próximos por distancia coseno.
3. Los registros recuperados se organizan como contexto, conservando referencias a páginas.
4. El proveedor de lenguaje seleccionado genera una respuesta a partir de la consulta y del contexto.
5. La interfaz presenta la respuesta, extrae las citas, habilita navegación a las páginas y resalta términos aproximados.

En preguntas reconocidas heurísticamente como globales, el sistema puede incluir una porción mayor del texto del documento activo. La síntesis se solicita de forma independiente y utiliza hasta 12.000 caracteres del texto reconstruido.

## Conceptos técnicos

- **OCR:** reconocimiento óptico de caracteres; convierte texto presente en imágenes en una representación textual procesable.
- **Embedding:** vector numérico que representa un texto para comparar similitud semántica.
- **RAG (Retrieval-Augmented Generation):** enfoque que recupera información de una fuente antes de generar una respuesta, aportando contexto externo al modelo.
- **pgvector:** extensión de PostgreSQL que almacena vectores y permite ordenarlos por distancia.
- **LLM:** modelo de lenguaje extenso usado para producir respuestas o síntesis.
- **Modelo de visión:** modelo capaz de interpretar imágenes, describir elementos o transcribir contenido visual.

## Alcance funcional

La versión actual procesa PDFs de hasta 30 páginas, indexa un registro por página, permite seleccionar un documento o todos los indexados, y proporciona chat, visor, resumen y temas personalizables. La disponibilidad de OCR depende de RapidOCR; la descripción visual depende de un motor accesible. Los modelos pueden ejecutarse localmente o mediante APIs externas.

## Aportes y beneficios esperados

- Reduce el tiempo necesario para localizar pasajes relevantes.
- Facilita consultas en lenguaje natural sin requerir conocimiento de SQL o herramientas de búsqueda.
- Mantiene trazabilidad básica al asociar contexto y respuesta con números de página.
- Aúna texto y descripciones visuales en una experiencia única.
- Permite contrastar la respuesta con el PDF original desde la misma interfaz.
- Ofrece flexibilidad de inferencia entre entornos locales y servicios en la nube.

## Limitaciones y validez

El desempeño está condicionado por calidad del PDF, extracción de texto, OCR, embeddings y recuperación. Las descripciones visuales y respuestas son generadas por modelos y pueden omitir o inventar detalles. La cita de página es una instrucción al modelo más una navegación basada en el número extraído; no constituye una prueba formal de que cada afirmación esté sustentada. Si Ollama no produce embeddings, se utiliza un vector de hash que no conserva similitud semántica. Además, aunque la interfaz expone parámetros de tamaño y solapamiento, la indexación implementada conserva un registro por página y no aplica esos parámetros. Por ello, el sistema debe considerarse una herramienta de apoyo, no de decisión autónoma.

## Conclusión

Document Studio demuestra una integración práctica de interfaz web, extracción multimodal, recuperación vectorial y generación de lenguaje para explorar documentos. Su rasgo diferenciador es conectar la consulta conversacional con la navegación hacia la fuente. El uso académico o profesional de sus resultados requiere validar la información directamente en el PDF y considerar las limitaciones de privacidad y de los modelos.

## Trabajo futuro

Entre las líneas de mejora se encuentran: evaluación sistemática de precisión de recuperación y fidelidad de respuestas; pruebas con corpus diversos; segmentación configurable; citas verificables por fragmento; extracción estructurada de tablas; procesamiento de documentos de mayor tamaño; control de acceso; y medición de latencia y consumo de recursos.
