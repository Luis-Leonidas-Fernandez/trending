# ADR-0013: Medición y scoring de calidad local en lugar de métricas remotas de red social

## Estado
Accepted

## Contexto
El plan original del proyecto asignaba la Fase 7 (Participante 7) a "Métricas y Frontend". Al no realizarse una publicación externa real en la red social de Instagram (según se estableció en el [ADR-0012](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0012-two-step-publication.md)), no existen métricas reales de engagement como likes, comentarios, impresiones o alcance provistos por la Graph API de Meta. Sin embargo, el pipeline requería una fase final de cierre que evaluara si el ciclo de producción fue satisfactorio o defectuoso.

## Decisión
1. Reorientar el servicio del Participante 7 ([`python_backend/services/metrics/metrics_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/metrics/metrics_service.py)) como un **Motor de Medición y Auditoría Local de Calidad**.
2. Evaluar de forma determinística una serie de condiciones objetivas sobre el post y su contexto en SQLite:
   - `has_post`: Si el post existe en la tabla `generated_posts`.
   - `has_caption`: Si el texto del caption no está vacío.
   - `has_image`: Si existe una ruta de imagen asociada.
   - `has_publication_log`: Si existe al menos un registro en `publication_logs`.
   - `topic_marked_used`: Si el tema asociado en `trending_topics` tiene efectivamente `used == 1`.
   - `is_published_simulated`: Si el estado final del post es `published_simulated`.
3. Calcular un **Score de Calidad** porcentual basado en el ratio de comprobaciones superadas (0 a 100%).
4. Emitir el output `output/participante-7/metrics_v1_{id}.json` con `status = "success"` si el score es exactamente 100, o `status = "draft"` si existen advertencias o comprobaciones pendientes.

## Justificación
- **Control de Calidad Automatizado:** Permite al sistema verificar por sí mismo si la ejecución cumplió todas las garantías arquitectónicas antes de dar la corrida por completada.
- **Sin dependencias remotas:** No requiere credenciales ni conectividad externa para auditar el post.
- **Feedback visual en el dashboard:** El puntaje de calidad se envía directamente a la interfaz web para mostrar una insignia de aprobación y el detalle de advertencias.

## Alternativas consideradas
- **Generar números aleatorios o falsos de "likes":** Descartada por ser engañosa y carecer de valor técnico o arquitectónico.
- **Omitir la Fase 7 y terminar en Fase 6:** Descartada para mantener el esquema de 7 participantes y brindar un reporte final consolidado de la corrida.

## Consecuencias positivas
- Reporte consolidado de integridad del post generado.
- Alimenta la vista de auditoría en el frontend (`GET /api/posts/audit/latest` y `GET /api/pipeline/metrics/latest`).
- Permite detectar fallos parciales (ej. post creado pero no simulado, o tema no marcado).

## Consecuencias negativas
- El usuario debe tener claro que la puntuación mide la **calidad estructural y técnica de la ejecución**, no el impacto o rendimiento comercial en la red social.

## Componentes afectados
- [`python_backend/services/metrics/metrics_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/metrics/metrics_service.py): Lógica de auditoría y cálculo de score.
- [`python_backend/routers/pipeline_router.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/routers/pipeline_router.py): Endpoint `/pipeline/metrics/latest`.
- [`output/participante-7/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-7): Directorio de outputs de Fase 7.

## Evidencias
- [`docs/exposure-participant-7.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/exposure-participant-7.md): *"Mi participante se encarga de la fase Medir. No consulta métricas reales de Instagram. Lo que hace es auditar localmente que el post haya quedado correctamente publicado en modo simulado"*.
- [`python_backend/services/metrics/metrics_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/metrics/metrics_service.py#L46-L56): Construcción del payload de métricas.
- [`tests/test_metrics_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_metrics_service.py): Pruebas `test_process_instagram_output_scores_success_when_local_audit_is_complete` y `test_process_instagram_output_returns_draft_when_checks_are_missing`.

## Trazabilidad
- **Fase:** Fase 7 (Medir / Auditoría final).
- **Fecha verificable:** 2026-07-27.
- **Decisiones relacionadas:** [ADR-0005](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md), [ADR-0012](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0012-two-step-publication.md), [ADR-0014](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0014-dual-pipeline-state.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia directa en código y guías de exposición.
