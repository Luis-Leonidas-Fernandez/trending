# Guía de exposición — Participante 6: Publicar / preparar publicación

Objetivo: Su responsabilidad es tomar el contenido generado por el Participante 5, persistirlo como post en SQLite y preparar la publicación para auditoría o simulación.

## Resumen 

“Mi participante se encarga de la fase Publicar. Recibe el contenido creado por IA, lo guarda como post en la base de datos y genera un output auditable. En esta versión no publica en Instagram real: primero deja el post como draft y luego puede cerrar una publicación simulada, crear un log y marcar el tema como usado.”

## Qué problema resuelve

El Participante 5 genera contenido, pero todavía no existe un post persistido. El Participante 6 convierte ese output de IA en un registro real de la app, con estado, imagen, caption, hashtags y trazabilidad para auditoría.

## Qué hace técnicamente

| Punto | Explicación para exposición |
|---|---|
| Entrada | Consume el output del Participante 5 (`stage: ai`). |
| Validación | Verifica que el input pertenezca a `participante-5` y no esté en error. |
| Persistencia | Crea un post en SQLite usando caption, description, hashtags e image_file. |
| Estado inicial | Guarda el post como `draft`. |
| Publicación externa | No llama a Instagram real en esta versión. |
| Simulación | Puede finalizar una publicación simulada local. |
| Auditoría | Crea un log de publicación simulada. |
| Tema usado | Marca el topic como usado sólo al simular publicación correctamente. |
| Output | Guarda JSON versionado en `output/participante-6/`. |

## Flujo de la fase

1. La fase **Crear** genera texto e imagen.
2. El usuario ejecuta la card **Publicar** o el pipeline completo.
3. El backend toma el output de `participante-5`.
4. Se valida que el output sea de IA y tenga datos mínimos.
5. Se crea un post en SQLite con estado `draft`.
6. Se genera un output de `participante-6` con `ready_to_publish: false` y `publication_skipped: true`.
7. Si se ejecuta publicación simulada, se crea un log, se actualiza el post a `published_simulated` y se marca el tema como usado.

## Guia demo

- La card **Publicar** en el dashboard.
- Que se ejecuta después de **Crear**.
- El archivo generado en `output/participante-6/`.
- Que el JSON contiene `participant: participante-6` y `stage: instagram`.
- El objeto `post` con `id`, `caption`, `hashtags`, `image_url` y `status`.
- El campo `publication_skipped: true` cuando sólo quedó preparado.
- El resultado de publicación simulada con `published_simulated`, `publication_log` y `topic_marked_used: true`.

## Archivo principal que lo implementa

```text
/Users/Name/Desktop/PROYECTOS/trending/python_backend/services/instagram/instagram_service.py
```

Funciones importantes:

```text
process_ai_output()
publish_post()
simulate_publication()
process_simulated_publication()
build_audit_view()
_post_payload_from_ai_output()
```

## Endpoints relacionados

```http
POST /pipeline/publish
POST /pipeline/publish-simulated
```

`/pipeline/publish` persiste el post como draft.  
`/pipeline/publish-simulated` cierra la publicación simulada para auditoría.

## Forma del output inicial

Ejemplo simplificado después de **Publicar**:

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "participant": "participante-6",
  "stage": "instagram",
  "status": "success",
  "data": {
    "post": {
      "id": 24,
      "topic_id": 46,
      "image_url": "output/participante-5/assets/ai_v1_xxxxxxxx.png",
      "caption": "Párrafo 1...

Párrafo 2...

Párrafo 3...",
      "description": "Descripción interna del post.",
      "hashtags": "#BancoNacion #BNA #Finanzas",
      "status": "draft"
    },
    "post_id": 24,
    "platform": "instagram",
    "ready_to_publish": false,
    "publication_skipped": true,
    "topic_marked_used": false
  },
  "errors": []
}
```

## Forma del output simulado

Después de **Publicar simulado**, el output incluye:

```json
{
  "status": "success",
  "data": {
    "post_id": 24,
    "post": {
      "status": "published_simulated"
    },
    "publication_log": {
      "platform": "instagram",
      "status": "published_simulated"
    },
    "simulated": true,
    "external_publication": false,
    "topic_marked_used": true,
    "ready_to_publish": true,
    "publication_skipped": false
  }
}
```

## Qué significan los estados

| Estado | Qué significa |
|---|---|
| `success` | El post se persistió o la simulación cerró correctamente. |
| `draft` | La fase heredó fallback desde IA o el post quedó preparado sin cierre final. |
| `error` | El input era inválido o faltaban datos obligatorios. |

## Validaciones importantes

Para simular publicación, el post debe tener:

- `id` válido,
- estado `draft` o `published_simulated`,
- `caption`,
- `image_url`.

Si falta caption o imagen, la publicación simulada falla. Esto evita marcar como publicado un post incompleto.

## Cuidado con los párrafos del caption

Esta fase preserva saltos de línea del caption con `

`. Eso es importante porque si se colapsa el texto, Instagram recibiría un bloque ilegible. Por eso el caption usa limpieza multilinea en vez de una limpieza que reemplace todo whitespace por espacios.

## Explicacion final

“Mi fase recibe el contenido que generó la IA y lo convierte en un post persistido dentro de la aplicación.

Primero valido que el input venga del Participante 5. Después construyo el payload del post con topic, imagen, caption, descripción y hashtags. Ese post se guarda en SQLite como draft.

En esta versión no publicamos en Instagram real. Lo que hacemos es preparar el post y dejar evidencia auditable. Luego existe una publicación simulada que actualiza el estado a `published_simulated`, crea un log y marca el tema como usado.

Eso es importante porque no queremos marcar un tema como usado apenas se crea el contenido. Lo marcamos recién cuando la publicación simulada termina bien.”

## Cierre

“Mi participante convierte el contenido generado por IA en un post persistido y auditable, listo para cerrar una publicación simulada sin tocar Instagram real.”

## Preguntas 

### ¿Esta fase publica realmente en Instagram?

No. En esta versión la publicación real está omitida. Se trabaja con preparación y simulación local.

### ¿Cuándo se marca el tema como usado?

Sólo después de una publicación simulada exitosa, no cuando el post queda en draft.

### ¿Por qué se crea un log?

Para auditar que la publicación simulada ocurrió, con plataforma, estado y respuesta registrada.

### ¿Qué pasa si falta imagen?

La publicación simulada falla, porque no se debe cerrar como publicado un post incompleto.

### ¿Qué consume la fase siguiente?

El Participante 7 consume el output de `participante-6` para medir calidad y estado final.

## Checklist

- [ ] Ejecutar antes **Descubrir**, **Filtrar**, **Elegir** y **Crear**.
- [ ] Ejecutar **Publicar**.
- [ ] Abrir el output en `output/participante-6/`.
- [ ] Mostrar el objeto `post` y su estado `draft`.
- [ ] Ejecutar o mostrar publicación simulada.
- [ ] Mostrar `publication_log`.
- [ ] Mostrar `topic_marked_used: true` después de la simulación.
- [ ] Aclarar que Instagram real no se toca en esta versión.
