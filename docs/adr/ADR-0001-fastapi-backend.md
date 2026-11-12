# ADR-0001: Adopción de Python 3.14.5 y FastAPI como framework central

## Estado
Accepted

## Contexto
El proyecto nació originalmente como una base en Node.js y Express (según consta en [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L11-L20) bajo fecha 2026-05-25). Sin embargo, el equipo requería una plataforma con mejor soporte nativo para librerías de scraping, manipulación de datos, validación estructurada y preparación para integración con modelos de inteligencia artificial en Python. Asimismo, se necesitaba una especificación de entorno estricta para evitar discrepancias de runtime entre desarrolladores y participantes.

## Decisión
1. Migrar y estandarizar el backend completamente sobre **Python 3.14.5**, fijando la versión en el archivo canónico [`.python-version`](file:///Users/luis/desktop/PROYECTOS/trending/.python-version).
2. Utilizar **FastAPI** (`0.128.8`) junto a **Uvicorn** (`0.39.0`) como framework web y servidor ASGI para exponer la API REST síncrona/asíncrona del sistema.
3. Descartar de forma definitiva la implementación legacy en Node.js/Express, eliminando `package.json` y dependencias de npm.

## Justificación
- **Documentación automática:** FastAPI genera OpenAPI (Swagger/ReDoc) de forma automática a partir de los tipos de Python y esquemas Pydantic, permitiendo a participantes principiantes probar endpoints en `/docs`.
- **Rendimiento y simplicidad:** Combina tipado estricto con una curva de aprendizaje reducida, ideal para el trabajo colaborativo por partes.
- **Ecosistema de IA:** Centraliza las futuras integraciones de scraping (RSS/HTML) y generación con LLMs en el ecosistema dominante de Python.
- **Unificación de runtime:** El uso de un archivo `.python-version` y la verificación obligatoria en [run.sh](file:///Users/luis/desktop/PROYECTOS/trending/run.sh) previene errores sutiles de sintaxis o incompatibilidades de librerías.

## Alternativas consideradas
- **Continuar con Node.js + Express:** Evidenciado en el historial del 2026-05-25. Se descartó el 2026-05-31 para evitar mantener dos backends paralelos y facilitar la integración con scripts de scraping e IA.
- **Flask:** Descartado implícitamente por carecer de validación nativa con Pydantic y documentación OpenAPI integrada sin extensiones de terceros.

## Consecuencias positivas
- Eliminación de deuda técnica al no mantener dos runtimes (Node.js y Python).
- Tipado estricto de extremo a extremo en endpoints.
- Acceso inmediato a la interfaz interactiva `/docs`.
- Ejecución ágil y ligera sin requerir compilación previa.

## Consecuencias negativas
- Obligó a reescribir los controladores y middlewares iniciales de Express a routers de FastAPI.
- Requiere entorno virtual específico de Python (`.venv`) en los puestos de los desarrolladores.

## Componentes afectados
- [`python_backend/main.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py): Punto de entrada de la aplicación FastAPI.
- [`.python-version`](file:///Users/luis/desktop/PROYECTOS/trending/.python-version): Definición del runtime oficial.
- [`python_backend/requirements.txt`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/requirements.txt): Dependencias base (`fastapi`, `uvicorn`).
- [`run.sh`](file:///Users/luis/desktop/PROYECTOS/trending/run.sh) y [`Makefile`](file:///Users/luis/desktop/PROYECTOS/trending/Makefile): Scripts de automatización y orquestación local.

## Evidencias
- [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L33-L60): Registro de migración a Python + FastAPI del 2026-05-31.
- [`python_backend/main.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/main.py#L18-L22): Instanciación de `FastAPI(title="Trending Instagram API")`.
- [`tests/test_python_backend.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_python_backend.py#L21-L26): Pruebas funcionales de endpoints sobre `TestClient(app)`.

## Trazabilidad
- **Fase:** Fase 1 (Backend Base) y Arquitectura General.
- **Fecha verificable:** 2026-05-31 (registrada en `CONTROL_CAMBIOS.md`).
- **Decisiones relacionadas:** [ADR-0002](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0002-layered-architecture.md), [ADR-0003](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0003-sqlite-sqlalchemy.md), [ADR-0004](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0004-pydantic-contracts.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia directa en código, dependencias e historial.
