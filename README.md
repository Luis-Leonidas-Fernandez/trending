# Backend Python - Sistema Trending para Instagram

Este proyecto implementa la base del sistema con **Python + FastAPI + SQLite**.

El objetivo es dejar una estructura simple para que 7 participantes trabajen por partes sin pisarse entre sí.

## Versión de Python recomendada

- `Python 3.14.5`

El proyecto ya fue validado con esa versión y el archivo `/Users/luis/Desktop/trending/.python-version` la deja explícita para que el equipo no improvise con runtimes distintos.

## Estado actual

El backend oficial del proyecto es:

- `python_backend/` → backend Python + FastAPI

El frontend queda reservado para más adelante:

- `frontend/` → espacio reservado para el Participante 7

## Qué incluye hoy

- FastAPI
- SQLite
- SQLAlchemy
- Pydantic para validar JSON
- routers separados por recurso
- models ORM con SQLAlchemy
- repositorios para hablar con la base usando SQLAlchemy
- schema SQL como referencia documental
- placeholders para participantes 2 a 6
- tests básicos con pytest
- lint con Ruff
- outputs JSON versionados y validados por participante

## Qué NO incluye todavía

Todavía NO se implementa:

- integración real con Google Trends
- normalización real de tendencias
- detección real de duplicados
- selección automática real del mejor tema
- generación real de imágenes con IA
- generación real de captions y hashtags con IA
- publicación real en Instagram
- frontend Astro

Eso le corresponde a los participantes asignados.

## Arquitectura elegida

La arquitectura es simple y pensada para principiantes:

- `routers/` → reciben requests HTTP y devuelven responses
- `schemas/` → validan datos de entrada con Pydantic
- `models/` → definen tablas y relaciones con SQLAlchemy
- `repositories/` → acceden a la base usando SQLAlchemy
- `database/` → conexión, sesión y creación de tablas
- `services/` → lógica futura de negocio por participante

Regla importante:

> Los routers no deben llenarse de lógica pesada. La lógica de negocio futura va en `services/`.

## Documentación del proyecto

- `docs/PLAN_COMPLETO.md` → plan completo del proyecto pasado desde el Word
- `docs/ARQUITECTURA_Y_NORMAS.md` → contrato oficial de arquitectura y reglas de código
- `docs/diagrama.svg` → flujo visual general del sistema
- `docs/entidad-relacion.svg` → diagrama visual de base de datos
- `RESPONSABILIDADES_PARTICIPANTES.md` → qué hace cada participante
- `PLANTILLA_ENTREGA.md` → formato de devolución
- `prompt/` → prompts para que cada participante use IA sin salirse de su alcance
- `output/` → resultados JSON versionados de cada participante
- `tools/validate_output.py` → validador de JSON de output

## Estructura principal

```text
python_backend/
├── main.py
├── database/
│   ├── connection.py
│   └── schema.sql
├── models/
│   ├── base.py
│   ├── log_model.py
│   ├── post_model.py
│   └── topic_model.py
├── repositories/
│   ├── log_repository.py
│   ├── post_repository.py
│   └── topic_repository.py
├── routers/
│   ├── health_router.py
│   ├── logs_router.py
│   ├── posts_router.py
│   └── topics_router.py
├── schemas/
│   ├── log_schema.py
│   ├── post_schema.py
│   └── topic_schema.py
└── services/
    ├── ai/
    ├── duplicates/
    ├── instagram/
    ├── topic_selector/
    └── trends/
```

## Tablas SQLite

### `trending_topics`
Guarda temas trending base.

### `generated_posts`
Guarda posts generados asociados a un tema.

### `publication_logs`
Guarda logs de publicación futura.

## Cómo se crean las tablas hoy

- `python_backend/database/schema.sql` queda como referencia documental
- la creación real de tablas la hace SQLAlchemy desde `python_backend/models/`

## Endpoints base

### Salud del backend
- `GET /api/health`

### Temas trending
- `GET /api/topics`
- `GET /api/topics/{id}`
- `POST /api/topics`

### Posts generados
- `GET /api/posts`
- `GET /api/posts/{id}`
- `POST /api/posts`

### Logs de publicación
- `GET /api/logs`
- `GET /api/logs/{id}`
- `POST /api/logs`

## Ejemplos de body JSON

### Crear tema

```json
{
  "title": "Nuevo trend",
  "normalized_title": "nuevo trend",
  "source": "google trends",
  "score": 95,
  "used": 0
}
```

### Crear post

```json
{
  "topic_id": 1,
  "image_url": "https://mi-imagen.com/post.png",
  "caption": "Caption de prueba",
  "description": "Descripción base",
  "hashtags": "#trend #instagram",
  "status": "draft"
}
```

### Crear log

```json
{
  "post_id": 1,
  "platform": "instagram",
  "status": "pending",
  "response_json": "{}",
  "error_message": null
}
```

## Outputs JSON por participante

Los participantes 2 a 7 pueden dejar evidencia de su resultado en `output/`.

Formato de carpeta:

```text
output/participante-2/
output/participante-3/
output/participante-4/
output/participante-5/
output/participante-5/assets/
output/participante-6/
output/participante-7/
```

Cada archivo debe llamarse con este formato:

```text
{stage}_v1_{uuid-corto}.json
```

Ejemplo:

```text
trends_v1_550e8400.json
```

Cada JSON debe incluir:

```json
{
  "schema_version": "1.0",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "participant": "participante-2",
  "stage": "trends",
  "generated_at": "2026-05-31T12:00:00Z",
  "status": "success",
  "data": {},
  "errors": []
}
```

Para validarlo:

```bash
python tools/validate_output.py output/participante-2/trends_v1_550e8400.json
```

### Caso especial: imagen del Participante 5

Si el Participante 5 genera una imagen para Instagram:

- la imagen va como archivo dentro de `output/participante-5/assets/`
- el JSON `ai_v1_{uuid-corto}.json` debe referenciarla en `data.image_file`

Ejemplo:

```text
output/participante-5/
├── ai_v1_550e8400.json
└── assets/
    └── ai_v1_preview.png
```

## Comandos para levantar el proyecto

### Opción recomendada: Makefile simple

Desde la raíz real del proyecto:

```bash
cd /Users/luis/Desktop/PROYECTOS/trending
make dev
```

Eso inicializa SQLite si hace falta y levanta:

```text
API FastAPI: http://127.0.0.1:8000
UI web:      http://127.0.0.1:5173
```

Para ejecutar también el pipeline implementado hasta ahora —Fase 2, Fase 3 y Fase 4— antes de levantar la API:

```bash
make pipeline
```

Para preparar dependencias en una máquina nueva:

```bash
make install
```

Para revisar entorno sin levantar el servidor:

```bash
make check
```

Comandos útiles:

```bash
make help
make test
make lint
```

Si necesitás cambiar host o puerto, podés seguir usando el script base:

```bash
HOST=0.0.0.0 PORT=8010 FRONTEND_PORT=5174 ./run.sh --no-reload
make api
```

La UI estática actual vive en:

```text
frontend/index.html
```

### Bajar los servidores

```bash
Ctrl + C
```

### Estado del pipeline

Mientras el pipeline completo no esté terminado, el progreso se guarda en:

```text
output/pipeline_state.json
```

Comandos útiles:

```bash
make state            # ver estado actual
make state-bootstrap  # crear estado desde outputs actuales de Fase 2, 3 y 4
make state-reset      # eliminar progreso y empezar de nuevo
make state-delete     # borrar el archivo sin recrearlo
```

## Comandos útiles

### Ejecutar tests

```bash
pytest -q
```

### Revisar estilo con Ruff

```bash
ruff check python_backend tests
```

## Siguiente paso lógico

Cada participante debe trabajar solo en su carpeta asignada dentro de `python_backend/services/` o `frontend/`, usando su prompt correspondiente.
