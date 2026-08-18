# Guía de exposición — Participante 2: Descubrir tendencias

Esta guía ayuda al Participante 2 a explicar su parte dentro de la app Trending. Su responsabilidad es iniciar el pipeline: buscar tendencias, normalizarlas y entregar un archivo versionado para que las fases siguientes trabajen con datos consistentes.

## Resumen para decir en 20 segundos

“Mi participante se encarga de la fase Descubrir. Consulta Google Trends para Argentina, transforma las tendencias en una estructura común y guarda un output versionado. Si Google Trends falla, la fase no rompe el pipeline: genera un fallback controlado marcado como draft para que el resto del sistema pueda seguir validándose.”

## Qué problema resuelve

Antes de crear un post, la app necesita saber de qué tema hablar. Detecta posibles temas en tendencia y los deja listos para que después se puedan filtrar, elegir, convertir en contenido y medir.

## Qué hace técnicamente

| Punto | Explicación para exposición |
|---|---|
| Fuente principal | Consulta el RSS de Google Trends. |
| País configurado | Usa Argentina por defecto (`AR`). |
| Límite | Devuelve hasta 10 tendencias. |
| Normalización | Limpia títulos, genera `normalized_title`, categoría, fecha y score. |
| Output | Guarda un JSON versionado en `output/participante-2/`. |
| Fallback | Si Google Trends falla, devuelve tendencias controladas con `source = fallback`. |

## Flujo de la fase

1. El usuario ejecuta la card **Descubrir** o el pipeline completo.
2. Backend llama al endpoint de pipeline para la fase `descubrir`.
3. El servicio consulta Google Trends.
4. Se parsea el RSS y se normalizan los resultados.
5. Se escribe un archivo JSON versionado.
6. La siguiente fase, **Filtrar**, consume ese output.

## Qué debe mostrar en la demo

- La card **Descubrir** en el dashboard.
- Que al correrla se genera un resultado nuevo.
- El archivo dentro de `output/participante-2/`.
- Que el JSON contiene `participant: participante-2` y `stage: trends`.
- Que el estado puede ser `success` si Google Trends respondió o `draft` si se usó fallback.

## Archivo principal que lo implementa

```text
/Users/luis/Desktop/PROYECTOS/trending/python_backend/services/trends/trends_service.py
```

Funciones importantes:

```text
collect_trending_topics()
save_trends_output()
_parse_google_trends_rss()
_fetch_google_trends_rss()
```

## Endpoint relacionado

```http
POST /pipeline/discover
```

Este endpoint ejecuta la fase `descubrir` dentro del pipeline.

## Forma del output

Ejemplo simplificado:

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "participant": "participante-2",
  "stage": "trends",
  "status": "success",
  "data": {
    "country": "AR",
    "items": [
      {
        "title": "Banco de la Nación Argentina",
        "normalized_title": "banco de la nacion argentina",
        "source": "google_trends",
        "category": "general",
        "date": "...",
        "score": 100
      }
    ],
    "used_fallback": false
  },
  "errors": []
}
```

## Qué significan los estados

| Estado | Qué significa |
|---|---|
| `success` | Google Trends respondió y se generaron tendencias reales. |
| `draft` | Google Trends falló o no devolvió datos útiles; se usó fallback. |
| `error` | La fase no pudo producir un output válido. |

## Guion sugerido para exponer

“Esta es la primera fase del pipeline. Su objetivo es descubrir temas posibles para convertirlos después en contenido.

El servicio consulta Google Trends para Argentina usando el RSS público. Cada resultado se limpia y se transforma en un formato común: título, título normalizado, fuente, categoría, fecha y score.

Lo importante es que esta fase no le pasa datos sueltos al resto del sistema. Genera un JSON versionado con `run_id`, participante, stage, estado, data y errores. Eso permite que las fases siguientes sepan exactamente qué entrada están consumiendo.

También tiene una protección: si Google Trends falla por timeout, error HTTP, XML inválido o lista vacía, no rompe todo el pipeline. En ese caso genera un fallback controlado y marca el output como draft. Así podemos seguir probando el flujo completo sin depender siempre de una fuente externa.”

## Cierre

“Mi participante convierte una señal externa e inestable, como Google Trends, en una entrada controlada, versionada y segura para el resto del pipeline.”

## Preguntas que pueden hacerle

### ¿Qué pasa si Google Trends falla?

La fase usa un fallback determinístico. El pipeline puede seguir, pero el output queda marcado como `draft` y `used_fallback: true`.

### ¿Por qué se normaliza el título?

Porque las fases siguientes necesitan comparar temas, detectar duplicados y reutilizar nombres sin depender de mayúsculas, acentos o formatos distintos.

### ¿Por qué se guarda un JSON?

Porque cada participante trabaja con contratos claros. El JSON versionado permite auditar qué produjo cada fase y repetir o depurar el pipeline sin mezclar estados.

### ¿Esta fase crea el post?

No. Sólo descubre candidatos. Crear texto, imagen, publicación y medición pertenece a participantes posteriores.

## Checklist antes de exponer

- [ ] Tener el backend levantado.
- [ ] Abrir el dashboard.
- [ ] Ejecutar sólo la card **Descubrir**.
- [ ] Confirmar que se generó un archivo en `output/participante-2/`.
- [ ] Mostrar que el JSON tiene `participant: participante-2` y `stage: trends`.
- [ ] Explicar qué significa `success`, `draft` y `used_fallback`.
