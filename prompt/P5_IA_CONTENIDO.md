# Prompt IA — Participante 5

Estoy trabajando en un proyecto llamado **Trending Instagram**.

Soy el **Participante 5** y solo debo trabajar la generación de contenido con IA en Python.

Antes de responder, debés respetar como contrato principal este archivo del proyecto:

- `docs/ARQUITECTURA_Y_NORMAS.md`

## Mi alcance

Debo trabajar únicamente:

- `python_backend/services/ai/`

## Lo que sí debo hacer

- preparar generación de imagen viral
- preparar generación de caption para Instagram
- preparar generación de hashtags
- preparar generación de descripción
- proponer contratos de entrada y salida claros
- mantener soluciones simples y entendibles para principiantes
- resolver solamente la parte del Participante 5
- dejar contratos claros para que otros participantes integren después
- respetar responsabilidad única:
  - `services/` contiene la lógica de esta parte
  - no debo mover lógica a `routers/`, `repositories/` o `schemas/`
- si hay varias alternativas, elegir la más simple y fácil de integrar
- si genero una salida de mi parte, debo guardarla como JSON versionado en `output/participante-5/`
- si genero una imagen, debo guardarla como archivo dentro de `output/participante-5/assets/`
- ese JSON debe usar `schema_version`, `run_id` UUID, `participant`, `stage`, `generated_at`, `status`, `data` y `errors`
- si hay imagen, el JSON debe referenciarla en `data.image_file`
- el nombre debe respetar el formato `ai_v1_{uuid-corto}.json`
- debo validar el JSON con `python tools/validate_output.py output/participante-5/ai_v1_{uuid-corto}.json`

## Lo que no debo hacer

- no debo modificar routers, repositories o schemas existentes
- no debo completar el flujo entero del sistema
- no debo implementar Google Trends
- no debo implementar validación de duplicados
- no debo implementar publicación en Instagram
- no debo modificar archivos fuera de la carpeta permitida
- no debo eliminar archivos existentes fuera de la carpeta permitida
- si pensás que hace falta tocar otro archivo, primero indicámelo y no avances
- no debés cambiar dependencias si no es realmente necesario

## Qué necesito de tu respuesta

Quiero que me digas:
1. qué archivo o archivos crear o modificar dentro de `python_backend/services/ai/`
2. el código necesario
3. una explicación breve y clara
4. además ayudame a completar `PLANTILLA_ENTREGA.md` con lo que hice
5. sin salirte del alcance del Participante 5
