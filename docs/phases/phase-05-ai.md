# Fase 5 — Generación de Contenido con IA (Texto e Imagen)

## 1. Objetivo
Transformar el tema seleccionado por la Fase 4 en una pieza de contenido integral lista para redes sociales: generar titular (`headline`), pie de publicación en tres párrafos (`caption`), descripción editorial (`description`), hashtags temáticos, prompt visual y generar un archivo binario PNG de imagen de alta calidad, soportando tanto inferencia real vía Spartan Provider como modo offline determinístico con fallback de seguridad.

---

## 2. Responsabilidad
* Consumir y validar el output de Fase 4 (`participante-4`, etapa `topic_selector`).
* Gestionar la configuración de IA mediante [`AIConfig`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py#L48) (variables de entorno).
* **Generación de Texto:**
  - Ejecutar [`SpartanAIClient`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py#L105) contra `http://127.0.0.1:20128/v1/chat/completions`.
  - Forzar al modelo (`gpt-5`) mediante prompt de sistema a devolver JSON estricto con caption dividido en 3 párrafos separados con `\n\n`.
* **Generación de Imagen (Fase 5B):**
  - Si `AI_IMAGE_ENABLED=true` y `AI_DRY_RUN=false`, invocar [`SpartanImageClient`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py#L178) en `/v1/images/generations`.
  - Decodificar el campo Base64 `b64_json` y guardar el archivo PNG en [`output/participante-5/assets/ai_v1_{id}.png`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-5/assets).
* **Resiliencia:** Activar [`DryRunAIClient`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py#L73) si `AI_DRY_RUN=true` o ante cualquier falla de red/auth de Spartan (`fallback_on_error`).
* Envolver los clientes en [`registered_closer`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/pipeline/pipeline_cancel_service.py#L39) para permitir cancelación en vuelo.
* Generar el JSON versionado en [`output/participante-5/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-5).

---

## 3. Entradas
* Archivo JSON de salida de Fase 4 (`output/participante-4/topic_selector_v1_{id}.json`).
* Variables de entorno: `AI_PROVIDER`, `AI_DRY_RUN`, `SPARTAN_PROVIDER_BASE_URL`, `SPARTAN_APP_CLIENT_API_KEY`, `SPARTAN_PROVIDER_MODEL`, etc.
* Respuestas HTTP de inferencia provenientes de Spartan Provider (puerto `20128`).

---

## 4. Procesamiento
1. **Extracción:** Cargar `selected_topic` verificando que contenga `id`, `title` y `normalized_title`.
2. **Selección de Cliente:**
   - Si `dry_run = True` o `provider != "spartan"`: se instancia `DryRunAIClient`.
   - Si `dry_run = False`: se instancia `SpartanAIClient`. Si falta `SPARTAN_APP_CLIENT_API_KEY`, se lanza un error que dispara el fallback.
3. **Llamada de Texto (Chat Completions):**
   - Se envía la solicitud HTTP POST a Spartan dentro del context manager `registered_closer(client.close)`.
   - Se parsea el contenido JSON de la respuesta y se sanitizan los campos `headline`, `caption`, `description`, `hashtags` e `image_prompt`.
4. **Llamada de Imagen (Generations):**
   - Si la generación de imagen está habilitada y no está en dry-run, se envía el `image_prompt` a `/v1/images/generations`.
   - Se decodifica el Base64 y se guarda en `output/participante-5/assets/ai_v1_{uuid-corto}.png`.
5. **Generación de Output:** Escribir `output/participante-5/ai_v1_{uuid-corto}.json` con todos los metadatos de IA, modelo usado, advertencias y ruta relativa a `data.image_file`.

---

## 5. Salidas
* Archivo físico JSON: `output/participante-5/ai_v1_{uuid-corto}.json`.
* Archivo físico binario PNG (si aplica): `output/participante-5/assets/ai_v1_{uuid-corto}.png`.

---

## 6. Dependencias
* **Código Fuente:** [`python_backend/services/ai/ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py) y [`spartan_auth_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/spartan_auth_service.py).
* **Infraestructura Externa:** Spartan Provider (`http://127.0.0.1:20128`).
* **Librerías:** `httpx`, `base64`, `pydantic`.

---

## 7. Contratos JSON
Ejemplo de `ai_v1_68d67253.json`:
```json
{
  "schema_version": "1.0",
  "run_id": "68d67253-e9d5-45cf-a201-140b991d3420",
  "participant": "participante-5",
  "stage": "ai",
  "generated_at": "2026-07-28T14:10:15Z",
  "status": "success",
  "data": {
    "topic_id": 14,
    "topic_title": "Dólar hoy",
    "headline": "El dólar marca récord en la jornada financiera",
    "caption": "La divisa paralela registró una suba pronunciada tras las medidas cambiarias anunciadas esta mañana.\n\nEl movimiento impacta directamente en las expectativas de precios y en los costos de reposición de insumos clave.\n\nEspecialistas recomiendan cautela en decisiones de crédito de corto plazo y seguir la cotización oficial.",
    "description": "Análisis editorial enfocado en la coyuntura cambiaria y su impacto en la economía cotidiana.",
    "hashtags": ["#DolarHoy", "#Economia", "#Finanzas", "#Argentina"],
    "image_prompt": "Ilustración editorial vertical para Instagram sobre mercados financieros, gráficos modernos y alto contraste.",
    "image_file": "output/participante-5/assets/ai_v1_68d67253.png",
    "provider": "spartan",
    "model": "gpt-5",
    "used_fallback": false
  },
  "errors": []
}
```

---

## 8. Persistencia
* **En SQLite:** No realiza escrituras directas.
* **En Disco:** Persiste el JSON en `output/participante-5/` y la imagen binaria en `output/participante-5/assets/`.

---

## 9. Manejo de Errores y Fallbacks
* **Fallback de Texto:** Si falla Spartan (timeout, error 500, credencial vacía), se activa `DryRunAIClient`, que genera textos determinísticos prearmados, marca `status = "draft"` y registra el mensaje en `data.provider_error`.
* **Fallback de Imagen:** Si el texto se genera bien pero falla la imagen, el contenido textual se preserva, se marca `used_image_fallback = True`, se registra el error en `image_error` y el output queda en `status = "draft"`.
* **Cancelación:** Si el usuario invoca `/pipeline/cancel`, el socket de HTTPX se cierra inmediatamente mediante `registered_closer`, abortando la petición en curso.

---

## 10. Pruebas Relacionadas
* [`tests/test_ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_ai_service.py):
  - `test_dry_run_client_generates_deterministic_content`
  - `test_spartan_client_posts_to_chat_completions`
  - `test_spartan_image_client_posts_to_images_generations`
  - `test_process_topic_selector_output_with_spartan_success_is_success`
  - `test_process_topic_selector_output_spartan_error_uses_fallback_and_keeps_error`
  - `test_process_topic_selector_output_writes_image_asset_when_image_client_succeeds`
  - `test_process_topic_selector_output_image_error_marks_draft`

---

## 11. ADRs Asociados
* [ADR-0005: Comunicación inter-fase basada en outputs JSON versionados](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md)
* [ADR-0010: Generación de contenido con Spartan Provider HTTP, fallback y dry-run](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0010-spartan-ai-provider.md)
* [ADR-0011: Almacenamiento local y exposición estática de imágenes en `output/.../assets/`](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0011-local-asset-storage.md)
* [ADR-0015: Cancelación cooperativa de peticiones HTTP en vuelo](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0015-cooperative-request-cancellation.md)

---

## 12. Limitaciones Conocidas
* La generación real depende de la disponibilidad del servidor local de Spartan en el puerto 20128.
* La generación de imágenes mediante modelos de difusión introduce una latencia significativa (entre 20 y 90 segundos por imagen).
