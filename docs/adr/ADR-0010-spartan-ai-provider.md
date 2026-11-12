# ADR-0010: Generación de contenido con Spartan Provider HTTP, fallback y dry-run

## Estado
Accepted

## Contexto
La Fase 5 (Participante 5) debe transformar el tema elegido en un post atractivo para Instagram: titular, pie de publicación (caption), hashtags, descripción editorial y prompt visual. El plan original mencionaba el uso de OpenAI o Gemini directos. Sin embargo, en un entorno de desarrollo compartido o educativo, exponer claves de API de OpenAI directas en repositorios o requerir tarjetas de crédito a cada alumno genera barreras y riesgos de seguridad. Se necesitaba una pasarela unificada, segura y resiliente ante caídas de conexión.

## Decisión
1. Adoptar **Spartan Provider** como pasarela centralizada de IA accesible vía HTTP local (`http://127.0.0.1:20128`), autenticado mediante `SPARTAN_APP_CLIENT_API_KEY` (sin quemar API keys comerciales de OpenAI en el proyecto).
2. Diseñar un cliente modular desacoplado en [`python_backend/services/ai/ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py) bajo el protocolo común `AIClient`:
   - [`SpartanAIClient`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py#L105): Llama a `/v1/chat/completions` con modelo configurable (`gpt-5` por defecto), inyectando un prompt de sistema estricto que exige español rioplatense natural y un caption estructurado obligatoriamente en 3 párrafos separados con `\n\n`.
   - [`DryRunAIClient`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py#L73): Genera contenido determinístico local sin conexión a red para desarrollo, CI/CD y pruebas unitarias rápidas.
3. Incorporar una estrategia de **Fallback Determinístico en Fallo (`fallback_on_error`)**:
   - Si falta la credencial de Spartan, si Spartan está apagado o si la llamada HTTP devuelve timeout o error 5xx, el servicio **no interrumpe el pipeline con una excepción no capturada**.
   - Invoca automáticamente a `DryRunAIClient`, conserva el error técnico original en `provider_error`, marca `used_fallback = True` y emite el archivo en `output/participante-5/` con `status = "draft"`.
4. Integrar un puente de autenticación administrativa en [`spartan_auth_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/spartan_auth_service.py) que permite consultar el estado de conexión de los proveedores de Spartan (`codex`, `gemini`) e iniciar flujos OAuth sin salir del dashboard de Trending.

## Justificación
- **Seguridad de credenciales:** Ningún secreto comercial de OpenAI o Gemini vive en el código ni en el archivo `.env` del proyecto.
- **Resiliencia absoluta:** El pipeline nunca se queda colgado; si Spartan no está levantado, el sistema genera un borrador válido que permite continuar hasta las Fases 6 y 7.
- **Calidad editorial garantizada:** El prompt del sistema fuerza la estructura en 3 párrafos (qué pasó, por qué importa y recomendación), evitando captions de un solo bloque de texto.

## Alternativas consideradas
- **Integrar SDK oficial de OpenAI (`openai-python`):** Descartada en `CONTROL_CAMBIOS.md` (2026-07-27) para no agregar dependencias innecesarias y evitar el manejo directo de API keys privadas en el proyecto compartido.
- **Llamadas síncronas bloqueantes sin fallback:** Descartada por interrumpir el pipeline y arruinar la experiencia del usuario ante microcortes.

## Consecuencias positivas
- El sistema funciona tanto con IA real en la nube como en modo 100% offline (activando `AI_DRY_RUN=true`).
- Cero dependencias adicionales (usa el cliente HTTP ya existente `httpx`).
- Supervisión del estado del proveedor desde el frontend en `/api/ai/providers/status`.

## Consecuencias negativas
- Dependencia de un proceso auxiliar externo (Spartan Gateway levantado en el puerto 20128) si se desea generación real de contenido.
- Si se activa el fallback determinístico, los textos son plantillas sintéticas y no redacciones contextuales de un modelo de lenguaje.

## Componentes afectados
- [`python_backend/services/ai/ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py): Clientes Spartan y DryRun, configuración y fallback.
- [`python_backend/services/ai/spartan_auth_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/spartan_auth_service.py): Puente de estado y OAuth.
- [`python_backend/routers/ai_router.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/routers/ai_router.py): Endpoints de proveedores.
- [`.env.example`](file:///Users/luis/desktop/PROYECTOS/trending/.env.example): Variables `AI_PROVIDER`, `AI_DRY_RUN`, `SPARTAN_PROVIDER_BASE_URL`, etc.

## Evidencias
- [`python_backend/services/ai/ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py#L48-L63): Dataclass `AIConfig`.
- [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L86-L92): Registro de implementación de Fase 5 con Spartan y fallback.
- [`tests/test_ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_ai_service.py): Pruebas unitarias de clientes, fallback y llamadas mockeadas a `/v1/chat/completions`.

## Trazabilidad
- **Fase:** Fase 5 (Generación con IA).
- **Fecha verificable:** 2026-07-27.
- **Decisiones relacionadas:** [ADR-0005](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md), [ADR-0011](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0011-local-asset-storage.md), [ADR-0015](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0015-cooperative-request-cancellation.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia de código, tests y variables de entorno.
