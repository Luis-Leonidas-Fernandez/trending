# ADR-0012: Publicación en dos tiempos: persistencia como `draft` y simulación auditada

## Estado
Accepted

## Contexto
La Fase 6 (Participante 6) tiene la responsabilidad de publicar el post en Instagram. La integración con **Instagram Graph API** oficial requiere una cuenta de Instagram Business o Creator vinculada a una página de Facebook, registro en Meta for Developers, tokens de acceso de larga duración con permisos específicos (`instagram_content_publish`) y que la imagen sea accesible mediante una URL HTTPS pública de internet (Meta rechaza IPs locales `127.0.0.1`). Exigir estos requisitos impedía probar y evaluar el pipeline localmente sin credenciales de Meta y túneles ngrok.

## Decisión
Dividir la Fase 6 en dos momentos operativos bien diferenciados en [`python_backend/services/instagram/instagram_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/instagram/instagram_service.py):
1. **Subfase 6A — Persistencia y Preparación:**
   - Consume el output de Fase 5.
   - Crea el registro del post en la tabla `generated_posts` de SQLite con estado inicial `status = "draft"`.
   - **No llama a Instagram externo** y **no marca el tema como usado** (`topic.used` sigue en `0`).
   - Genera el output versionado `output/participante-6/instagram_v1_{id}.json` con `ready_to_publish = False` y `publication_skipped = True`.
2. **Subfase 6B — Simulación de Publicación Local y Auditoría:**
   - Provee la función `simulate_publication(post_id)` expuesta en `POST /api/posts/{id}/publish-simulated` y `POST /api/pipeline/publish-simulated`.
   - Valida que el post exista, tenga `caption` y `image_url`.
   - Inserta un registro en `publication_logs` con `platform = "instagram"`, `status = "published_simulated"` y un payload JSON que aclara `external_publication: False`, `provider: "local_audit"`.
   - Actualiza el estado del post a `published_simulated`.
   - **Marca definitivamente el tema asociado como usado (`topic.used = 1`).**

## Justificación
- **Ejecución autónoma y educativa:** Permite recorrer el ciclo completo de vida de una publicación (de borrador a publicado) sin depender de Meta ni de credenciales pagas.
- **Trazabilidad estricta:** La separación garantiza que si el pipeline falla antes de la simulación, el tema no se marca como usado.
- **Preparación para producción:** La arquitectura deja el punto de enganche exacto en `publish_post` para incorporar la llamada real a `graph.facebook.com/v19.0/{ig_user_id}/media` en una versión futura sin alterar el resto del pipeline.

## Alternativas consideradas
- **Integración real con Instagram Graph API en esta etapa:** Descartada por requerir dominio HTTPS público y cuenta Meta Business aprobada, inviable para el entorno de desarrollo local.
- **Marcar como publicado directamente en Fase 6A:** Descartada porque se deseaba poder auditar el borrador en la UI antes de "cerrar" la publicación.

## Consecuencias positivas
- El pipeline puede cerrarse exitosamente de punta a punta en cualquier máquina local.
- Registro auditable en `publication_logs` con trazabilidad al post y al tema.
- Se evita el riesgo de publicar contenidos de prueba en cuentas reales de redes sociales.

## Consecuencias negativas
- La aplicación no publica efectivamente en Instagram en este release; es una simulación local auditada.

## Componentes afectados
- [`python_backend/services/instagram/instagram_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/instagram/instagram_service.py): Métodos `publish_post`, `simulate_publication`, `process_ai_output`.
- [`python_backend/repositories/post_repository.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories/post_repository.py) y [`log_repository.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories/log_repository.py).
- [`python_backend/routers/posts_router.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/routers/posts_router.py) y [`pipeline_router.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/routers/pipeline_router.py).

## Evidencias
- [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L94-L106): Descripción detallada de las subfases 6A y 6B.
- [`python_backend/services/instagram/instagram_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/instagram/instagram_service.py#L54-L100): Implementación de `simulate_publication`.
- [`tests/test_instagram_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_instagram_service.py): Pruebas `test_process_ai_output_persists_post_and_generates_success_output`, `test_simulate_publication_creates_log_updates_post_and_marks_topic`.

## Trazabilidad
- **Fase:** Fase 6 (Publicación / Persistencia).
- **Fecha verificable:** 2026-07-27.
- **Decisiones relacionadas:** [ADR-0003](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0003-sqlite-sqlalchemy.md), [ADR-0009](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0009-pure-topic-selection.md), [ADR-0013](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0013-local-audit-metrics.md).

## Observaciones
Decisión plenamente **Confirmada**. El código distingue claramente entre `ready_to_publish: false` y `simulated: true`.
