# ADR-0008: Deduplicación por `normalized_title` y persistencia atómica en SQLite

## Estado
Accepted

## Contexto
Google Trends suele devolver temas redactados con ligeras variaciones ortográficas, diferencias de mayúsculas o acentos en distintas consultas, y puede repetir tendencias a lo largo de los días. Si el sistema no filtra rigurosamente los duplicados, generará posts repetidos sobre el mismo acontecimiento. Además, se requería una estrategia clara para la persistencia: ¿en qué momento se escriben los temas en la tabla `trending_topics` y cómo se tratan los temas que ya existen en la base de datos pero aún no han sido publicados?

## Decisión
1. Implementar la deduplicación en la Fase 3 ([`python_backend/services/duplicates/duplicates_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/duplicates/duplicates_service.py)) aplicando **igualdad exacta sobre `normalized_title`** (reutilizando la misma función canónica de Fase 2).
2. Aplicar un doble nivel de filtrado preservando estrictamente el orden original de entrada:
   - **Nivel 1 (Deduplicación interna del lote):** Descartar temas que aparezcan repetidos dentro del mismo input de Fase 2 (`_DISCARD_DUPLICATE_INPUT`).
   - **Nivel 2 (Deduplicación contra base de datos):** Comparar contra todos los registros existentes en `trending_topics`.
3. **Regla de tratamiento de temas existentes en SQLite:**
   - Si el tema ya existe en SQLite y `used == 1` (ya se publicó un post con él), se descarta de forma definitiva (`_DISCARD_ALREADY_USED`).
   - Si el tema ya existe en SQLite pero `used == 0` (no ha sido utilizado aún), **no se vuelve a insertar en la base**, pero se recupera y se incluye en la lista de candidatos como tema reutilizable (`reusable_items`).
4. **Persistencia atómica:** Persistir en la tabla `trending_topics` **únicamente los temas nuevos** (`new_items`) mediante `topic_repository.create_topic`, obteniendo sus IDs autoincrementales asignados por SQLite.
5. El output de Fase 3 consolida tanto los temas recién guardados como los reutilizables disponibles (`candidate_items = [*saved_items, *reusable_items]`), junto con contadores auditables de descartes.

## Justificación
- **Idempotencia y ahorro de almacenamiento:** Evita la polución de la tabla `trending_topics` con filas redundantes.
- **Tolerancia a ejecuciones repetidas:** Si el usuario corre el pipeline varias veces en el mismo día sobre el mismo RSS, el sistema no duplica filas y sigue ofreciendo temas válidos no usados.
- **Integridad:** Asigna un ID primario entero positivo de SQLite a cada tema antes de pasar a la selección de Fase 4.

## Alternativas consideradas
- **Detección semántica por IA / embeddings:** Descartada por complejidad excesiva, costo computacional y retraso en el tiempo de respuesta para una tarea que se resuelve eficazmente por normalización ortográfica.
- **Índice UNIQUE en SQLite sobre `normalized_title` sin filtro en memoria:** Descartada para permitir auditar explícitamente en el JSON de salida la razón exacta de cada descarte (`duplicate_in_input`, `duplicate_in_database`, `already_used_in_database`, `invalid_title`).

## Consecuencias positivas
- Prevención de publicaciones duplicadas en Instagram.
- Auditoría exacta en el JSON de Fase 3 de cuántos temas entraron, cuántos se guardaron, cuántos eran reutilizables y cuántos se descartaron con sus motivos.
- Preservación del orden de ranking de tendencias recibido de Google Trends.

## Consecuencias negativas
- Si una tendencia tiene redacciones sustancialmente distintas (ej. "Dólar blue" vs "Cotización de la divisa informal"), la normalización por caracteres no detectará que hablan del mismo evento.

## Componentes afectados
- [`python_backend/services/duplicates/duplicates_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/duplicates/duplicates_service.py): Algoritmo de filtrado y persistencia.
- [`python_backend/repositories/topic_repository.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories/topic_repository.py): Métodos de consulta y creación.
- [`output/participante-3/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-3): JSON de auditoría de Fase 3.

## Evidencias
- [`python_backend/services/duplicates/duplicates_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/duplicates/duplicates_service.py#L40-L98): Funciones `filter_new_topics` y `process_trends_output`.
- [`tests/test_duplicates_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_duplicates_service.py): Pruebas `test_filter_new_topics_normalizes_case_accents_punctuation_and_spaces`, `test_process_trends_output_discards_existing_used_topics`, `test_process_trends_output_reuses_existing_unused_topics_as_candidates`.

## Trazabilidad
- **Fase:** Fase 3 (Filtrar duplicados).
- **Fecha verificable:** 2026-07-27 (completado por intervención administrativa según `CONTROL_CAMBIOS.md`).
- **Decisiones relacionadas:** [ADR-0003](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0003-sqlite-sqlalchemy.md), [ADR-0005](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md), [ADR-0007](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0007-trends-rss-fallback.md), [ADR-0009](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0009-pure-topic-selection.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia en código, registros de cambios y pruebas de integración con SQLite temporal.
