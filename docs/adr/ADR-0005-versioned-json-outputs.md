# ADR-0005: Comunicación inter-fase basada en outputs JSON versionados y desacoplados

## Estado
Accepted

## Contexto
El pipeline de generación de contenido consta de múltiples pasos consecutivos (descubrir tendencias -> filtrar duplicados -> elegir tema -> generar contenido -> publicar/simular -> medir). En un diseño tradicional en memoria, una falla en el paso 5 obligaría a reejecutar todo el flujo desde el paso 2 (consumiendo cuotas externas de Google Trends y tokens de IA). Además, resultaba fundamental que cada participante pudiera generar una entrega auditable y reproducible de forma independiente.

## Decisión
1. Implementar un protocolo de **Outputs Versionados en Disco** bajo el directorio canónico [`output/`](file:///Users/luis/desktop/PROYECTOS/trending/output), con subdirectorios dedicados por participante (`participante-2/` a `participante-7/`).
2. Adoptar una convención obligatoria y determinística para el nombre de archivos:
   `{stage}_v1_{uuid-corto}.json`
   donde `{uuid-corto}` corresponde exactamente a los primeros 8 caracteres del `run_id` (UUID v4) contenido en el JSON.
3. Exigir la validación formal de estos archivos mediante [`tools/validate_output.py`](file:///Users/luis/desktop/PROYECTOS/trending/tools/validate_output.py), que comprueba:
   - Extensión `.json` y formato de nombre mediante expresión regular.
   - Correspondencia entre el nombre y el campo `stage` del payload.
   - Correspondencia entre los primeros 8 caracteres del `run_id` y el nombre del archivo.
   - Existencia real en disco de cualquier asset referenciado en `data.image_file` (restringido a Fase 5).
4. Diseñar los servicios de las Fases 3 a 7 para que tomen como entrada la ruta a un archivo de salida de la fase previa, en lugar de recibir objetos volátiles en memoria.

## Justificación
- **Auditoría completa:** Cualquier corrida histórica queda guardada como un archivo estático JSON inmutable, permitiendo reconstruir exactamente qué datos se generaron y qué errores ocurrieron.
- **Trazabilidad y reproducibilidad:** Si falla la Fase 5, se puede reintentar pasando el archivo generado por la Fase 4 sin volver a consultar Google Trends ni alterar SQLite.
- **Desacoplamiento temporal:** Los participantes pueden desarrollar y probar sus servicios consumiendo archivos JSON de prueba sin necesidad de que el resto del sistema esté levantado.

## Alternativas consideradas
- **Comunicación exclusivamente en memoria / sesiones web:** Descartada porque una desconexión o fallo en un paso provocaría la pérdida del progreso y hacía imposible la auditoría forense offline.
- **Persistencia en tablas intermedias de base de datos:** Descartada para mantener el esquema relacional limpio (solo entidades finales de negocio) y permitir compartir archivos JSON fácilmente entre participantes.

## Consecuencias positivas
- Cada corrida del pipeline produce evidencia tangible y versionada.
- Posibilidad de inspeccionar manualmente los payloads generados por cada fase.
- Capacidad para reanudar o bifurcar ejecuciones del pipeline a partir de cualquier archivo previo.

## Consecuencias negativas
- Acumulación de archivos JSON en el directorio `output/` a lo largo del tiempo.
- Requiere I/O de disco para serializar y deserializar en cada transición de fase.

## Componentes afectados
- [`output/`](file:///Users/luis/desktop/PROYECTOS/trending/output): Estructura de carpetas por participante.
- [`tools/validate_output.py`](file:///Users/luis/desktop/PROYECTOS/trending/tools/validate_output.py): Script de validación de outputs.
- [`docs/ARQUITECTURA_Y_NORMAS.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/ARQUITECTURA_Y_NORMAS.md#L230-L308): Sección 8 con el contrato oficial de outputs.
- Todos los servicios de fase en [`python_backend/services/`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services).

## Evidencias
- [`docs/ARQUITECTURA_Y_NORMAS.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/ARQUITECTURA_Y_NORMAS.md#L230-L308): Contrato detallado de outputs JSON versionados.
- [`tools/validate_output.py`](file:///Users/luis/desktop/PROYECTOS/trending/tools/validate_output.py#L16-L56): `FILE_NAME_PATTERN` y función `validate_output_filename`.
- [`tests/test_output_validation.py`](file:///Users/luis/desktop/PROYECTOS/trending/tests/test_output_validation.py): Pruebas de sufijo, UUID corto, campos obligatorios y formato.

## Trazabilidad
- **Fase:** General y Pipeline Transversal.
- **Fecha verificable:** 2026-05-31.
- **Decisiones relacionadas:** [ADR-0004](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0004-pydantic-contracts.md), [ADR-0011](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0011-local-asset-storage.md), [ADR-0014](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0014-dual-pipeline-state.md).

## Observaciones
Decisión plenamente **Confirmada** con amplia evidencia en el código y cientos de outputs reales persistidos en `output/`.
