# Prompt IA — Participante 7

Estoy trabajando en un proyecto llamado **Trending Instagram**.

Soy el **Participante 7** y solo debo trabajar el frontend del proyecto.

Antes de responder, debés respetar como contrato principal este archivo del proyecto:

- `docs/ARQUITECTURA_Y_NORMAS.md`

## Mi alcance

Debo trabajar únicamente:

- `frontend/`

## Lo que sí debo hacer

- crear dashboard
- mostrar tendencias consumiendo la API FastAPI
- mostrar posts generados
- mostrar estado de publicaciones
- crear configuración visual
- proponer una solución simple y entendible para principiantes
- resolver solamente la parte del Participante 7
- dejar contratos claros para que el frontend pueda integrarse bien con el backend
- respetar responsabilidad única:
  - `frontend/` contiene solo la lógica visual y de consumo de API
  - no debo mover lógica de negocio del backend al frontend
- si hay varias alternativas, elegir la más simple y fácil de integrar
- si genero una salida de mi parte, debo guardarla como JSON versionado en `output/participante-7/`
- ese JSON debe usar `schema_version`, `run_id` UUID, `participant`, `stage`, `generated_at`, `status`, `data` y `errors`
- el nombre debe respetar el formato `frontend_v1_{uuid-corto}.json`
- debo validar el JSON con `python tools/validate_output.py output/participante-7/frontend_v1_{uuid-corto}.json`

## Lo que no debo hacer

- no debo modificar archivos del backend Python
- no debo completar el flujo entero del sistema
- no debo modificar archivos fuera de la carpeta permitida
- no debo eliminar archivos existentes fuera de la carpeta permitida
- si pensás que hace falta tocar otro archivo, primero indicámelo y no avances
- no debés reorganizar todo el proyecto
- no debés cambiar dependencias si no es realmente necesario

## Qué necesito de tu respuesta

Quiero que me digas:
1. qué archivo o archivos crear o modificar dentro de `frontend/`
2. el código necesario
3. una explicación breve y clara
4. además ayudame a completar `PLANTILLA_ENTREGA.md` con lo que hice
5. sin salirte del alcance del Participante 7
