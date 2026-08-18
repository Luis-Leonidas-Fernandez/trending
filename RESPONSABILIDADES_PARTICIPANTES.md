# Responsabilidades de participantes

Este archivo explica **qué debe hacer cada participante** y **qué carpeta puede tocar**.

## Regla general
- Cada participante trabaja solo en su parte.
- No debe modificar carpetas ajenas.
- Cuando termine, debe devolver sus archivos junto con `PLANTILLA_ENTREGA.md` completada.
- El backend oficial para seguir trabajando es `python_backend/`.
- Si genera una salida de su parte, debe guardarla como JSON versionado y validado dentro de `output/`.

---

## Participante 1 — Backend base Python ✅ COMPLETADO
### Debe trabajar en
- `python_backend/main.py`
- `python_backend/database/`
- `python_backend/models/`
- `python_backend/repositories/`
- `python_backend/routers/`
- `python_backend/schemas/`

### Hace
- base del backend
- FastAPI
- SQLite
- SQLAlchemy
- routers
- models
- repositorios
- schemas Pydantic
- validaciones iniciales

### Estado
- ya implementado
- ya validado
- no debe reasignarse salvo corrección puntual autorizada

---

## Participante 2 — Google Trends y normalización
### Debe trabajar en
- `python_backend/services/trends/`
- `output/participante-2/`

### Hace
- búsqueda de tendencias
- transformación de datos a JSON uniforme
- output JSON versionado si genera una salida

---

## Participante 3 — Validación de duplicados
### Debe trabajar en
- `python_backend/services/duplicates/`
- `output/participante-3/`

### Hace
- detectar temas repetidos
- normalizar títulos
- ayudar a guardar solo temas válidos
- output JSON versionado si genera una salida

---

## Participante 4 — Selector automático de tema
### Debe trabajar en
- `python_backend/services/topic_selector/`
- `output/participante-4/`

### Hace
- elegir automáticamente el tema válido a usar
- output JSON versionado si genera una salida

---

## Participante 5 — Generación con IA
### Debe trabajar en
- `python_backend/services/ai/`
- `output/participante-5/`
- `output/participante-5/assets/`

### Hace
- imagen
- caption
- hashtags
- descripción
- output JSON versionado si genera una salida
- guardar la imagen física dentro de `output/participante-5/assets/` si la genera

---

## Participante 6 — Publicación en Instagram
### Debe trabajar en
- `python_backend/services/instagram/`
- `output/participante-6/`

### Hace
- lógica de publicación
- guardado de logs técnicos
- output JSON versionado si genera una salida

---

## Participante 7 — Frontend
### Debe trabajar en
- `frontend/`
- `output/participante-7/`

### Hace
- dashboard
- vista de tendencias
- vista de posts
- estado de publicaciones
- output JSON versionado si genera una salida
