# ADR-0006: Organización modular por participantes y regla de intervención administrativa

## Estado
Accepted

## Contexto
El proyecto fue diseñado como un ejercicio colaborativo dividido en responsabilidades asignadas a hasta 7 participantes (humanos o asistidos por IA). Uno de los problemas habituales en proyectos pedagógicos y colaborativos por fases en cascada es el **bloqueo en cadena**: si el Participante 3 no entrega su código de deduplicación, el Participante 4 (selector) y el 5 (IA) quedan completamente paralizados. Se requería una regla de gobernanza que preservara la autonomía individual sin comprometer el avance global del proyecto.

## Decisión
1. Establecer en [`docs/ARQUITECTURA_Y_NORMAS.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/ARQUITECTURA_Y_NORMAS.md#L140-L186) límites de edición estrictos por participante: cada uno sólo puede modificar su servicio específico y su carpeta de outputs.
2. Incorporar formalmente la **"Excepción por entregable incompleto / Intervención administrativa"** ([`ARQUITECTURA_Y_NORMAS.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/ARQUITECTURA_Y_NORMAS.md#L187-L199)): si un participante no completa su entregable a tiempo, un administrador técnico del proyecto queda autorizado a implementar el código faltante bajo condiciones estrictas:
   - Debe quedar registrado qué participante no pudo completar su parte.
   - El administrador debe tocar únicamente los archivos indispensables para desbloquear el flujo.
   - Debe respetarse la arquitectura oficial y no implementar alcance no solicitado.
   - El cambio debe quedar explícitamente documentado en [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md).

## Justificación
- **Continuidad del proyecto:** Evita que el retraso o deserción de un participante paralice al resto del equipo.
- **Trazabilidad ética y académica:** Deja constancia transparente de qué partes fueron completadas por su responsable original y cuáles requirieron intervención administrativa de rescate.
- **Protección de la arquitectura:** La regla limita al administrador para que no aproveche la situación para rediseñar caprichosamente el sistema.

## Alternativas consideradas
- **Esperar indefinidamente al participante:** Descartada por inviable operativamente ante plazos de entrega.
- **Reasignar la tarea a otro participante:** Descartada para no sobrecargar a compañeros con responsabilidades ajenas a su alcance inicial.

## Consecuencias positivas
- El proyecto pudo completarse de punta a punta: el 2026-07-27 el administrador completó con éxito las Fases 3, 4, 5, 6A, 6B y 5B que estaban pendientes, documentándolo en [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L70-L114).
- Las fases implementadas por el administrador respetaron al 100% los contratos y la responsabilidad única.

## Consecuencias negativas
- Menor homogeneidad de autoría en el código final del repositorio.
- Requiere un perfil senior/administrador con visión completa de la arquitectura para resolver los bloqueos.

## Componentes afectados
- [`docs/ARQUITECTURA_Y_NORMAS.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/ARQUITECTURA_Y_NORMAS.md#L187-L199): Cláusula de excepción.
- [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L70-L114): Bitácora de intervenciones administrativas.
- Todos los servicios completados bajo este esquema ([`duplicates_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/duplicates/duplicates_service.py), [`topic_selector_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/topic_selector/topic_selector_service.py), [`ai_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py), [`instagram_service.py`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/services/instagram/instagram_service.py)).

## Evidencias
- [`CONTROL_CAMBIOS.md`](file:///Users/luis/desktop/PROYECTOS/trending/CONTROL_CAMBIOS.md#L72, #L78, #L86, #L94, #L102, #L109): Registros explícitos titulados *"Intervención administrativa — Fase X"*.
- [`docs/ARQUITECTURA_Y_NORMAS.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/ARQUITECTURA_Y_NORMAS.md#L187-L199): Sección "Excepción por entregable incompleto".

## Trazabilidad
- **Fase:** Metodología y Gobernanza Transversal.
- **Fecha verificable:** 2026-07-27.
- **Decisiones relacionadas:** [ADR-0002](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0002-layered-architecture.md), [ADR-0005](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0005-versioned-json-outputs.md).

## Observaciones
Decisión plenamente **Confirmada** con evidencia documental explícita e histórica en el repositorio.
