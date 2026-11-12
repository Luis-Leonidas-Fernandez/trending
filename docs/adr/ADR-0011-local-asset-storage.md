# ADR-0011: Almacenamiento local y exposición estática de imágenes en `output/.../assets/`

## Estado
Accepted

## Contexto
En la Fase 5B (acoplada a Spartan Provider), el sistema no solo genera textos para el post sino también imágenes virales llamando al endpoint `/v1/images/generations`. Las imágenes generadas por modelos de difusión (DALL-E / Imagen) se reciben codificadas en Base64 (`b64_json`). Si se guardaran directamente en la base de datos SQLite como cadenas Base64 o BLOBs pesados, la base crecería descontroladamente y ralentizaría las consultas. Por otra parte, las URLs remotas de CDNs temporales expiran a las pocas horas.

## Decisión
1. Almacenar los bytes binarios de las imágenes generadas como archivos físicos en formato PNG dentro del directorio [`output/participante-5/assets/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-5/assets), utilizando la convención determinística `ai_v1_{uuid-corto}.png` ([`python_backend/services/ai/ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py#L387-L403)).
2. El JSON de salida de Fase 5 debe referenciar la ruta relativa del archivo en el campo `data.image_file` (ej. `"output/participante-5/assets/ai_v1_02a99c68.png"`).
3. Montar dicho directorio en FastAPI como archivos estáticos en [`main.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py#L33-L35) bajo la ruta pública:
   `/assets/participante-5`
4. Ajustar el validador [`tools/validate_output.py`](file:///Users/luis/desktop/PROYECTOS/trending/tools/validate_output.py#L58-L70) para comprobar que cuando `participant == "participante-5"` y `stage == "ai"`, el archivo referenciado en `image_file` exista físicamente en disco y tenga extensión válida (`.png`, `.jpg`, `.webp`).

## Justificación
- **Persistencia duradera:** Los archivos físicos no expiran como los enlaces firmados de S3/Azure, garantizando que el historial visual del proyecto se preserve indefinidamente.
- **Base de datos ágil:** La tabla `generated_posts` en SQLite solo guarda la ruta o URL pública en su columna `image_url`, manteniendo la base ligera y rápida.
- **Acceso web directo:** Montar `StaticFiles` permite al frontend y a herramientas externas previsualizar la imagen generada directamente mediante una etiqueta `<img src="/assets/participante-5/ai_v1_...png">`.

## Alternativas consideradas
- **Guardar imágenes en BLOB dentro de SQLite:** Descartada por saturar el archivo `.sqlite` con megabytes binarios y degradar el rendimiento de lectura.
- **Dependencia de almacenamiento S3 / Cloud Storage:** Descartada para evitar requerir cuentas de AWS o configuración de buckets en entornos de desarrollo local.

## Consecuencias positivas
- Previsualización instantánea en el dashboard web.
- Aislamiento limpio entre metadatos (JSON) y artefactos binarios pesados (PNG).
- Respaldo local de las imágenes generadas.

## Consecuencias negativas
- El directorio `output/participante-5/assets/` acumula archivos binarios en el disco local que deben ser ignorados en Git o gestionados con políticas de retención.

## Componentes afectados
- [`python_backend/services/ai/ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py): Funciones `_write_image_asset` y `SpartanImageClient`.
- [`python_backend/main.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py): Montaje de `StaticFiles(directory=ASSETS_DIR)`.
- [`tools/validate_output.py`](file:///Users/luis/desktop/PROYECTOS/trending/tools/validate_output.py): Validación de existencia de assets.
- [`frontend/index.html`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/index.html): Visualización de imágenes en el panel de auditoría.

## Evidencias
- [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L107-L114): Registro de Fase 5B y exposición de `/assets/participante-5/`.
- [`python_backend/main.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py#L33-L35): `app.mount("/assets/participante-5", StaticFiles(directory=ASSETS_DIR)...)`.
- [`tests/test_output_validation.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_output_validation.py): Pruebas `test_ai_output_with_existing_asset_passes` y `test_ai_output_with_missing_asset_fails`.

## Trazabilidad
- **Fase:** Fase 5B (Generación de imágenes).
- **Fecha verificable:** 2026-07-27.
- **Decisiones relacionadas:** [ADR-0005](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md), [ADR-0010](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0010-spartan-ai-provider.md), [ADR-0012](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0012-two-step-publication.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia directa en código, routing de FastAPI y pruebas.
