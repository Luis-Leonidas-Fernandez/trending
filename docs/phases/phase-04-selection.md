# Fase 4 — Selección Determinística de Tema

## 1. Objetivo
Recibir la lista de temas candidatos filtrados por la Fase 3, evaluar su estructura y seleccionar determinísticamente el primer tema válido que no haya sido utilizado, preservando el estado de la base de datos sin modificaciones para proteger la reutilización del tema en caso de fallos en fases posteriores.

---

## 2. Responsabilidad
* Validar que el archivo de entrada pertenezca a `participante-3` y etapa `duplicates`.
* Validar la integridad estructural de cada tema candidato (`id` entero positivo, `title` y `normalized_title` no vacíos).
* Aplicar la estrategia determinística `STRATEGY = "first_valid_unused"`.
* Seleccionar el primer tema con `used in (0, False)`.
* Generar el output versionado en [`output/participante-4/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-4).
* Proveer la funcionalidad de selección manual de temas históricos ([`create_reuse_topic_output`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/topic_selector/topic_selector_service.py#L96)) bajo la estrategia `manual_history_reuse`.

---

## 3. Entradas
* Ruta al archivo JSON de salida de Fase 3 (`output/participante-3/duplicates_v1_{id}.json`).
* En modo reutilización: Diccionario representativo de un tema de la tabla `trending_topics`.

---

## 4. Procesamiento
1. **Carga y Verificación:** Deserializar y validar contra `ParticipantOutput`.
2. **Evaluación de Elegibilidad:**
   - Se itera `data.items` preservando el orden original de Google Trends.
   - Si un elemento no es diccionario o carece de campos obligatorios, se descarta con `reason = "invalid_topic"`.
   - Si tiene `used not in (0, False)`, se descarta con `reason = "already_used"`.
3. **Selección Pura:** El primer elemento elegible se asigna como `selected_topic`.
4. **Protección de Estado en Base de Datos:** **La Fase 4 no ejecuta queries SQL ni marca `used = 1`**. El tema permanece intacto en SQLite.
5. **Generación de Output:** Escribir `output/participante-4/topic_selector_v1_{uuid-corto}.json`.

---

## 5. Salidas
* Archivo físico en `output/participante-4/topic_selector_v1_{uuid-corto}.json` con el objeto `data.selected_topic`.
* En caso de reutilización manual: `topic_selector_v1_{id}_reuse.json` con `strategy = "manual_history_reuse"`.

---

## 6. Dependencias
* **Código Fuente:** [`python_backend/services/topic_selector/topic_selector_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/topic_selector/topic_selector_service.py).
* **Schemas:** [`ParticipantOutput`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/schemas/output_schema.py).

---

## 7. Contratos JSON
Ejemplo de `topic_selector_v1_fcb7e995.json`:
```json
{
  "schema_version": "1.0",
  "run_id": "fcb7e995-156c-4861-bb2e-503a56658055",
  "participant": "participante-4",
  "stage": "topic_selector",
  "generated_at": "2026-07-28T14:10:08Z",
  "status": "success",
  "data": {
    "strategy": "first_valid_unused",
    "selected_topic": {
      "id": 14,
      "title": "Dólar hoy",
      "normalized_title": "dolar hoy",
      "source": "google_trends",
      "score": 100.0,
      "used": 0,
      "created_at": "2026-07-28 14:10:05"
    },
    "eligible_count": 8,
    "input_count": 8,
    "discarded": []
  },
  "errors": []
}
```

---

## 8. Persistencia
* **Cero escrituras en SQLite:** La Fase 4 no muta ninguna tabla.

---

## 9. Manejo de Errores y Fallbacks
* Si no hay temas elegibles (lista vacía o todos usados), `selected_topic` es `None`, el output se guarda con `status = "draft"` y un error `"No se encontraron temas elegibles"`.
* Si el input de Fase 3 venía en `draft` o con `used_fallback = True`, el output de Fase 4 hereda el estado `draft`.
* Errores de lectura de archivo o contrato inválido generan un JSON con `status = "error"`.

---

## 10. Pruebas Relacionadas
* [`tests/test_topic_selector_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_topic_selector_service.py):
  - `test_select_topic_returns_first_valid_unused_and_preserves_input_order`
  - `test_select_topic_does_not_mutate_received_items`
  - `test_select_topic_does_not_prioritize_by_score`
  - `test_select_topic_ignores_invalid_structures_invalid_ids_empty_titles_and_used_topics`
  - `test_process_duplicates_output_success_matches_schema_filename_and_counts`
  - `test_process_duplicates_output_without_eligible_topics_is_draft`
  - `test_create_reuse_topic_output_preserves_used_and_is_explicit`

---

## 11. ADRs Asociados
* [ADR-0005: Comunicación inter-fase basada en outputs JSON versionados](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md)
* [ADR-0008: Deduplicación por `normalized_title` y persistencia atómica en SQLite](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0008-duplicate-detection-idempotency.md)
* [ADR-0009: Selección determinística pura de tema postergando la mutación de estado](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0009-pure-topic-selection.md)

---

## 12. Limitaciones Conocidas
* No analiza el contexto semántico del tema para ponderar cuál es "más viral"; la prioridad la dicta estrictamente la posición provista por Google Trends en el paso 2.
