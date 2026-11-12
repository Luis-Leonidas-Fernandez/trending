# Fase 7 — Medición, Auditoría de Calidad y Dashboard Web

## 1. Objetivo
Cerrar el ciclo de vida del pipeline mediante una auditoría técnica local automatizada que verifique la integridad y completitud de la publicación generada, calculando un puntaje objetivo de calidad (`score`), y proveer la interfaz web interactiva (dashboard) para la operación visual, supervisión y consulta histórica del sistema.

---

## 2. Responsabilidad
* **Auditoría y Métricas ([`metrics_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/metrics/metrics_service.py)):**
  - Consumir el output de Fase 6 (`participante-6`, etapa `instagram`).
  - Auditar contra SQLite la presencia del post, caption, imagen, bitácora de publicación y marcado de tema usado.
  - Calcular el puntaje porcentual de calidad (0 a 100%).
  - Emitir el entregable versionado en [`output/participante-7/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-7).
* **Dashboard y Experiencia de Usuario ([`frontend/`](file:///Users/luis/desktop/PROYECTOS/trending/frontend)):**
  - Visualizar el estado de cada una de las 6 fases del pipeline.
  - Permitir la ejecución por lotes ("Ejecutar todo") o paso a paso ("Correr selección").
  - Ofrecer controles de cancelación inmediata (`/pipeline/cancel`) y reseteo (`DELETE /pipeline/state`).
  - Previsualizar en un modal interactivo el post generado (imagen, titular, caption con saltos de párrafo, hashtags y puntaje).
  - Proveer la vista de historial (`frontend/history.html`) con filtros de fechas y botón para **reutilizar temas históricos** en un nuevo ciclo.

---

## 3. Entradas
* Archivo JSON de salida de Fase 6 (`output/participante-6/instagram_v1_{id}.json`).
* Estado relacional en SQLite de las tablas `generated_posts`, `trending_topics` y `publication_logs`.
* Para el frontend: Interacción del usuario vía clicks y peticiones HTTP fetch a la API FastAPI.

---

## 4. Procesamiento
1. **Auditoría de Métricas:**
   - Deserializar el output de Fase 6 y extraer `post.id`.
   - Consultar el post en SQLite con `post_repository.get_post_by_id(post_id)`.
   - Consultar el tema asociado con `topic_repository.get_topic_by_id(topic_id)`.
   - Consultar logs con `log_repository.get_logs_by_post_id(post_id)`.
   - Comprobar las 6 condiciones de calidad: `has_post`, `has_caption`, `has_image`, `has_publication_log`, `topic_marked_used`, `is_published_simulated`.
   - Calcular `score = (passed_checks / total_checks) * 100`.
   - Si `score == 100`, marcar output con `status = "success"`; en caso contrario, marcar como `"draft"` con advertencias explicativas.
   - Escribir `output/participante-7/metrics_v1_{uuid-corto}.json`.
2. **Dashboard Web:**
   - Realiza polling ligero a `/api/pipeline/state` para actualizar las tarjetas y animaciones.
   - Al finalizar, consulta `/api/posts/audit/latest` y `/api/pipeline/metrics/latest` para poblar el modal de entrega.

---

## 5. Salidas
* Archivo físico JSON: `output/participante-7/metrics_v1_{uuid-corto}.json`.
* Actualización de `quality_score` en la tabla `pipeline_runs` de SQLite.
* Interfaz visual renderizada en el navegador en `http://127.0.0.1:5173`.

---

## 6. Dependencias
* **Código Fuente:** [`python_backend/services/metrics/metrics_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/metrics/metrics_service.py).
* **Frontend:** [`frontend/index.html`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/index.html), [`frontend/history.html`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/history.html), [`frontend/history.js`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/history.js).
* **Repositorios:** `post_repository`, `topic_repository`, `log_repository`.

---

## 7. Contratos JSON
Ejemplo de `metrics_v1_19341e47.json`:
```json
{
  "schema_version": "1.0",
  "run_id": "19341e47-2bf4-498d-a48e-7e9b04fbb1c2",
  "participant": "participante-7",
  "stage": "metrics",
  "generated_at": "2026-07-28T14:10:25Z",
  "status": "success",
  "data": {
    "score": 100.0,
    "total_checks": 6,
    "passed_checks": 6,
    "failed_checks": 0,
    "checks": {
      "has_post": true,
      "has_caption": true,
      "has_image": true,
      "has_publication_log": true,
      "topic_marked_used": true,
      "is_published_simulated": true
    },
    "warnings": []
  },
  "errors": []
}
```

---

## 8. Persistencia
* No inserta nuevas tablas; actualiza la columna `quality_score` en la tabla `pipeline_runs`.
* Escribe el archivo JSON en `output/participante-7/`.

---

## 9. Manejo de Errores y Fallbacks
* Si el post no existe en base de datos, `process_instagram_output` genera un output con `status = "error"`.
* Si alguna de las comprobaciones de calidad no se cumple (ej. falta imagen o el topic no se marcó como usado), la corrida no se rompe: el score disminuye proporcionalmente y el estado se reporta como `draft`.

---

## 10. Pruebas Relacionadas
* [`tests/test_metrics_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_metrics_service.py):
  - `test_process_instagram_output_scores_success_when_local_audit_is_complete`
  - `test_process_instagram_output_returns_draft_when_checks_are_missing`
* [`tests/test_pipeline_history_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_pipeline_history_service.py):
  - `test_history_persists_multiple_correlated_runs_and_upserts`

---

## 11. ADRs Asociados
* [ADR-0005: Comunicación inter-fase basada en outputs JSON versionados](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md)
* [ADR-0013: Medición y scoring de calidad local en lugar de métricas remotas](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0013-local-audit-metrics.md)
* [ADR-0014: Persistencia dual de estado: `pipeline_state.json` y tabla relacional `pipeline_runs`](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0014-dual-pipeline-state.md)
* [ADR-0016: Adopción de Frontend Vanilla Web](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0016-vanilla-web-frontend.md)

---

## 12. Limitaciones Conocidas
* Las métricas son técnicas e internas del pipeline; no miden alcance ni viralidad real en Instagram.
* El frontend no cuenta con sistema de autenticación de operadores.
