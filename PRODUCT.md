# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Estudiantes, docentes, investigadores y profesionales que consultan y verifican información en documentos PDF.

## Product Purpose

Document Studio permite consultar, explorar y sintetizar PDFs. El usuario pregunta sobre un documento y puede seguir las referencias de página en el visor integrado.

## Positioning

Combina en una misma interfaz conversación documental, referencias navegables, visor PDF, extracción OCR y análisis visual opcional.

## Operating Context

La app se ejecuta localmente como interfaz Streamlit. Los usuarios cargan PDFs, seleccionan documentos, consultan contenido, revisan las páginas citadas y pueden generar síntesis.

## Capabilities and Constraints

- Mantener operativos el chat, la carga y selección de PDFs, las citas, el visor, las síntesis, los proveedores existentes y la personalización de temas.
- En esta iteración, los cambios se limitan a presentación, navegación visual y notificaciones de interfaz; no cambiar backend ni comportamiento de las funciones.
- La referencia visual mencionada por el usuario es ChatPDF y NotebookLM, como inspiración de producto, no como diseños para copiar.
- Sidebar solicitado: módulos independientes de Biblioteca, Añadir PDF, Apariencia y Sesión; navegar módulos no debe cambiar la vista central/derecha.
- Preferir notificaciones nativas `st.toast` para evitar una nueva dependencia JavaScript.

## Brand Commitments

Conservar el nombre Document Studio. Mantener una identidad original inspirada en herramientas de lectura documental, sin replicar ChatPDF ni NotebookLM.

## Evidence on Hand

- `docs/DOCUMENTACION_TECNICA.md`: arquitectura, comportamiento, proveedores y limitaciones.
- `docs/VISION_GENERAL.md`: propósito, objetivos, usuarios y características.
- `app.py`: implementación vigente de interfaz, chat, visor, resumen, temas y carga.

## Product Principles

- Mantener las fuentes y sus citas cerca de la conversación.
- Dar confirmación visible y discreta a las acciones.
- Permitir explorar controles sin perder el contexto del documento.
- Preservar las funciones existentes al mejorar la interfaz.
