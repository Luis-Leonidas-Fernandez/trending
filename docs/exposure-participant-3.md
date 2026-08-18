# Guía de exposición — Participante 3: Filtrar duplicados

Objetivos: recibir las tendencias descubiertas por el Participante 2, descartar temas inválidos o repetidos, persistir temas nuevos en SQLite y entregar un JSON auditable para que el Participante 4 pueda elegir el mejor tema.

## Resumen

“Mi participante se encarga de la fase Filtrar. Recibe las tendencias descubiertas, valida que tengan título útil, elimina duplicados dentro del mismo input y contra la base de datos, guarda los temas nuevos y deja un output versionado para la fase Elegir.”

## Qué problema resuelve

Google Trends puede traer temas repetidos, títulos inválidos o temas que la app ya conoce. Si pasamos todo eso directo a la selección, el pipeline puede crear posts repetidos o trabajar con datos sucios. En esta seccion se produce el filtro de calidad antes de elegir el tema final.

## Qué hace técnicamente

| Punto | Explicación para exposición |
|---|---|
| Entrada | Consume el output del Participante 2 (`stage: trends`). |
| Validación | Verifica que el input sea un JSON válido y pertenezca a `participante-2`. |
| Normalización | Usa `normalized_title` para comparar temas de forma consistente. |
| Duplicados internos | Descarta temas repetidos dentro del mismo lote recibido. |
| Duplicados en DB | Compara contra `trending_topics` en SQLite. |
| Persistencia | Guarda en DB sólo los temas nuevos. |
| Reutilización | Si un tema ya existe pero no fue usado, puede reutilizarlo como candidato. |
| Output | Guarda un JSON versionado en `output/participante-3/`. |

## Flujo de la fase

1. La fase **Descubrir** genera un archivo de tendencias.
2. El usuario ejecuta la card **Filtrar** o el pipeline completo.
3. El backend toma el output de `participante-2`.
4. Se validan estructura, participante y stage.
5. Se filtran títulos inválidos y duplicados.
6. Se guardan temas nuevos en SQLite.
7. Se genera el output de `participante-3` para que lo consuma **Elegir**.

## Qué debe mostrar en la demo

- La card **Filtrar** en el dashboard.
- Que se ejecuta después de **Descubrir**.
- El archivo generado en `output/participante-3/`.
- Que el JSON contiene `participant: participante-3` y `stage: duplicates`.
- Los contadores: `input`, `saved`, `reused`, `duplicates`, `invalid`, `discarded`.
- La lista `discarded`, si hubo temas descartados.

## Archivo principal que lo implementa

```text
/Users/Name/Desktop/PROYECTOS/trending/python_backend/services/duplicates/duplicates_service.py
```

Funciones importantes:

```text
process_trends_output()
filter_new_topics()
_filter_topics()
_persist_topics()
_load_phase_2_output()
```

## Endpoint relacionado

```http
POST /pipeline/filter
```

Este endpoint ejecuta la fase `filtrar` dentro del pipeline.

## Forma del output

Ejemplo simplificado:

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "participant": "participante-3",
  "stage": "duplicates",
  "status": "success",
  "data": {
    "items": [
      {
        "id": 12,
        "title": "Banco de la Nación Argentina",
        "normalized_title": "banco de la nacion argentina",
        "source": "google_trends",
        "score": 100,
        "used": 0
      }
    ],
    "counts": {
      "input": 10,
      "saved": 4,
      "reused": 1,
      "duplicates": 3,
      "invalid": 0,
      "discarded": 3
    },
    "discarded": [],
    "source": {
      "participant": "participante-2",
      "stage": "trends",
      "status": "success"
    }
  },
  "errors": []
}
```

## Motivos de descarte

| Motivo | Qué significa |
|---|---|
| `invalid_title` | El tema no tiene un título válido. |
| `duplicate_in_input` | El tema aparece repetido dentro del mismo lote. |
| `duplicate_in_database` | El tema ya existe en la base de datos. |
| `already_used_in_database` | El tema ya existe y ya fue usado antes. |

## Qué significan los estados

| Estado | Qué significa |
|---|---|
| `success` | Hay candidatos válidos para la fase Elegir. |
| `draft` | La fase pudo ejecutarse, pero viene de fallback o no hay candidatos suficientes. |
| `error` | El input no era válido o hubo un problema de persistencia. |

## Explicacion

“Mi fase recibe las tendencias que descubrió el Participante 2. El objetivo no es elegir todavía el mejor tema, sino limpiar la lista para que la selección trabaje con datos confiables.

Primero valido que el archivo de entrada sea realmente del Participante 2 y que pertenezca al stage `trends`. Después reviso cada tema: limpio el título, normalizo el nombre y descarto entradas inválidas o repetidas.

También comparo contra la base de datos. Si el tema es nuevo, lo guardo en SQLite. Si ya existe pero todavía no fue usado, puede volver como candidato reutilizable. Si ya fue usado, lo descarto para evitar repetir publicaciones.

Al final genero un JSON versionado con los temas que pasan el filtro, los contadores de lo que ocurrió y el detalle de descartes. Esto permite auditar por qué un tema siguió adelante o por qué quedó afuera.”

## Cierre

“Mi participante protege al pipeline de trabajar con datos repetidos o sucios: convierte una lista cruda de tendencias en candidatos confiables para elegir.”

## Preguntas que pueden hacerle

### ¿Esta fase elige el mejor tema?

No. Esta fase sólo filtra y persiste candidatos. La elección final pertenece al Participante 4.

### ¿Cómo sabe si un tema está repetido?

Compara por `normalized_title`, que permite evitar diferencias por mayúsculas, acentos o formato.

### ¿Qué pasa si un tema ya existe pero no fue usado?

Puede reutilizarse como candidato. Eso evita perder un tema válido que ya estaba en la base pero todavía no llegó a publicarse.

### ¿Por qué guarda temas en SQLite?

Porque la app necesita memoria de temas anteriores para evitar repetir publicaciones y para alimentar el historial del pipeline.

### ¿Qué pasa si no queda ningún candidato?

La fase queda en `draft`, porque técnicamente pudo ejecutarse, pero no produjo candidatos útiles para continuar con seguridad.

## Checklist 

- [ ] Ejecutar primero **Descubrir**.
- [ ] Ejecutar después **Filtrar**.
- [ ] Abrir el output en `output/participante-3/`.
- [ ] Mostrar `participant: participante-3` y `stage: duplicates`.
- [ ] Mostrar `counts` para explicar cuántos entraron, cuántos se guardaron y cuántos se descartaron.
- [ ] Explicar al menos un motivo de descarte.
- [ ] Aclarar que la fase siguiente, **Elegir**, consume este resultado.
