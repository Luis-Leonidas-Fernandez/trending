# ADR-0009: Selección determinística pura de tema postergando la mutación de estado

## Estado
Accepted

## Contexto
Una vez filtrados los temas en Fase 3, el pipeline debe decidir cuál de ellos avanzará a la costosa fase de generación de contenido con IA (Fase 5). Existía la disyuntiva de si la Fase 4 debía marcar inmediatamente el tema como `used = 1` en la base de datos para reservarlo. Si el tema se marcaba como usado en Fase 4 y posteriormente la Fase 5 fallaba (por falta de tokens, error en Spartan o timeout de red), dicho tema quedaba "quemado" e inutilizable en SQLite sin haber producido ningún post.

## Decisión
1. Diseñar la Fase 4 ([`python_backend/services/topic_selector/topic_selector_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/topic_selector/topic_selector_service.py)) como un **Selector Funcional Puro**:
   - Consume el JSON versionado de Fase 3.
   - Preserva estrictamente el orden recibido en `data.items`.
   - Aplica la estrategia determinística `STRATEGY = "first_valid_unused"`.
   - Selecciona el primer elemento que cumpla: es un diccionario, tiene `id` entero positivo, `title` y `normalized_title` válidos, y `used` es exactamente `0` o `False`.
2. **Postergación de mutación de base de datos:** La Fase 4 **no realiza consultas a SQLite ni modifica el campo `used`** del tema elegido.
3. El marcado definitivo `topic.used = 1` se traslada a la finalización exitosa de la publicación en la Fase 6B.
4. **Modo de Reutilización Manual (`manual_history_reuse`):** Se dota al selector de la función `create_reuse_topic_output` para permitir que un usuario elija desde el frontend cualquier tema previo no usado y genere una selección explícita sin necesidad de ejecutar las Fases 2 y 3.

## Justificación
- **Seguridad ante fallos en fases posteriores:** Si la IA en Fase 5 arroja error, el tema sigue intacto en SQLite con `used = 0` y puede ser reintentado o seleccionado en una corrida posterior.
- **Transparencia funcional y reproducibilidad:** La función `select_topic(topics)` no produce efectos colaterales en el sistema.
- **Separación de responsabilidades:** La selección es una decisión de filtrado y prioridad; la modificación del ciclo de vida del post le corresponde a la fase de publicación.

## Alternativas consideradas
- **Marcar `used = 1` inmediatamente en Fase 4:** Descartada formalmente en `CONTROL_CAMBIOS.md` (2026-07-27) tras evaluar el riesgo de quemar temas ante fallos de downstream.
- **Selección aleatoria o basada en machine learning:** Descartada para mantener el pipeline predecible y respetar el orden de relevancia entregado por Google Trends.

## Consecuencias positivas
- Tolerancia total a fallos en la generación de IA sin pérdida de temas candidatos.
- El servicio es completamente testeable con pruebas unitarias en memoria sin base de datos.
- Permite la funcionalidad de reutilizar temas desde el historial en un clic.

## Consecuencias negativas
- Si dos pipelines corrieran en paralelo simultáneo sobre la misma base (escenario fuera del alcance mono-usuario actual), ambos seleccionarían el mismo primer tema al no haber un bloqueo o reserva intermedia.

## Componentes afectados
- [`python_backend/services/topic_selector/topic_selector_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/topic_selector/topic_selector_service.py): Lógica de selección pura.
- [`python_backend/routers/pipeline_router.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/routers/pipeline_router.py): Endpoints `/pipeline/select` y `/pipeline/topics/{id}/reuse`.
- [`output/participante-4/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-4): Salidas versionadas de selección.

## Evidencias
- [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L80-L82): *"Se decidió no modificar SQLite ni marcar used en esta fase; ese cambio queda reservado para después de persistir exitosamente el post en una fase posterior"*.
- [`python_backend/services/topic_selector/topic_selector_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/topic_selector/topic_selector_service.py#L39-L50): Función `select_topic` que no muta la lista ni accede a repositorios.
- [`tests/test_topic_selector_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_topic_selector_service.py): Pruebas `test_select_topic_does_not_mutate_received_items`, `test_select_topic_returns_first_valid_unused_and_preserves_input_order`.

## Trazabilidad
- **Fase:** Fase 4 (Selector de tema).
- **Fecha verificable:** 2026-07-27.
- **Decisiones relacionadas:** [ADR-0005](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md), [ADR-0008](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0008-duplicate-detection-idempotency.md), [ADR-0010](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0010-spartan-ai-provider.md), [ADR-0012](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0012-two-step-publication.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia textual directa en la documentación y pruebas automáticas.
