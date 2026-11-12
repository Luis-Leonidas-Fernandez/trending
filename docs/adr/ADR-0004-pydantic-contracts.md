# ADR-0004: Validación tipada de entradas y salidas mediante contratos Pydantic v2

## Estado
Accepted

## Contexto
En un flujo modular donde múltiples participantes e integraciones externas interactúan con la API y generan archivos JSON en disco, la falta de validación tipada provoca fallos silenciosos, inconsistencia en los nombres de campos (ej. `camelCase` vs `snake_case`) y desvíos de formato que son difíciles de depurar aguas abajo. Se requería un mecanismo declarativo, estricto y de alto rendimiento para validar cargas útiles HTTP y la estructura de archivos persistidos.

## Decisión
1. Adoptar **Pydantic v2** (`pydantic==2.13.4`) como la biblioteca estándar y única de validación de datos del proyecto.
2. Definir esquemas para peticiones HTTP dentro de `python_backend/schemas/` (`topic_schema.py`, `post_schema.py`, `log_schema.py`).
3. Definir un esquema formal canónico de salida inter-fases en [`python_backend/schemas/output_schema.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/schemas/output_schema.py) mediante la clase [`ParticipantOutput`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/schemas/output_schema.py#L32), fijando `schema_version = "1.0"`, `run_id` como UUID, participantes permitidos, etapas (`stage`), estado (`status`), metadatos y listas de errores.
4. Configurar un manejador de excepciones personalizado en FastAPI ([`validation_exception_handler`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py#L38-L48)) que intercepte `RequestValidationError` y devuelva un formato estandarizado JSON (`HTTP 422` con `success: False`, `message: "JSON inválido"` y lista de errores).

## Justificación
- **Validación robusta:** Pydantic v2 está implementado internamente en Rust (pydantic-core), ofreciendo una velocidad de serialización y deserialización óptima.
- **Mensajes de error precisos:** Permite a los participantes saber exactamente qué campo falló, qué tipo se esperaba y qué valor se recibió.
- **Consistencia inter-fase:** Cada servicio que consume un archivo de una fase previa valida su contenido mediante `ParticipantOutput.model_validate(payload)`. Si el esquema no cumple el contrato, el servicio rechaza el procesamiento de inmediato con error controlado.

## Alternativas consideradas
- **Zod:** Utilizado en la etapa inicial de Node.js (2026-05-25). Fue sustituido por Pydantic al migrar a Python el 2026-05-31.
- **Validación manual con `dict.get()` y `isinstance()`:** Descartada por ser propensa a errores humanos, generar código repetitivo y carecer de tipado formal.

## Consecuencias positivas
- Prevención total de datos mal formados en la base de datos o en los outputs del pipeline.
- Generación automática de especificaciones JSON Schema y Swagger en FastAPI.
- Manejo uniforme de errores en respuestas HTTP 422.

## Consecuencias negativas
- Curva de adaptación a las restricciones estrictas de tipos para desarrolladores principiantes.
- Necesidad de mantener actualizados los modelos Pydantic si evolucionan los contratos de datos.

## Componentes afectados
- [`python_backend/schemas/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/schemas): Todos los modelos Pydantic (`output_schema.py`, `topic_schema.py`, `post_schema.py`, `log_schema.py`).
- [`python_backend/main.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py): Handler de validación HTTP.
- [`tools/validate_output.py`](file:///Users/luis/desktop/PROYECTOS/trending/tools/validate_output.py): Herramienta CLI de verificación basada en Pydantic.

## Evidencias
- [`python_backend/schemas/output_schema.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/schemas/output_schema.py#L32-L40): Definición de `ParticipantOutput`.
- [`python_backend/main.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py#L38-L48): `validation_exception_handler`.
- [`tests/test_output_validation.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_output_validation.py): Pruebas completas de validación de esquemas válidos e inválidos.

## Trazabilidad
- **Fase:** Fase 1 (Backend Base) y Contratos del Pipeline.
- **Fecha verificable:** 2026-05-31.
- **Decisiones relacionadas:** [ADR-0001](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0001-fastapi-backend.md), [ADR-0002](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0002-layered-architecture.md), [ADR-0005](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia directa en código y suite de tests de validación.
