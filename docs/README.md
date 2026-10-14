# Documentación de Document Studio

Esta carpeta reúne la documentación técnica y académica del proyecto **Document Studio**, una aplicación para consultar, explorar y sintetizar documentos PDF mediante inteligencia artificial.

## Guía de lectura

| Documento | Contenido |
|---|---|
| [Visión general](VISION_GENERAL.md) | Qué es el proyecto, problema que aborda, objetivos, usuarios y características principales. Es el mejor punto de partida. |
| [Documentación técnica](DOCUMENTACION_TECNICA.md) | Arquitectura, módulos, flujo de datos, base de datos, motores de IA, configuración, ejecución y limitaciones observadas en el código. |
| [Documentación académica](DOCUMENTACION_ACADEMICA.md) | Descripción formal, planteamiento del problema, objetivos, metodología, alcance, beneficios y limitaciones. |
| [Guion de exposición](GUIA_EXPOSICION.md) | Estructura sugerida para presentar el proyecto, demostración, ideas clave y preguntas frecuentes. |

## Alcance y fuente

La implementación revisada está principalmente en `app.py`. `README.md` ofrece un resumen inicial, y `test.pdf` es un archivo de prueba del repositorio. Esta documentación describe el comportamiento observable del código y distingue las capacidades implementadas de las ideas o parámetros que aparecen en la interfaz pero no se aplican completamente.

> La aplicación procesa documentos potencialmente sensibles y puede enviar contenido a proveedores externos si se selecciona un motor en la nube. Revise las consideraciones de privacidad de la [documentación técnica](DOCUMENTACION_TECNICA.md#privacidad-y-seguridad).
