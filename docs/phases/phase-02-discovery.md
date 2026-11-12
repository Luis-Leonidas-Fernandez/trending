# Fase 2 — Descubrimiento y Normalización de Tendencias

## 1. Objetivo
Descubrir los temas de conversación más populares en tiempo real a través de fuentes públicas de Google Trends para una región geográfica determinada (Argentina por defecto), transformar los datos en una estructura JSON normalizada y uniforme, y generar un output versionado auditable que alimente a la Fase 3.

---

## 2. Responsabilidad
* Consultar el feed RSS sindicado de Google Trends (`https://trends.google.com/trending/rss?geo={country}`).
* Parsear el documento XML devuelto y extraer título, fecha de publicación y categoría.
* Limpiar y normalizar los títulos (eliminación de acentos, caracteres especiales y minúsculas) para generar `normalized_title`.
* Asignar un puntaje decreciente proporcional a la posición del ranking (`score`).
* Guardar el archivo JSON versionado bajo el directorio [`output/participante-2/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-2).
* Proveer un mecanismo de fallback determinístico ante errores de red, timeouts o listas vacías.

---

## 3. Entradas
* Parámetros de función o query HTTP:
  - `country`: Código de país ISO de 2 letras (por defecto `"AR"`).
  - `limit`: Cantidad máxima de tendencias a obtener (entre 1 y 10, por defecto 10).
* Respuesta XML externa proveniente de `trends.google.com`.

---

## 4. Procesamiento
1. **Validación:** Comprobar que el país sea un string alfabético de 2 caracteres y que el límite esté dentro de `[1, 10]`.
2. **Petición HTTP:** Realizar un `GET` síncrono mediante `httpx.get` con timeout de 10.0 segundos.
3. **Parseo XML:** Analizar las etiquetas `<item>` del canal RSS usando `xml.etree.ElementTree`. Extraer `<title>` y `<pubDate>`.
4. **Normalización:**
   - Remover espacios redundantes y sanitizar caracteres invisibles.
   - Aplicar `unicodedata.normalize("NFKD", title)` para descomponer caracteres con tildes y diéresis.
   - Eliminar caracteres que no sean alfanuméricos ASCII o espacios y convertir a minúsculas para producir `normalized_title`.
   - Asignar `score = (limit - index) * 10`.
5. **Persistencia de Output:** Generar un UUID v4, validar el schema [`ParticipantOutput`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/schemas/output_schema.py#L32) y escribir `output/participante-2/trends_v1_{uuid-corto}.json`.

---

## 5. Salidas
* Archivo físico en `output/participante-2/trends_v1_{uuid-corto}.json`.
* Objeto de retorno [`TrendsResult`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/trends/trends_service.py#L52) con `items`, `country`, `used_fallback` y `error`.

---

## 6. Dependencias
* **Código Fuente:** [`python_backend/services/trends/trends_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/trends/trends_service.py).
* **Librerías:** `httpx`, `xml.etree.ElementTree`, `unicodedata`, `email.utils`.

---

## 7. Contratos JSON
Ejemplo de `trends_v1_02b0af11.json`:
```json
{
  "schema_version": "1.0",
  "run_id": "02b0af11-4fa2-4f05-9507-6bcfda45c60e",
  "participant": "participante-2",
  "stage": "trends",
  "generated_at": "2026-07-28T14:10:00Z",
  "status": "success",
  "data": {
    "country": "AR",
    "total_found": 10,
    "used_fallback": false,
    "items": [
      {
        "title": "Dólar hoy",
        "normalized_title": "dolar hoy",
        "category": "Economía",
        "source": "google_trends",
        "score": 100.0,
        "published_at": "2026-07-28T13:00:00Z"
      }
    ]
  },
  "errors": []
}
```

---

## 8. Persistencia
* La Fase 2 **no accede a SQLite**. Únicamente escribe archivos en `output/participante-2/`.

---

## 9. Manejo de Errores y Fallbacks
* Ante `httpx.TimeoutException`, `httpx.HTTPError`, `ET.ParseError` o lista devuelta vacía:
  - Se activa el fallback determinístico con `_FALLBACK_TITLES` (ej. "economía argentina", "tecnología", "deportes argentina").
  - El campo `source` de cada elemento se marca como `"fallback"`.
  - El output se genera con `status = "draft"` y se registra el error original sanitizado en `data.error` y en `errors`.
  - **El pipeline no se interrumpe.**

---

## 10. Pruebas Relacionadas
* [`tests/test_trends_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_trends_service.py):
  - `test_valid_rss_returns_normalized_unique_items`
  - `test_timeout_or_http_error_activates_fallback`
  - `test_invalid_xml_or_empty_list_activates_fallback`
  - `test_rss_with_more_than_limit_respects_limit`
  - `test_save_trends_output_success_matches_schema_and_filename`
  - `test_save_trends_output_fallback_is_draft_with_error`
  - `test_invalid_country_returns_clear_error`

---

## 11. ADRs Asociados
* [ADR-0005: Comunicación inter-fase basada en outputs JSON versionados](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md)
* [ADR-0007: Ingesta de tendencias vía Google Trends RSS con fallback determinístico](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0007-trends-rss-fallback.md)

---

## 12. Limitaciones Conocidas
* Depende de la disponibilidad del RSS público de Google Trends (sujeto a cambios en la estructura XML de Google).
* Solo soporta filtros por código de país; no permite segmentar por región provincial ni por categorías avanzadas.
