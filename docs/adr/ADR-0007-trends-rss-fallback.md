# ADR-0007: Ingesta de tendencias vía Google Trends RSS con fallback determinístico

## Estado
Accepted

## Contexto
La Fase 2 (Participante 2) es la encargada de alimentar al sistema con temas de conversación actuales. Se evaluaron diversas vías de obtención (APIs no oficiales como `pytrends`, scraping HTML directo y fuentes RSS sindicadas). Las APIs no oficiales de Google Trends son conocidas por sufrir bloqueos agresivos de rate limiting y captchas (`HTTP 429 Too Many Requests`). Si el servicio de obtención falla o no responde, el pipeline completo queda detenido en el primer paso.

## Decisión
1. Adoptar el **feed RSS público de Google Trends** (`https://trends.google.com/trending/rss?geo={country}`) como fuente primaria de datos, fijando Argentina (`AR`) como país por defecto y un límite de 10 tendencias ([`python_backend/services/trends/trends_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/trends/trends_service.py)).
2. Implementar un proceso riguroso de sanitización y normalización:
   - Limpieza de títulos, eliminación de acentos/diacríticos con `unicodedata.normalize('NFKD')`, paso a minúsculas y eliminación de caracteres especiales para producir `normalized_title`.
   - Cálculo determinístico de puntuación (`score = (limit - index) * 10`).
   - Normalización de fechas RFC 822 / ISO 8601 en UTC.
3. Incorporar una estrategia de **Fallback Determinístico en caso de Fallo**:
   - Si la petición HTTP sufre un timeout (>10s), error HTTP (4xx/5xx), error de parseo XML (`xml.etree.ElementTree.ParseError`) o devuelve una lista vacía, el servicio **no arroja una excepción no controlada**.
   - En su lugar, devuelve una lista de temas de respaldo predefinidos (`_FALLBACK_TITLES`: "economía argentina", "tecnología", "deportes argentina", etc.), marca el campo `used_fallback: True`, `source: "fallback"`, registra el error técnico sanitizado y emite el output con estado `status = "draft"`.

## Justificación
- **Estabilidad frente a bloqueos:** El endpoint RSS de Google Trends es mucho más ligero y tolerante a peticiones que la interfaz web dinámica o endpoints privados de Google.
- **Sin dependencias pesadas:** Se resuelve con la biblioteca estándar (`xml.etree.ElementTree`, `unicodedata`, `email.utils`) y el cliente HTTP existente (`httpx`).
- **Resiliencia del pipeline:** Al degradar a estado `draft` en vez de explotar, los participantes de fases posteriores pueden seguir testeando sus módulos en modo local o de desarrollo sin depender de la conectividad a internet de Google.

## Alternativas consideradas
- **`pytrends`:** Descartada por inestabilidad recurrente ante cambios de API no documentada de Google y por riesgo de captchas durante pruebas automáticas.
- **Scraping con BeautifulSoup o Playwright:** Descartada por introducir dependencias complejas y lentitud en la ejecución.

## Consecuencias positivas
- El pipeline siempre puede iniciar su ejecución, incluso sin conexión a internet.
- Los títulos se entregan en un formato predecible y uniforme para la deduplicación de Fase 3.
- Registro claro de errores externos en el payload JSON.

## Consecuencias negativas
- Dependencia del formato RSS provisto por Google (si Google discontinúa el RSS, se requiere adaptar el parser).
- Si se activa el fallback, el contenido trending no es en tiempo real, sino temáticas generales de prueba.

## Componentes afectados
- [`python_backend/services/trends/trends_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/trends/trends_service.py): Lógica de consulta, parseo, normalización y fallback.
- [`python_backend/routers/pipeline_router.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/routers/pipeline_router.py): Endpoint `/pipeline/discover`.
- [`output/participante-2/`](file:///Users/luis/desktop/PROYECTOS/trending/output/participante-2): Directorio de outputs generados.

## Evidencias
- [`python_backend/services/trends/trends_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/trends/trends_service.py#L24-L45): Constantes `GOOGLE_TRENDS_RSS_URL`, `_FALLBACK_TITLES`.
- [`tests/test_trends_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_trends_service.py): Pruebas `test_valid_rss_returns_normalized_unique_items`, `test_timeout_or_http_error_activates_fallback`, `test_invalid_xml_or_empty_list_activates_fallback`.

## Trazabilidad
- **Fase:** Fase 2 (Descubrir tendencias).
- **Fecha verificable:** 2026-05-31 (base) y validaciones consolidadas en agosto de 2026.
- **Decisiones relacionadas:** [ADR-0005](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md), [ADR-0008](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0008-duplicate-detection-idempotency.md).

## Observaciones
Decisión plenamente **Confirmada** con amplia cobertura de pruebas unitarias y mocks en `test_trends_service.py`.
