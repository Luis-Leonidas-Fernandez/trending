# Arquitectura y normas del proyecto

Este archivo es el **contrato principal del proyecto**.

Todos los participantes y todas las inteligencias artificiales que ayuden en este trabajo deben respetar estas reglas.

Si un prompt, una sugerencia de IA o una decisión individual contradice este archivo, **gana este archivo**.

---

## 1. Arquitectura oficial

La arquitectura oficial del proyecto es:

- **Python 3.14.5**
- **FastAPI**
- **SQLite**
- **SQLAlchemy**
- **Pydantic**

La estructura principal del backend es esta:

```text
python_backend/
├── main.py
├── database/
├── models/
├── repositories/
├── routers/
├── schemas/
└── services/
```

### Responsabilidad por capa

- `routers/` → reciben requests HTTP y devuelven responses HTTP
- `schemas/` → validan datos de entrada y salida con Pydantic
- `models/` → definen tablas y relaciones con SQLAlchemy
- `repositories/` → leen y escriben datos en la base
- `services/` → contienen la lógica de negocio de cada participante
- `database/` → configura conexión, sesión y creación de tablas

---

## 2. Principio obligatorio: responsabilidad única

Cada archivo y cada capa debe tener una responsabilidad clara.

### Regla práctica

#### `routers/`
Sí deben:
- recibir parámetros
- llamar a la capa correspondiente
- devolver respuestas HTTP
- traducir errores a códigos HTTP cuando corresponda

No deben:
- meter lógica pesada de negocio
- escribir SQL
- decidir algoritmos complejos

#### `schemas/`
Sí deben:
- validar JSON
- definir estructura esperada

No deben:
- consultar base de datos
- ejecutar lógica de negocio

#### `models/`
Sí deben:
- definir entidades ORM
- definir relaciones

No deben:
- contener lógica de negocio
- devolver respuestas HTTP

#### `repositories/`
Sí deben:
- consultar, guardar, actualizar o eliminar datos
- hablar con SQLAlchemy y SQLite

No deben:
- contener lógica de negocio pesada
- decidir flujos funcionales del sistema
- implementar features de otros participantes

#### `services/`
Sí deben:
- contener la lógica de negocio del participante
- coordinar reglas, validaciones funcionales y decisiones del flujo

No deben:
- responder HTTP directamente
- mezclar responsabilidades de otros participantes

---

## 3. Reglas de implementación

### Reglas generales

- El código debe ser **simple, claro y entendible para principiantes**.
- Priorizar nombres descriptivos.
- Evitar abstracciones innecesarias.
- No crear capas extras “por las dudas”.
- No cambiar la arquitectura sin autorización explícita.
- No romper compatibilidad con Python `3.14.5`.

### Regla de simplicidad

Si hay dos opciones:

- una compleja y muy flexible
- otra simple y suficiente

se debe elegir la **simple y suficiente**.

---

## 4. Reglas para usar inteligencia artificial

Toda IA usada por participantes debe respetar estas reglas:

- No implementar partes de otros participantes.
- No modificar archivos fuera de la carpeta permitida.
- No eliminar archivos existentes fuera de la carpeta permitida.
- No reorganizar el proyecto completo.
- No cambiar dependencias si no es realmente necesario.
- Si cree que necesita tocar otra carpeta o archivo, debe **detenerse y avisar primero**.
- Debe respetar la arquitectura de este documento.
- Debe proponer código claro, corto y mantenible.

---

## 5. Límites por participante

### Participante 1
Puede trabajar en:

- `python_backend/main.py`
- `python_backend/database/`
- `python_backend/models/`
- `python_backend/repositories/`
- `python_backend/routers/`
- `python_backend/schemas/`

### Participante 2
Puede trabajar en:

- `python_backend/services/trends/`

### Participante 3
Puede trabajar en:

- `python_backend/services/duplicates/`

### Participante 4
Puede trabajar en:

- `python_backend/services/topic_selector/`

### Participante 5
Puede trabajar en:

- `python_backend/services/ai/`

### Participante 6
Puede trabajar en:

- `python_backend/services/instagram/`

### Participante 7
Puede trabajar en:

- `frontend/`

Si un participante cree que necesita tocar otra carpeta, debe:

1. detenerse
2. explicarlo
3. esperar aprobación antes de avanzar

### Excepción por entregable incompleto

Si uno o más participantes no logran terminar su entregable, un administrador del proyecto puede avanzar sobre el o los entregables faltantes.

Esta excepción debe cumplir estas condiciones:

- debe quedar claro qué participante no pudo completar su parte
- el administrador debe tocar solo los archivos necesarios para completar ese entregable
- el administrador debe respetar la arquitectura oficial y la responsabilidad única de las capas
- el cambio debe documentarse en la entrega o en el control de cambios
- no habilita a reorganizar el proyecto completo ni a implementar alcance no pedido

---

## 6. Qué NO se debe hacer

- No mezclar lógica de negocio en `routers/`.
- No meter acceso a base en `schemas/`.
- No meter respuestas HTTP en `repositories/`.
- No crear nuevas features completas fuera del alcance asignado.
- No borrar archivos del proyecto porque “parecen innecesarios”.
- No cambiar el stack tecnológico del proyecto.
- No cambiar nombres de carpetas principales sin autorización.

---

## 7. Criterios de entrega

Cada participante debe entregar:

- archivos modificados o creados
- explicación breve de qué hizo
- `PLANTILLA_ENTREGA.md` completada

La entrega debe permitir que el integrador entienda:

- qué cambió
- qué parte del flujo cubre
- qué falta
- si agregó dependencias

---

## 8. Outputs JSON versionados

Cada participante del 2 al 7 puede guardar evidencia de su resultado en `output/`.

La estructura permitida es:

```text
output/
├── participante-2/
├── participante-3/
├── participante-4/
├── participante-5/
│   └── assets/
├── participante-6/
└── participante-7/
```

Cada JSON debe estar versionado y validado.

Formato obligatorio:

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

Reglas:

- `schema_version` versiona el contrato del JSON.
- `run_id` identifica una corrida concreta y debe ser UUID válido.
- El nombre del archivo debe seguir el formato `{stage}_v1_{uuid-corto}.json`.
- El UUID corto del nombre debe coincidir con los primeros 8 caracteres de `run_id`.
- `data` debe existir siempre.
- `errors` debe existir siempre como lista.
- Los outputs se validan con `tools/validate_output.py`.
- Si el Participante 5 genera una imagen, debe guardarla como archivo dentro de `output/participante-5/assets/`.
- En ese caso, el JSON debe referenciarla desde `data.image_file`.
- `data.image_file` solo se admite para `participant = participante-5` y `stage = ai`.

Ejemplo:

```bash
python tools/validate_output.py output/participante-2/trends_v1_550e8400.json
```

Ejemplo para Participante 5:

```text
output/participante-5/
├── ai_v1_550e8400.json
└── assets/
    └── ai_v1_preview.png
```

```json
{
  "schema_version": "1.0",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "participant": "participante-5",
  "stage": "ai",
  "generated_at": "2026-05-31T12:00:00Z",
  "status": "success",
  "data": {
    "image_file": "output/participante-5/assets/ai_v1_preview.png",
    "caption": "Caption para Instagram",
    "description": "Descripción de la imagen generada",
    "hashtags": "#trend #instagram #viral"
  },
  "errors": []
}
```

## 9. Regla final

Este proyecto se construye por partes.

Por eso, la prioridad no es que cada participante haga “mucho”.

La prioridad es que cada participante haga **su parte**, sin romper la arquitectura del resto.

Es así de fácil.
