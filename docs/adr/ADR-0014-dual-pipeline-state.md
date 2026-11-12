# ADR-0014: Persistencia dual de estado: `pipeline_state.json` y tabla relacional `pipeline_runs`

## Estado
Accepted

## Contexto
El pipeline de generación necesita coordinar dos necesidades operativas distintas:
1. **Estado activo en tiempo real:** Saber qué paso se está ejecutando en el momento presente, qué pasos fueron seleccionados por el usuario, cuál es el siguiente paso y cuáles son las referencias a los outputs de la rama en curso.
2. **Historial duradero y consultable:** Poder listar corridas pasadas, filtrar por fechas, buscar qué post se generó para qué tema y analizar errores históricos sin tener que recorrer y parsear cientos de archivos JSON en el sistema de archivos.

## Decisión
Implementar un modelo de **Persistencia Dual Complementaria**:
1. **Estado Volátil/Activo en Archivo JSON (`output/pipeline_state.json`):**
   - Gestionado por [`python_backend/services/pipeline/pipeline_state_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/pipeline/pipeline_state_service.py).
   - Representa la "rama activa" en memoria/disco.
   - Contiene `run_id`, `status` (`idle`, `running`, `success`, `draft`, `error`, `cancelled`), `current_step`, `selected_steps`, `completed_steps`, `next_step` y un mapa `outputs` con las rutas a los archivos JSON generados.
   - Se puede reiniciar con `DELETE /api/pipeline/state` o mediante CLI con `tools/pipeline_state.py reset`.
2. **Historial Persistente en Tabla Relacional SQLite (`pipeline_runs`):**
   - Gestionado por [`python_backend/services/pipeline/pipeline_history_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/pipeline/pipeline_history_service.py).
   - Cada cambio de estado de la rama activa se sincroniza mediante `upsert_pipeline_run`, insertando o actualizando una fila en la tabla `pipeline_runs` indexada por `run_id`.
   - Almacena en columnas indexadas: `started_at`, `updated_at`, `status`, `topic_id`, `topic_title`, `post_id`, `quality_score`, y en columnas de texto los JSON serializados (`outputs_json`, `errors_json`, `evidence_json`).
   - Soporta filtros avanzados en endpoints `GET /api/pipeline/runs` y `GET /api/pipeline/history` (por rango de fechas, topic ID y búsqueda de texto).

## Justificación
- **El archivo JSON desacopla la ejecución:** La orquestación paso a paso lee y escribe un archivo JSON rápido sin lidiar con bloqueos de base de datos ni esquemas rígidos durante el avance del pipeline.
- **La tabla SQLite optimiza las consultas:** Evita que el endpoint de historial tenga que escanear el directorio `output/` con `os.listdir()` y abrir cientos de archivos para responder al usuario.
- **Resiliencia ante reseteos:** Borrar o reiniciar `pipeline_state.json` para empezar una nueva corrida **no borra el historial de corridas en `pipeline_runs`**, preservando la memoria histórica del proyecto.

## Alternativas consideradas
- **Persistir únicamente en SQLite:** Descartada para mantener las herramientas CLI de desarrollo (`tools/pipeline_state.py`) operando directamente sobre JSON simple sin requerir inicializar el motor de SQLAlchemy.
- **Persistir únicamente en JSON:** Descartada por la lentitud e ineficiencia que supondría paginar y filtrar el historial web desde el disco.

## Consecuencias positivas
- Separación limpia entre "lo que está pasando ahora" y "lo que pasó antes".
- Consultas SQL ultrarrápidas para la vista de historial (`frontend/history.html`).
- Capacidad de reconstruir el estado activo a partir de outputs existentes mediante `tools/pipeline_state.py bootstrap-current`.

## Consecuencias negativas
- Duplicidad de persistencia que requiere disciplina para mantener ambos sincronizados (resuelto invocando `sync_current_pipeline_state` en los routers).

## Componentes afectados
- [`python_backend/services/pipeline/pipeline_state_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/pipeline/pipeline_state_service.py): Manejo del archivo JSON.
- [`python_backend/services/pipeline/pipeline_history_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/pipeline/pipeline_history_service.py): Sincronización y consultas en SQLite.
- [`python_backend/models/pipeline_run_model.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/models/pipeline_run_model.py): Modelo ORM `PipelineRun`.
- [`tools/pipeline_state.py`](file:///Users/luis/desktop/PROYECTOS/trending/tools/pipeline_state.py): Herramienta CLI de inspección y reseteo.

## Evidencias
- [`python_backend/models/pipeline_run_model.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/models/pipeline_run_model.py): Definición de la entidad `PipelineRun` con índices sobre `updated_at`, `status`, `topic_id`.
- [`python_backend/services/pipeline/pipeline_history_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/pipeline/pipeline_history_service.py#L34-L80): Función `upsert_pipeline_run`.
- [`tests/test_pipeline_state_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_pipeline_state_service.py) y [`test_pipeline_history_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_pipeline_history_service.py): Pruebas de sincronización, aislamiento y filtros.

## Trazabilidad
- **Fase:** Orquestación Transversal del Pipeline.
- **Fecha verificable:** 2026-07-27 / 2026-07-28.
- **Decisiones relacionadas:** [ADR-0003](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0003-sqlite-sqlalchemy.md), [ADR-0005](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md), [ADR-0015](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0015-cooperative-request-cancellation.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia directa en modelos, base de datos y tests.
