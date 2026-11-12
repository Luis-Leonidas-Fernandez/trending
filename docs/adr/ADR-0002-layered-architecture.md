# ADR-0002: Arquitectura en capas con responsabilidad única y límites por componente

## Estado
Accepted

## Contexto
El desarrollo del proyecto fue concebido para que hasta 7 participantes (y modelos de IA que los asistan) trabajaran simultáneamente en diferentes secciones del pipeline. Sin límites claros, existía el riesgo recurrente de que la lógica de negocio se mezclara en los controladores HTTP, que los endpoints hicieran consultas SQL directas o que un participante sobreescribiera el trabajo de otro.

## Decisión
Se estableció formalmente en [`docs/ARQUITECTURA_Y_NORMAS.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/ARQUITECTURA_Y_NORMAS.md) una arquitectura desacoplada en capas con principio estricto de **Responsabilidad Única**:
1. **`routers/`:** Solo reciben solicitudes HTTP, validan parámetros mediante schemas, delegan a services o repositories y devuelven respuestas HTTP. Prohibido incluir SQL o algoritmos de negocio complejos.
2. **`schemas/`:** Definen y validan contratos de datos con Pydantic. Prohibido consultar base de datos o ejecutar lógica de negocio.
3. **`models/`:** Definen tablas y relaciones ORM con SQLAlchemy. Prohibido contener lógica de negocio o responder HTTP.
4. **`repositories/`:** Encapsulan consultas, escrituras y transacciones en SQLite vía SQLAlchemy. Prohibido mezclar lógica de negocio pesada o responder HTTP.
5. **`services/`:** Contienen la lógica pura de negocio de cada participante, dividida por directorios (`trends/`, `duplicates/`, `topic_selector/`, `ai/`, `instagram/`, `metrics/`, `pipeline/`).
6. **`database/`:** Configura el motor, la sesión y la inicialización del esquema.

## Justificación
- **Aislamiento de responsabilidades:** Facilita la división de tareas y reduce colisiones de código en Git.
- **Testabilidad:** Los servicios pueden ser testeados de manera unitaria con datos aislados o mocks sin necesidad de levantar el servidor HTTP.
- **Claridad para principiantes:** Cada archivo tiene un rol predecible. La regla de diseño explícita es: *"Si hay dos opciones, una compleja y otra simple y suficiente, se debe elegir la simple y suficiente"*.

## Alternativas consideradas
- **Arquitectura Monolítica Plana (FastAPI scripts):** Descartada por provocar acoplamiento severo y bloquear el trabajo paralelo del equipo.
- **Clean Architecture / Hexagonal con interfaces abstractas extensas:** Descartada expresamente por la directriz *"Evitar abstracciones innecesarias y no crear capas extras por las dudas"*.

## Consecuencias positivas
- Separación cristalina entre el protocolo web (FastAPI) y la lógica de dominio (servicios).
- Facilidad para que un participante trabaje exclusivamente en su carpeta designada dentro de `python_backend/services/`.
- Protección contra efectos colaterales al modificar la persistencia o la capa web.

## Consecuencias negativas
- Mayor cantidad de archivos por entidad (un model, un schema, un repository y un router para cada recurso).
- Requiere disciplina para no saltarse capas (ej. llamar a repositories desde routers sin pasar por services en flujos simples).

## Componentes afectados
- [`python_backend/routers/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/routers)
- [`python_backend/schemas/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/schemas)
- [`python_backend/models/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/models)
- [`python_backend/repositories/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories)
- [`python_backend/services/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services)
- [`python_backend/database/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/database)

## Evidencias
- [`docs/ARQUITECTURA_Y_NORMAS.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/ARQUITECTURA_Y_NORMAS.md#L45-L100): Definición explícita de "Responsabilidad por capa" y "Regla práctica: Sí deben / No deben".
- Implementación real en [main.py](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py#L89-L94) donde se montan los routers modulares.

## Trazabilidad
- **Fase:** Fase 1 (Backend Base) y Arquitectura General.
- **Fecha verificable:** 2026-05-31.
- **Decisiones relacionadas:** [ADR-0001](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0001-fastapi-backend.md), [ADR-0003](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0003-sqlite-sqlalchemy.md), [ADR-0006](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0006-participant-isolation-admin-fallback.md).

## Observaciones
Decisión plenamente **Confirmada**. El contrato de arquitectura es el documento normativo más citado y respetado del proyecto.
