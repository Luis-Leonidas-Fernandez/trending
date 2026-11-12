# Catálogo y Especificación de Endpoints REST

La API del **Sistema Trending para Instagram** está implementada con **FastAPI** y escucha por defecto en `http://127.0.0.1:8000`. La especificación interactiva Swagger UI se encuentra disponible en `http://127.0.0.1:8000/docs`.

Todos los endpoints REST utilizan prefijo `/api` (a excepción del root `/` y los assets estáticos `/assets/participante-5/`).

---

## 1. Endpoints Base y Salud

### `GET /`
* **Descripción:** Información general de la API y lista de endpoints disponibles.
* **Respuesta exitosa (200 OK):**
```json
{
  "success": true,
  "message": "API FastAPI del sistema trending de Instagram",
  "scope": "Backend Python paralelo",
  "availableEndpoints": [ ... ]
}
```

### `GET /api/health`
* **Descripción:** Endpoint de comprobación de salud y actividad del backend.
* **Respuesta exitosa (200 OK):**
```json
{
  "success": true,
  "message": "Servidor funcionando correctamente",
  "timestamp": "2026-07-28T14:00:00Z"
}
```

---

## 2. Orquestación del Pipeline (`/api/pipeline`)

### `GET /api/pipeline/state`
* **Descripción:** Devuelve el estado activo de la ejecución actual desde `output/pipeline_state.json`.
* **Respuesta exitosa (200 OK):**
```json
{
  "success": true,
  "data": {
    "state_version": "1.0",
    "run_id": "fcb7e995-156c-4861-bb2e-503a56658055",
    "status": "idle",
    "current_step": null,
    "selected_steps": ["descubrir", "filtrar", "elegir", "crear", "publicar", "medir"],
    "completed_steps": [],
    "next_step": "descubrir",
    "outputs": {
      "trends": "output/participante-2/trends_v1_02b0af11.json",
      "duplicates": null,
      "topic_selector": null,
      "ai": null,
      "instagram": null,
      "frontend": null
    },
    "errors": [],
    "created_at": "2026-07-28T14:10:00Z",
    "updated_at": "2026-07-28T14:10:00Z",
    "execution_mode": "full_pipeline"
  }
}
```

### `DELETE /api/pipeline/state`
* **Descripción:** Reinicia el estado activo del pipeline a modo `idle` con un nuevo `run_id` limpio. No borra las corridas históricas guardadas en SQLite.
* **Respuesta exitosa (200 OK):** Devuelve el nuevo estado reiniciado.

### `POST /api/pipeline/run`
* **Descripción:** Ejecuta una secuencia de pasos por lote en orden determinístico.
* **Cuerpo de la petición (JSON):**
```json
{
  "steps": ["descubrir", "filtrar", "elegir", "crear", "publicar", "medir"]
}
```
* **Respuesta exitosa (200 OK):** Devuelve el estado final del pipeline tras ejecutar la secuencia.

### `POST /api/pipeline/cancel`
* **Descripción:** Cancela cooperativamente la ejecución activa en vuelo, cerrando sockets HTTP pendientes hacia Spartan Provider.
* **Cuerpo de la petición (JSON):**
```json
{
  "reason": "Cancelado por el usuario desde el dashboard"
}
```
* **Respuesta exitosa (200 OK):**
```json
{
  "success": true,
  "message": "Pipeline cancelado",
  "closed_resources": 1,
  "data": { "status": "cancelled", ... }
}
```

### Pasos Individuales del Pipeline
* **`POST /api/pipeline/discover`:** Ejecuta exclusivamente la Fase 2 (Google Trends RSS).
* **`POST /api/pipeline/filter`:** Ejecuta la Fase 3 sobre el output de Fase 2.
* **`POST /api/pipeline/select`:** Ejecuta la Fase 4 sobre el output de Fase 3.
* **`POST /api/pipeline/create`:** Ejecuta la Fase 5 sobre el output de Fase 4.
* **`POST /api/pipeline/publish`:** Ejecuta la Fase 6A (persiste borrador).
* **`POST /api/pipeline/publish-simulated`:** Ejecuta la Fase 6B (simula publicación y marca `topic.used = 1`).

### Reutilización e Historial
* **`POST /api/pipeline/topics/{topic_id}/reuse`:** Prepara un tema histórico existente en SQLite para iniciar una rama de creación a partir de Fase 5 sin volver a descubrir ni filtrar.
* **`GET /api/pipeline/runs`:** Lista las corridas históricas correlacionadas desde la tabla `pipeline_runs` en SQLite. Soporta query params: `date_from`, `date_to`, `topic_id`, `topic`, `limit`.
* **`GET /api/pipeline/runs/{run_id}`:** Devuelve el detalle completo de una corrida específica.
* **`GET /api/pipeline/history`:** Endpoint de compatibilidad para consultas de historial agregadas.
* **`GET /api/pipeline/metrics/latest`:** Devuelve las métricas de calidad de la corrida activa.

---

## 3. Publicaciones (`/api/posts`)

### `GET /api/posts`
* **Descripción:** Lista todas las publicaciones registradas en la tabla `generated_posts`.
* **Respuesta exitosa (200 OK):** Lista de posts con sus relaciones de topic.

### `GET /api/posts/{id}`
* **Descripción:** Obtiene el detalle de un post específico por su ID entero.
* **Respuesta (404 Not Found):** Si el post no existe.

### `POST /api/posts`
* **Descripción:** Crea un post directamente en base de datos.
* **Cuerpo de la petición (JSON):**
```json
{
  "topic_id": 14,
  "caption": "Texto editorial...",
  "description": "Descripción...",
  "hashtags": "#trend #argentina",
  "image_url": "/assets/participante-5/ai_v1_68d67253.png",
  "status": "draft"
}
```

### `GET /api/posts/audit/latest`
* **Descripción:** Devuelve la vista consolidada de auditoría para la publicación generada en la corrida activa (incluye post, topic, imagen, caption y bitácoras).
* **Respuesta (404 Not Found):** Si no hay ninguna corrida activa con post generado.

### `POST /api/posts/{id}/publish-simulated`
* **Descripción:** Simula la publicación del post especificado, actualiza su estado a `published_simulated`, crea la bitácora en `publication_logs` y marca `topic.used = 1`.

---

## 4. Temas en Tendencia (`/api/topics`)

### `GET /api/topics`
* **Descripción:** Lista todos los temas registrados en la tabla `trending_topics`.
* **Respuesta exitosa (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": 14,
      "title": "Dólar hoy",
      "normalized_title": "dolar hoy",
      "source": "google_trends",
      "score": 100.0,
      "used": 1,
      "created_at": "2026-07-28 14:10:05"
    }
  ]
}
```

### `GET /api/topics/{id}`
* **Descripción:** Obtiene el detalle de un tema específico.

### `POST /api/topics`
* **Descripción:** Registra manualmente un nuevo tema en SQLite.
* **Cuerpo de la petición (JSON):**
```json
{
  "title": "Inteligencia Artificial",
  "normalized_title": "inteligencia artificial",
  "source": "manual",
  "score": 50.0,
  "used": 0
}
```

---

## 5. Bitácoras Técnicas (`/api/logs`)

### `GET /api/logs`
* **Descripción:** Lista todas las bitácoras registradas en `publication_logs`.
### `GET /api/logs/{id}`
* **Descripción:** Obtiene un log específico.
### `POST /api/logs`
* **Descripción:** Inserta un nuevo log técnico asociado a un post existente.

---

## 6. Proveedores de IA (`/api/ai`)

### `GET /api/ai/providers/status`
* **Descripción:** Consulta el estado de conectividad y autenticación de los proveedores de Spartan Provider (`codex`, `gemini`).
* **Respuesta exitosa (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "provider": "codex",
      "connected": true,
      "reconnect_required": false,
      "message": "Conectado",
      "reason": null
    }
  ]
}
```

### `POST /api/ai/providers/{provider}/connect`
* **Descripción:** Inicia el flujo de autenticación OAuth en Spartan Provider y devuelve la `authorization_url` para que el operador complete la vinculación en el navegador.

---

## 7. Assets Estáticos

### `GET /assets/participante-5/{filename}`
* **Descripción:** Sirve directamente las imágenes binarias PNG generadas por la Fase 5 y almacenadas en [`output/participante-5/assets/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-5/assets).
* **Content-Type:** `image/png`.
