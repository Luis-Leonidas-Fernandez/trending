# Guía de exposición — Participante 7: Medir / auditoría final

Objetivo: Su responsabilidad es cerrar el pipeline con una medición local: revisa el post, la publicación simulada, el log y el tema usado para calcular una calidad final auditable.

## Resumen 

“Mi participante se encarga de la fase Medir. No consulta métricas reales de Instagram. Lo que hace es auditar localmente que el post haya quedado correctamente publicado en modo simulado: que tenga imagen, caption, hashtags, log de publicación y tema marcado como usado. Con esos checks calcula un score de calidad.”

## Qué problema resuelve

Después de publicar o simular la publicación, necesitamos saber si el pipeline terminó bien. El Participante 7 convierte el estado final en evidencia medible: qué se cumplió, qué falta y qué score obtuvo la corrida.

## Qué hace técnicamente

| Punto | Explicación para exposición |
|---|---|
| Entrada | Consume el output del Participante 6 (`stage: instagram`). |
| Validación | Verifica que el output pertenezca a `participante-6` y no esté en error. |
| DB | Busca el post en SQLite por `post_id`. |
| Log | Busca logs de publicación del post. |
| Topic | Verifica si el tema fue marcado como usado. |
| Checks | Evalúa condiciones locales de calidad. |
| Score | Calcula porcentaje de checks cumplidos. |
| Output | Guarda JSON versionado en `output/participante-7/`. |

## Flujo de la fase

1. La fase **Publicar** o **Publicar simulado** genera output de `participante-6`.
2. El usuario ejecuta la card **Medir** o el pipeline completo.
3. El backend toma el output de `participante-6`.
4. Se valida que el input sea correcto.
5. Se busca el post persistido en SQLite.
6. Se busca el log de publicación local.
7. Se verifica el estado del topic.
8. Se calculan checks, warnings y score.
9. Se genera el output final de `participante-7`.

## Guia demo

- La card **Medir** en el dashboard.
- Que se ejecuta después de **Publicar**.
- El archivo generado en `output/participante-7/`.
- Que el JSON contiene `participant: participante-7` y `stage: metrics`.
- El campo `score`.
- El objeto `checks`.
- La lista `warnings` si algo no se cumplió.
- El estado final `success` si el score es 100.

## Archivo principal que lo implementa

```text
/Users/Name/Desktop/PROYECTOS/trending/python_backend/services/metrics/metrics_service.py
```

Funciones importantes:

```text
process_instagram_output()
_build_metrics()
_warnings_from_checks()
_asset_exists()
_load_instagram_output()
```

## Endpoints relacionados

```http
POST /pipeline/run
GET /pipeline/metrics/latest
```

Cuando se ejecuta el step `medir`, el router llama a `process_instagram_output()`.

## Checks que calcula

| Check | Qué verifica |
|---|---|
| `post_published_simulated` | El post quedó en estado `published_simulated`. |
| `has_image` | El post tiene `image_url`. |
| `image_file_exists` | El archivo de imagen existe en disco. |
| `has_caption` | El post tiene caption. |
| `has_hashtags` | El post tiene hashtags. |
| `has_publication_log` | Existe log de publicación. |
| `log_published_simulated` | El log registra estado `published_simulated`. |
| `topic_marked_used` | El tema quedó marcado como usado. |

## Cómo calcula el score

El score es un porcentaje simple:

```text
checks cumplidos / total de checks * 100
```

Si todos los checks pasan, el score es `100` y el output queda en `success`. Si falta algo, queda en `draft` y se generan warnings.

## Forma del output

Ejemplo simplificado:

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "participant": "participante-7",
  "stage": "metrics",
  "status": "success",
  "data": {
    "post_id": 24,
    "topic_id": 46,
    "topic_title": "Banco de la Nación Argentina",
    "checks": {
      "post_published_simulated": true,
      "has_image": true,
      "image_file_exists": true,
      "has_caption": true,
      "has_hashtags": true,
      "has_publication_log": true,
      "log_published_simulated": true,
      "topic_marked_used": true
    },
    "score": 100,
    "warnings": [],
    "ready_for_real_publication": false,
    "external_metrics_available": false,
    "next_action": "Revisión humana antes de integrar publicación real con Instagram."
  },
  "errors": []
}
```

## Qué significan los estados

| Estado | Qué significa |
|---|---|
| `success` | Todos los checks pasaron y el score es 100. |
| `draft` | La medición corrió, pero faltan condiciones para cierre perfecto. |
| `error` | No se pudo medir porque el input o los datos base eran inválidos. |

## Qué NO hace esta fase

- No consulta Instagram real.
- No calcula likes, comentarios ni alcance real.
- No publica contenido.
- No modifica el post.
- No decide un nuevo tema.

Su objetivo es auditoría local del pipeline, no analítica externa.

## Explicacion final

“Mi fase cierra el pipeline. No mide métricas reales de Instagram, porque en esta versión no estamos publicando afuera. Lo que hago es una auditoría local para verificar que todo el flujo terminó correctamente.

Tomo el output del Participante 6, busco el post en la base de datos, reviso si tiene imagen, caption y hashtags, verifico si existe un log de publicación simulada y si el tema quedó marcado como usado.

Cada condición es un check. Con esos checks calculo un score. Si todo está correcto, el score es 100 y la fase queda en success. Si falta algo, la fase queda en draft y devuelve warnings para explicar qué está incompleto.

Esto permite que el dashboard muestre un cierre claro de la corrida y que el historial guarde evidencia de calidad.”

## Cierre

“Mi participante no mide Instagram real: mide si nuestro pipeline terminó correctamente y deja evidencia auditable de calidad.”

## Preguntas 

### ¿Esta fase mide likes o comentarios?

No. Todavía no hay integración con métricas reales de Instagram. Mide calidad local del pipeline.

### ¿Por qué el score puede ser menor a 100?

Porque falta algún check: imagen, caption, hashtags, log, estado simulado o tema marcado como usado.

### ¿Esta fase modifica datos?

No. Sólo lee post, log y topic para construir la auditoría final.

### ¿Por qué es importante el log?

Porque demuestra que la publicación simulada ocurrió y no estamos inventando un estado final.

### ¿Qué pasa si Medir se ejecuta sobre un draft?

El score baja y aparecen warnings, porque el post todavía no cumple todas las condiciones de cierre.

## Checklist antes de exponer

- [ ] Ejecutar antes **Descubrir**, **Filtrar**, **Elegir**, **Crear** y **Publicar**.
- [ ] Asegurarse de que haya publicación simulada antes de medir.
- [ ] Ejecutar **Medir**.
- [ ] Abrir el output en `output/participante-7/`.
- [ ] Mostrar `score`.
- [ ] Mostrar `checks`.
- [ ] Explicar algún warning si el score no es 100.
- [ ] Aclarar que no son métricas reales de Instagram.
