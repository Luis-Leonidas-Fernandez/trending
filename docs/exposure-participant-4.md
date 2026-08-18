# Guía de exposición — Participante 4: Elegir tema

Objetivo: Su responsabilidad es recibir los candidatos filtrados por el Participante 3 y seleccionar el tema que va a continuar hacia la creación del post.

## Resumen 

“Mi participante se encarga de la fase Elegir. Recibe los temas ya filtrados, valida cuáles son elegibles y selecciona el primer tema válido que todavía no fue usado. No modifica la base de datos: sólo genera un output versionado con el tema elegido para que la fase Crear pueda generar contenido.”

## Qué problema resuelve

Después de descubrir y filtrar tendencias, todavía puede haber varios candidatos posibles. El Participante 4 transforma esa lista en una única decisión: cuál tema pasa a producción de contenido.

## Qué hace técnicamente

| Punto | Explicación para exposición |
|---|---|
| Entrada | Consume el output del Participante 3 (`stage: duplicates`). |
| Validación | Verifica que el input pertenezca a `participante-3` y no esté en error. |
| Estrategia | Usa `first_valid_unused`: elige el primer tema válido y no usado. |
| Elegibilidad | El tema debe tener `id` positivo, `title`, `normalized_title` y `used` en `0` o `false`. |
| Descartes | Registra temas inválidos o ya usados. |
| Pureza | No consulta SQLite ni marca el tema como usado. |
| Output | Guarda un JSON versionado en `output/participante-4/`. |

## Flujo de la fase

1. La fase **Filtrar** genera candidatos válidos.
2. El usuario ejecuta la card **Elegir** o el pipeline completo.
3. El backend toma el output de `participante-3`.
4. Se valida estructura, participante y stage.
5. Se revisa cada candidato en orden.
6. Se elige el primer tema válido y no usado.
7. Se genera el output de `participante-4` para que lo consuma **Crear**.

## Guia demo

- La card **Elegir** en el dashboard.
- Que se ejecuta después de **Filtrar**.
- El archivo generado en `output/participante-4/`.
- Que el JSON contiene `participant: participante-4` y `stage: topic_selector`.
- El campo `selected_topic`.
- La estrategia `first_valid_unused`.
- Los contadores `input`, `eligible` y `discarded`.

## Archivo principal que lo implementa

```text
/Users/luis/Desktop/PROYECTOS/trending/python_backend/services/topic_selector/topic_selector_service.py
```

Funciones importantes:

```text
process_duplicates_output()
select_topic()
_select_from_topics()
create_reuse_topic_output()
_load_phase_3_output()
```

## Endpoint relacionado

```http
POST /pipeline/select
```

Este endpoint ejecuta la fase `elegir` dentro del pipeline.

## Forma del output

Ejemplo simplificado:

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "participant": "participante-4",
  "stage": "topic_selector",
  "status": "success",
  "data": {
    "selected_topic": {
      "id": 46,
      "title": "Banco de la Nación Argentina",
      "normalized_title": "banco de la nacion argentina",
      "source": "google_trends",
      "score": 100,
      "used": 0
    },
    "strategy": "first_valid_unused",
    "counts": {
      "input": 5,
      "eligible": 3,
      "discarded": 2
    },
    "discarded": [],
    "source": {
      "participant": "participante-3",
      "stage": "duplicates",
      "status": "success"
    }
  },
  "errors": []
}
```

## Motivos de descarte

| Motivo | Qué significa |
|---|---|
| `invalid_topic` | El candidato no tiene estructura suficiente para elegirse. |
| `already_used` | El tema ya fue usado y no debe repetirse. |

## Qué significan los estados

| Estado | Qué significa |
|---|---|
| `success` | Se seleccionó un tema válido para Crear. |
| `draft` | La fase pudo ejecutarse, pero venía de fallback o no encontró tema seleccionable. |
| `error` | El input de Fase 3 era inválido o estaba en error. |

## Caso especial: reutilización manual desde Historial

Además de la selección automática, este participante también puede preparar un tema reutilizado desde Historial. En ese caso la estrategia cambia a:

```text
manual_history_reuse
```

Ese modo permite empezar desde **Crear** sin volver a ejecutar Descubrir, Filtrar y Elegir. Es importante porque evita que el tema reutilizado sea pisado por una nueva selección automática.

## Explicacion final

“Mi fase toma la lista limpia que dejó el Participante 3 y decide qué tema sigue hacia la creación del post.

La estrategia actual es simple y auditable: `first_valid_unused`. Eso significa que se respeta el orden recibido y se elige el primer tema que tenga estructura válida y que todavía no haya sido usado.

Esta fase no marca el tema como usado y no modifica la base de datos. Esa separación es importante: Elegir sólo toma la decisión; Publicar es quien finalmente confirma que el tema fue usado.

El resultado queda en un JSON versionado con `selected_topic`, estrategia, contadores y descartes. Así la fase Crear sabe exactamente sobre qué tema generar texto e imagen.”

## Cierre

“Mi participante convierte una lista de candidatos en una decisión clara y auditable: el tema exacto que va a transformarse en post.”

## Preguntas que pueden hacerle

### ¿Esta fase crea contenido?

No. Sólo elige el tema. La generación de texto e imagen pertenece al Participante 5.

### ¿Por qué elige el primero válido?

Porque el Participante 3 ya dejó una lista ordenada y filtrada. Esta estrategia es simple, predecible y fácil de auditar.

### ¿Marca el tema como usado?

No. Esa responsabilidad queda para una fase posterior, cuando el post ya fue publicado o simulado correctamente.

### ¿Qué pasa si no hay tema elegible?

El output queda en `draft`, con `selected_topic: null`, para mostrar que no hay una decisión segura para continuar.

### ¿Qué tiene que ver con el Historial?

Cuando se reutiliza un tema desde Historial, esta fase genera un output especial con estrategia `manual_history_reuse`, dejando preparado el pipeline para continuar desde Crear.

## Checklist 

- [ ] Ejecutar primero **Descubrir**.
- [ ] Ejecutar después **Filtrar**.
- [ ] Ejecutar **Elegir**.
- [ ] Abrir el output en `output/participante-4/`.
- [ ] Mostrar `selected_topic`.
- [ ] Mostrar `strategy: first_valid_unused`.
- [ ] Explicar que esta fase no modifica `used`.
- [ ] Aclarar que la siguiente fase, **Crear**, consume este tema seleccionado.
