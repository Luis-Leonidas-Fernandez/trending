# ADR-0015: Cancelación cooperativa de peticiones HTTP en vuelo (`pipeline_cancel_service`)

## Estado
Accepted

## Contexto
Durante la ejecución del pipeline, la Fase 5 puede tomar entre 10 y 60 segundos si invoca modelos de generación de texto o difusión de imágenes mediante Spartan Provider. Si el usuario cancela la operación desde la interfaz web o si se interrumpe la conexión, los servidores web ASGI tradicionales marcan la conexión cliente como desconectada, pero el hilo de ejecución de Python y la llamada HTTP sincrónica hacia Spartan/OpenAI continúan activas en segundo plano, consumiendo tokens innecesariamente y pudiendo alterar el estado posterior.

## Decisión
Implementar un mecanismo de **Cancelación Cooperativa con Context Variables y Closers Registrados** en [`python_backend/services/pipeline/pipeline_cancel_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/pipeline/pipeline_cancel_service.py):
1. **Contexto de Ejecución:** Usar `ContextVar("pipeline_current_run_id")` mediante el context manager `pipeline_run_scope(run_id)` para que cualquier hilo o servicio conozca cuál es el `run_id` activo.
2. **Registro de Recursos Cancelables:** Usar el context manager `registered_closer(closer)` con un bloqueo `threading.RLock()`. Al abrir un cliente `httpx.Client()` en `ai_service.py`, se registra temporalmente su método `client.close`.
3. **Endpoint de Cancelación:** Al invocar `POST /api/pipeline/cancel`:
   - El estado en `pipeline_state.json` se actualiza inmediatamente a `status = "cancelled"`.
   - Se ejecuta `cancel_active_run(run_id)`, el cual extrae los métodos closer asociados al `run_id` y los ejecuta de inmediato, forzando el cierre prematuro de los sockets TCP/HTTP en vuelo.
   - El cliente HTTP de Spartan recibe una interrupción de conexión y el pipeline aborta de forma limpia sin generar outputs posteriores.

## Justificación
- **Ahorro de recursos y tokens:** Detiene inmediatamente las peticiones costosas de generación de imágenes o texto.
- **Seguridad en concurrencia:** El uso de `ContextVar` y `RLock` garantiza aislamiento y evita colisiones si concurren varias solicitudes.
- **Feedback inmediato al usuario:** El botón "Cancelar" en la interfaz web responde en milisegundos sin esperar a que Spartan agote su timeout.

## Alternativas consideradas
- **Esperar a que termine la llamada y descartar el resultado:** Descartada por desperdiciar tokens y mantener la UI bloqueada.
- **Terminación violenta de subprocesos / threads (`os.kill`):** Descartada por riesgo de corrupción de la base de datos SQLite y desestabilización del proceso FastAPI.

## Consecuencias positivas
- Control total del usuario sobre ejecuciones largas del pipeline.
- Cierre limpio de sockets y descriptores de archivo en el sistema operativo.
- Pruebas automatizadas que validan que el estado se marca como cancelado y se cierran recursos.

## Consecuencias negativas
- Requiere envolver cada cliente HTTP en el context manager `registered_closer(client.close)` dentro de los servicios.

## Componentes afectados
- [`python_backend/services/pipeline/pipeline_cancel_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/pipeline/pipeline_cancel_service.py): Core del servicio de cancelación.
- [`python_backend/services/ai/ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py#L129, #L207): Envoltura de clientes HTTP de texto e imagen.
- [`python_backend/routers/pipeline_router.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/routers/pipeline_router.py#L121-L126): Endpoint `/pipeline/cancel`.

## Evidencias
- [`python_backend/services/pipeline/pipeline_cancel_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/pipeline/pipeline_cancel_service.py#L38-L78): Implementación de `registered_closer` y `cancel_active_run`.
- [`tests/test_pipeline_state_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_pipeline_state_service.py): Pruebas `test_pipeline_cancel_service_closes_registered_resources_for_active_run`, `test_mark_pipeline_cancelled_preserves_current_step_and_outputs`.
- [`tests/test_python_backend.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_python_backend.py): Prueba `test_pipeline_cancel_endpoint_marks_state_cancelled`.

## Trazabilidad
- **Fase:** Transversal / Resiliencia del Pipeline.
- **Fecha verificable:** 2026-07-28.
- **Decisiones relacionadas:** [ADR-0010](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0010-spartan-ai-provider.md), [ADR-0014](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0014-dual-pipeline-state.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia en código fuente y suites de pruebas de concurrencia.
