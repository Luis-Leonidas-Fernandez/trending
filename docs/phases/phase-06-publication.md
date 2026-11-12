# Fase 6 — Persistencia de Publicación y Simulación Auditada

## 1. Objetivo
Tomar el contenido textual y visual generado en la Fase 5, crear y persistir el registro del post en la base de datos relacional SQLite bajo estado `draft` (Subfase 6A), y proveer el mecanismo de simulación de publicación local auditada (Subfase 6B) que valida la integridad de la pieza, genera la bitácora técnica y marca definitivamente el tema como utilizado.

---

## 2. Responsabilidad
* **Subfase 6A (Persistencia y Preparación):**
  - Consumir el output de Fase 5 (`participante-5`, etapa `ai`).
  - Crear un nuevo registro en la tabla `generated_posts` con estado `draft`.
  - Construir la URL pública relativa de la imagen si vino en `data.image_file`.
  - Guardar el output versionado en [`output/participante-6/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-6).
  - No llamar a Instagram externo ni marcar `topic.used = 1`.
* **Subfase 6B (Simulación Local Auditada):**
  - Implementar [`simulate_publication(post_id)`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/instagram/instagram_service.py#L54).
  - Validar que el post exista y contenga obligatoriamente `caption` e `image_url`.
  - Insertar un registro en la tabla `publication_logs` con `status = "published_simulated"` y metadatos JSON aclarando `external_publication: False`, `provider: "local_audit"`.
  - Actualizar el estado del post a `published_simulated`.
  - **Actualizar `topic.used = 1`** en la tabla `trending_topics`.
  - Generar el output versionado auditado `instagram_v1_{id}_simulated.json`.

---

## 3. Entradas
* **Subfase 6A:** Ruta al archivo JSON de Fase 5 (`output/participante-5/ai_v1_{id}.json`).
* **Subfase 6B:** Identificador entero del post (`post_id`).

---

## 4. Procesamiento
1. **Subfase 6A:**
   - Deserializar y validar contra `ParticipantOutput`.
   - Extraer `caption`, `description`, `hashtags`, `image_file` y `topic_id`.
   - Si `image_file` existe, formatear la ruta pública (ej. `/assets/participante-5/ai_v1_...png`).
   - Invocar `post_repository.create_post(...)` con estado `draft`.
   - Escribir `output/participante-6/instagram_v1_{uuid-corto}.json`.
2. **Subfase 6B:**
   - Invocar `post_repository.get_post_by_id(post_id)`.
   - Comprobar que el post no esté vacío y tenga imagen y caption.
   - Insertar la fila de auditoría en `log_repository.create_log(...)`.
   - Actualizar el estado del post con `post_repository.update_post_status(post_id, "published_simulated")`.
   - Marcar el tema con `topic_repository.mark_topic_used(topic_id)`.
   - Escribir el output de simulación completada.

---

## 5. Salidas
* Archivo físico en `output/participante-6/instagram_v1_{uuid-corto}.json`.
* Registro creado en la tabla `generated_posts`.
* Registro creado en la tabla `publication_logs` (tras simular).
* Tema actualizado (`used = 1`) en la tabla `trending_topics` (tras simular).

---

## 6. Dependencias
* **Código Fuente:** [`python_backend/services/instagram/instagram_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/instagram/instagram_service.py).
* **Repositorios:** [`post_repository.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories/post_repository.py), [`log_repository.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories/log_repository.py), [`topic_repository.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories/topic_repository.py).

---

## 7. Contratos JSON
Ejemplo de `instagram_v1_14389ab4.json` (tras Subfase 6B):
```json
{
  "schema_version": "1.0",
  "run_id": "14389ab4-38fa-4a11-85bc-926f4901aa87",
  "participant": "participante-6",
  "stage": "instagram",
  "generated_at": "2026-07-28T14:10:20Z",
  "status": "success",
  "data": {
    "post_id": 5,
    "platform": "instagram",
    "simulated": true,
    "external_publication": false,
    "ready_to_publish": false,
    "post": {
      "id": 5,
      "topic_id": 14,
      "caption": "Texto del caption...",
      "image_url": "/assets/participante-5/ai_v1_68d67253.png",
      "status": "published_simulated"
    },
    "publication_log": {
      "id": 8,
      "post_id": 5,
      "platform": "instagram",
      "status": "published_simulated"
    },
    "topic": {
      "id": 14,
      "used": 1
    }
  },
  "errors": []
}
```

---

## 8. Persistencia
* **SQLite:** Modifica y crea filas en tres tablas (`generated_posts`, `publication_logs`, `trending_topics`).

---

## 9. Manejo de Errores y Fallbacks
* Si el input de Fase 5 viene en estado `draft` o con errores, el post se persiste pero el output de Fase 6 se marca como `status = "draft"`, propagando los mensajes.
* Si el post no tiene imagen o caption, `simulate_publication` arroja un `InstagramServiceError` que es devuelto por el router como `HTTP 400 Bad Request`.
* Si falla la persistencia en base de datos, se genera un archivo de output con `status = "error"` y detalle en `errors`.

---

## 10. Pruebas Relacionadas
* [`tests/test_instagram_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_instagram_service.py):
  - `test_process_ai_output_persists_post_and_generates_success_output`
  - `test_process_ai_output_draft_input_stays_draft_and_propagates_errors`
  - `test_process_ai_output_requires_caption`
  - `test_simulate_publication_creates_log_updates_post_and_marks_topic`
  - `test_simulate_publication_requires_image`
  - `test_process_simulated_publication_generates_valid_output`

---

## 11. ADRs Asociados
* [ADR-0003: Persistencia relacional con SQLite y SQLAlchemy ORM](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0003-sqlite-sqlalchemy.md)
* [ADR-0005: Comunicación inter-fase basada en outputs JSON versionados](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md)
* [ADR-0009: Selección determinística pura de tema postergando la mutación de estado](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0009-pure-topic-selection.md)
* [ADR-0012: Publicación en dos tiempos: persistencia como `draft` y simulación auditada](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0012-two-step-publication.md)

---

## 12. Limitaciones Conocidas
* No existe integración real con la API de Instagram Graph en producción (no publica remotamente).
* La publicación simulada asume que las credenciales locales de auditoría siempre son válidas.
