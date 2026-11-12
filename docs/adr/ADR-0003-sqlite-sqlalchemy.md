# ADR-0003: Persistencia relacional con SQLite y SQLAlchemy ORM en modo síncrono

## Estado
Accepted

## Contexto
El backend requiere persistir datos relacionales entre tendencias descubiertas (`trending_topics`), publicaciones generadas (`generated_posts`), bitácoras de auditoría (`publication_logs`) y el historial de ejecuciones del pipeline (`pipeline_runs`). La solución de base de datos debía ser cero-configuración, ejecutarse localmente sin requerir demonios externos (como PostgreSQL o MySQL) y soportar relaciones e integridad referencial estricta.

## Decisión
1. Adoptar **SQLite** embebido como motor de persistencia relacional principal, almacenado en `python_backend/database/trending.sqlite` (configurable vía variable `PYTHON_DB_FILE`).
2. Utilizar **SQLAlchemy** (`2.0.44`) con mapeo declarativo moderno (`Mapped`, `mapped_column`, `relationship`).
3. Activar de manera forzosa la integridad referencial en SQLite mediante el evento de conexión `PRAGMA foreign_keys=ON`.
4. Utilizar sesiones síncronas estándar (`sessionmaker(future=True)`) con context managers por transacción (`with get_session() as session:`).
5. Mantener un archivo canónico de DDL en [`schema.sql`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/database/schema.sql) como referencia documental del esquema.

## Justificación
- **Portabilidad absoluta:** SQLite no requiere instalación de servicios de base de datos, facilitando que nuevos integrantes y entornos Windows/macOS/Linux levanten el proyecto en segundos.
- **Transaccionalidad ACID y claves foráneas:** La activación de `PRAGMA foreign_keys=ON` garantiza que ningún post huérfano apunte a un tema inexistente y que ningún log apunte a un post inexistente.
- **ORM Declarativo 2.0:** SQLAlchemy 2.0 ofrece compatibilidad nativa con tipos de Python y previene errores sutiles de sintaxis SQL.
- **Concurrencia local:** `connect_args={"check_same_thread": False}` permite a FastAPI atender solicitudes síncronas concurrentes sin bloquear la conexión de SQLite.

## Alternativas consideradas
- **SQLite3 nativo sin ORM:** Implementado inicialmente el 2026-05-31 y descartado el mismo día (migrado a SQLAlchemy para desacoplar consultas crudas y evitar inyecciones SQL o boilerplate de mapeo).
- **PostgreSQL / MySQL:** Descartados por imponer dependencias de infraestructura local (Docker, servicios del SO) que complicaban el setup a principiantes.

## Consecuencias positivas
- El proyecto se levanta con un archivo `.sqlite` local que se inicializa automáticamente al arrancar ([`initialize_database()`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/database/connection.py#L57)).
- Pruebas aisladas ultrarrápidas utilizando bases temporales creadas al vuelo vía `tempfile` en pytest.
- Integridad referencial reforzada a nivel de motor.

## Consecuencias negativas
- SQLite no está diseñado para alta concurrencia masiva de escritura simultánea en producción distribuida (limitación asumida para el alcance MVP/educativo).
- Las migraciones de esquema estructurales en SQLite son más complejas que en PostgreSQL (resuelto manteniendo tablas complementarias como `pipeline_runs` creadas idempotentemente con `create_all`).

## Componentes afectados
- [`python_backend/database/connection.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/database/connection.py): Configuración del engine, eventos y sessions.
- [`python_backend/database/schema.sql`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/database/schema.sql): Referencia DDL del esquema relacional.
- [`python_backend/models/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/models): Entidades ORM (`base.py`, `topic_model.py`, `post_model.py`, `log_model.py`, `pipeline_run_model.py`).
- [`python_backend/repositories/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/repositories): Acceso a datos.

## Evidencias
- [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L51-L55): Registro de migración de `sqlite3` directo a SQLAlchemy bajo fecha 2026-05-31.
- [`python_backend/database/connection.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/database/connection.py#L40-L45): Listener `set_sqlite_pragma` con `PRAGMA foreign_keys=ON`.
- [`tests/test_python_backend.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_python_backend.py#L11-L14): Aislamiento en tests mediante base temporal en variable `PYTHON_DB_FILE`.

## Trazabilidad
- **Fase:** Fase 1 (Backend Base) y Persistencia.
- **Fecha verificable:** 2026-05-31.
- **Decisiones relacionadas:** [ADR-0001](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0001-fastapi-backend.md), [ADR-0002](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0002-layered-architecture.md), [ADR-0008](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0008-duplicate-detection-idempotency.md), [ADR-0014](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0014-dual-pipeline-state.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia directa en código y pruebas de integridad referencial.
