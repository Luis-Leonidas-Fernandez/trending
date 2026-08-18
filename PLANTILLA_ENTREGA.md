# Plantilla de entrega

## Participante
Participante 6 — Persistencia de post generado / preparación Instagram (Fase 6A).

> Intervención administrativa: el administrador del proyecto completó esta subfase porque el entregable estaba pendiente y la regla arquitectónica vigente permite avanzar con entregables faltantes. El alcance se limitó a persistir el post y preparar el contrato; no se publica en Instagram real todavía.

## Fecha
2026-07-27

## Qué hice
- Consumí el output `participante-5 / ai` generado por Fase 5.
- Validé contrato, tema seleccionado, caption y estado de entrada.
- Persistí el contenido generado en SQLite usando `post_repository.create_post`.
- Guardé el post como `draft`.
- Generé output versionado `participante-6 / instagram`.
- Dejé `ready_to_publish=false` y `publication_skipped=true` para aclarar que no hubo publicación externa.
- No marqué `topic.used=1`; eso queda para una fase posterior cuando la publicación/preparación final sea exitosa.
- Conecté el paso `publicar` al pipeline como Fase 6A por intervención administrativa.

## Archivos que modifiqué o creé
- `/Users/luis/Desktop/PROYECTOS/trending/python_backend/services/instagram/instagram_service.py`
- `/Users/luis/Desktop/PROYECTOS/trending/python_backend/routers/pipeline_router.py`
- `/Users/luis/Desktop/PROYECTOS/trending/python_backend/main.py`
- `/Users/luis/Desktop/PROYECTOS/trending/tests/test_instagram_service.py`
- `/Users/luis/Desktop/PROYECTOS/trending/tests/test_python_backend.py`
- `/Users/luis/Desktop/PROYECTOS/trending/PLANTILLA_ENTREGA.md`
- `/Users/luis/Desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md`

## Dependencias nuevas
- ninguna

## Justificación de dependencias nuevas
- No aplica; se reutilizó biblioteca estándar, Pydantic existente y repositorios actuales.

## Cambios en .env
- ninguno

## Output JSON generado
- `output/participante-6/instagram_v1_{uuid-corto}.json`

## Assets generados
- ninguno

## Validaciones realizadas
- Pruebas unitarias de persistencia mockeada.
- Pruebas de input `success`, `draft`, error de persistencia, contrato inválido y caption faltante.
- Prueba de conexión del paso `publicar` al router del pipeline.
- Validación del output con `/Users/luis/Desktop/PROYECTOS/trending/tools/validate_output.py`.

## Qué falta
- Publicación real o preparación final para Instagram.
- Crear logs de publicación cuando exista intento real.
- Marcar `topic.used=1` únicamente después de una persistencia/publicación final exitosa.
- Fase 7 / medición o frontend final.

## Instrucciones para integrar
1. Usar `process_ai_output(input_path)` para consumir un output de Fase 5 y generar Fase 6A.
2. Consumir `data.post_id` desde `output/participante-6/instagram_v1_{uuid-corto}.json` en fases posteriores.
3. No tratar `ready_to_publish=false` como publicación real; es sólo persistencia/preparación.


## Actualización administrativa — Fase 6B simulada

- Se agregó cierre de publicación simulada para auditoría local.
- La operación no publica en Instagram real; registra un intento simulado en `publication_logs`.
- Si la simulación es exitosa, el post pasa a `published_simulated` y el tema se marca como usado.
- La UI muestra una tarjeta de post finalizado con imagen, caption, hashtags, estado y log asociado.
- Esto permite validar el flujo completo antes de integrar Instagram Graph API real.

## Actualización administrativa — Fase 5B imágenes vía Spartan

- Fase 5 ahora puede consumir el endpoint de imágenes de Spartan Provider.
- La imagen se guarda como PNG versionado en `output/participante-5/assets/` y se referencia desde `data.image_file`.
- La integración es auditable: un fallo de imagen no se oculta, deja la salida en `draft` con error informado.
- Variables relevantes: `AI_IMAGE_ENABLED`, `SPARTAN_PROVIDER_IMAGE_MODEL`, `SPARTAN_PROVIDER_IMAGE_SIZE`, `SPARTAN_PROVIDER_IMAGE_TIMEOUT_SECONDS`.
