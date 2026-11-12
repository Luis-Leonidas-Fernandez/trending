# Fase 1 — Backend Base, Persistencia y API

## 1. Objetivo
Establecer la infraestructura de software del proyecto sobre **Python 3.14.5 + FastAPI + SQLAlchemy + SQLite**, configurando la inicialización del esquema de datos relacional, la validación de contratos con Pydantic y los endpoints REST fundamentales para temas, posts y bitácoras técnicas.

---

## 2. Responsabilidad
* Configurar la aplicación FastAPI con middlewares de CORS y manejador global de validación.
* Proveer la conexión a SQLite con integridad referencial forzada (`PRAGMA foreign_keys=ON`).
* Proveer los modelos declarativos ORM en `models/` y sus repositorios encapsulados en `repositories/`.
* Exponer los routers modulares para operaciones CRUD básicas de topics, posts y logs.
* Servir los assets estáticos de Fase 5B en `/assets/participante-5/`.

---

## 3. Entradas
* Peticiones HTTP en formato JSON (`Content-Type: application/json`) validadas contra esquemas Pydantic (`TopicCreate`, `PostCreate`, `LogCreate`).
* Variables de entorno leídas vía `python-dotenv`: `PYTHON_DB_FILE`, `HOST`, `PORT`, etc.

---

## 4. Procesamiento
1. En el arranque de la aplicación ([`main.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py#L16)), se ejecuta [`initialize_database()`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/database/connection.py#L57), invocando `Base.metadata.create_all(bind=engine)`.
2. Las rutas REST en `routers/` reciben la carga, Pydantic valida el tipado y delega la operación a la función correspondiente de `repositories/`.
3. El repositorio abre una sesión con `with get_session() as session:`, ejecuta la sentencia SQLAlchemy y convierte la entidad resultante a diccionario nativo de Python antes de retornar.

---

## 5. Salidas
* Respuestas HTTP con estructura uniforme `{"success": true, "data": ...}` o `{"success": false, "message": ..., "errors": ...}`.
* Códigos HTTP: `200 OK`, `201 Created`, `400 Bad Request`, `404 Not Found`, `422 Unprocessable Entity`.
* Archivo físico de base de datos en `python_backend/database/trending.sqlite`.

---

## 6. Dependencias
* **Internas:** `python_backend/database/`, `python_backend/models/`, `python_backend/repositories/`, `python_backend/schemas/`.
* **Externas:** `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `python-dotenv`.

---

## 7. Contratos JSON
Ejemplo de creación de tema (`POST /api/topics`):
```json
{
  "title": "Inteligencia Artificial en Argentina",
  "normalized_title": "inteligencia artificial en argentina",
  "source": "manual",
  "score": 100.0,
  "used": 0
}
```

---

## 8. Persistencia
* Tabla `trending_topics`: Almacena temas descubiertos o creados.
* Tabla `generated_posts`: Almacena posts en estado borrador o simulado.
* Tabla `publication_logs`: Almacena bitácoras técnicas de intentos de publicación.

---

## 9. Manejo de Errores
* **`RequestValidationError`:** Capturado por [`validation_exception_handler`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py#L38-L48). Devuelve código `422` con lista detallada de errores de formato.
* **`IntegrityError` de base de datos:** Mapeado en los routers a `HTTP 400 Bad Request` si se intenta violar una restricción de clave foránea.
* **Entidades no encontradas:** Retornan `HTTP 404 Not Found`.

---

## 10. Pruebas Relacionadas
* [`tests/test_python_backend.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_python_backend.py):
  - `test_health_endpoint_returns_success`
  - `test_create_and_list_topic`
  - `test_invalid_topic_returns_clear_error`
  - `test_create_post_and_log_with_relationships`
  - `test_get_post_by_id_includes_topic_title_without_detached_error`

---

## 11. ADRs Asociados
* [ADR-0001: Adopción de Python 3.14.5 y FastAPI como framework central](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0001-fastapi-backend.md)
* [ADR-0002: Arquitectura en capas con responsabilidad única](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0002-layered-architecture.md)
* [ADR-0003: Persistencia relacional con SQLite y SQLAlchemy ORM](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0003-sqlite-sqlalchemy.md)
* [ADR-0004: Validación tipada de entradas y salidas con Pydantic v2](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0004-pydantic-contracts.md)

---

## 12. Limitaciones Conocidas
* No implementa autenticación ni autorización de usuarios para los endpoints de la API (asume uso local/monousuario).
* La concurrencia de escritura está limitada por el motor de bloqueo de archivo único de SQLite.
