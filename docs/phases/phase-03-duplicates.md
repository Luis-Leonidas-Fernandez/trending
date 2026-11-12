# Fase 3 — Filtrado de Duplicados y Persistencia

## 1. Objetivo
Consumir el lote de tendencias descubierto en la Fase 2, descartar elementos con títulos inválidos o repetidos mediante comparación exacta sobre `normalized_title`, persistir atómicamente en SQLite los temas verdaderamente nuevos y generar un output versionado auditable para la Fase 4 que consolide tanto temas nuevos como temas existentes no utilizados.

---

## 2. Responsabilidad
* Validar que el archivo de entrada pertenezca a `participante-2` y etapa `trends`.
* Comparar cada tema contra los temas del mismo lote (deduplicación interna).
* Comparar cada tema contra la tabla `trending_topics` en SQLite (deduplicación en base de datos).
* Descartar temas ya usados (`used == 1`).
* Recuperar temas ya existentes pero no usados (`used == 0`) para reciclarlos como candidatos.
* Persistir en SQLite únicamente los temas nuevos.
* Generar el archivo JSON de salida en [`output/participante-3/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-3).

---

## 3. Entradas
* Ruta al archivo de salida de Fase 2 (`output/participante-2/trends_v1_{id}.json`).
* Estado actual de la tabla `trending_topics` en SQLite (consultado vía [`topic_repository.get_all_topics()`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories/topic_repository.py)).

---

## 4. Procesamiento
1. **Carga y Validación:** Leer el JSON con [`_load_phase_2_output`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/duplicates/duplicates_service.py) y verificar que cumple el contrato `ParticipantOutput`.
2. **Filtrado en Memoria:**
   - Para cada elemento de `data.items`, re-aplicar `normalize_title()`. Si está vacío, registrar descarte `invalid_title`.
   - Si el `normalized_title` ya apareció en este mismo lote, registrar descarte `duplicate_in_input`.
   - Si ya existe en la base de datos:
     - Si `used == 1`: registrar descarte `already_used_in_database`.
     - Si `used == 0`: añadir a `reusable_items` (no se inserta de nuevo).
   - Si no existe en la base de datos: añadir a `new_items`.
3. **Persistencia Atómica:** Para cada tema en `new_items`, invocar `topic_repository.create_topic(...)`. SQLite le asigna un ID autoincremental positivo.
4. **Construcción de Candidatos:** Unificar `candidate_items = [*saved_items, *reusable_items]`, preservando el orden original relativo.
5. **Generación de Salida:** Escribir `output/participante-3/duplicates_v1_{id}.json` con métricas de filtrado: `input_count`, `saved_count`, `reused_count`, `duplicate_count`, `invalid_count` y detalle de descartes.

---

## 5. Salidas
* Archivo físico en `output/participante-3/duplicates_v1_{uuid-corto}.json`.
* Nuevos registros insertados en la tabla `trending_topics` de SQLite con `used = 0`.

---

## 6. Dependencias
* **Código Fuente:** [`python_backend/services/duplicates/duplicates_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/duplicates/duplicates_service.py).
* **Capa de Persistencia:** [`python_backend/repositories/topic_repository.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories/topic_repository.py).
* **Schemas:** [`ParticipantOutput`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/schemas/output_schema.py).

---

## 7. Contratos JSON
Ejemplo de `duplicates_v1_7c57590b.json`:
```json
{
  "schema_version": "1.0",
  "run_id": "7c57590b-8d32-4211-a8cf-4b7119e8c312",
  "participant": "participante-3",
  "stage": "duplicates",
  "generated_at": "2026-07-28T14:10:05Z",
  "status": "success",
  "data": {
    "input_count": 10,
    "saved_count": 7,
    "reused_count": 1,
    "duplicate_count": 2,
    "invalid_count": 0,
    "items": [
      {
        "id": 14,
        "title": "Dólar hoy",
        "normalized_title": "dolar hoy",
        "source": "google_trends",
        "score": 100.0,
        "used": 0,
        "created_at": "2026-07-28 14:10:05"
      }
    ],
    "discarded": [
      {
        "title": "Dolar Hoy",
        "normalized_title": "dolar hoy",
        "reason": "duplicate_in_input"
      }
    ]
  },
  "errors": []
}
```

---

## 8. Persistencia
* **Escritura en SQLite:** Inserta temas en `trending_topics` con `used = 0`.
* **No altera filas existentes:** No sobreescribe ni modifica temas ya registrados.

---

## 9. Manejo de Errores y Fallbacks
* Si el input de Fase 2 vino con `status = "draft"` o `used_fallback = true`, la Fase 3 propaga dicho estado (`status = "draft"`).
* Si no hay ningún tema candidato elegible (todos eran duplicados usados), el output se marca como `"draft"` con advertencia explicativa.
* Si ocurre una excepción de I/O o base de datos, se atrapa de forma controlada y se genera un output con `status = "error"` y detalle en `errors`.

---

## 10. Pruebas Relacionadas
* [`tests/test_duplicates_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_duplicates_service.py):
  - `test_filter_new_topics_normalizes_case_accents_punctuation_and_spaces`
  - `test_filter_new_topics_discards_duplicates_in_same_input_and_preserves_order`
  - `test_process_trends_output_persists_only_new_topics_with_mocked_repository`
  - `test_process_trends_output_discards_existing_used_topics`
  - `test_process_trends_output_reuses_existing_unused_topics_as_candidates`
  - `test_process_trends_output_integration_with_temporary_sqlite`
  - `test_process_trends_output_rejects_non_phase_2_input`

---

## 11. ADRs Asociados
* [ADR-0003: Persistencia relacional con SQLite y SQLAlchemy ORM](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0003-sqlite-sqlalchemy.md)
* [ADR-0005: Comunicación inter-fase basada en outputs JSON versionados](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md)
* [ADR-0008: Deduplicación por `normalized_title` y persistencia atómica en SQLite](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0008-duplicate-detection-idempotency.md)

---

## 12. Limitaciones Conocidas
* La deduplicación se basa en igualdad ortográfica exacta de cadenas normalizadas. Variaciones semánticas complejas (sinónimos o construcciones oracionales distintas) no son detectadas como duplicados.
