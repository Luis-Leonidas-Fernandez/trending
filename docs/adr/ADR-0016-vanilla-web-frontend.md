# ADR-0016: Adopción de Frontend Vanilla (HTML/CSS/JS) y descarte del stack Astro + Tailwind

## Estado
Proposed (Pendiente de confirmación del desarrollador)

## Contexto
El documento inicial de diseño ([`docs/PLAN_COMPLETO.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/PLAN_COMPLETO.md#L16)) establecía que la capa de presentación (Fase 7) se construiría utilizando el framework **Astro** junto a **TailwindCSS**. De igual manera, [`prompt/P7_FRONTEND.md`](file:///Users/luis/desktop/PROYECTOS/trending/prompt/P7_FRONTEND.md) mencionaba "Frontend futuro: Astro + TailwindCSS". Sin embargo, en el código fuente actual del repositorio no existe ningún proyecto Astro, ni archivos `.astro`, ni `package.json`, ni toolchain de Node.js. En su lugar, el directorio [`frontend/`](file:///Users/luis/desktop/PROYECTOS/trending/frontend) contiene una aplicación web completa desarrollada íntegramente en **Vanilla HTML5, CSS moderno y JavaScript modular nativo (ES6)** ([`index.html`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/index.html), [`history.html`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/history.html), [`history.js`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/history.js)), servida localmente con el módulo nativo de Python `http.server 5173` en [`run.sh`](file:///Users/luis/desktop/PROYECTOS/trending/run.sh#L211-L213).

## Decisión
Adoptar y mantener una interfaz de usuario **Vanilla Web (HTML/CSS/JS)** sin dependencias de Node.js, npm ni etapas de build/compilación:
1. `frontend/index.html`: Dashboard principal interactivo que renderiza las 6 cards del pipeline, el panel de control de ejecución paso a paso o batch, la barra de estado animada, el modal de auditoría del último post y la conexión a Spartan Provider.
2. `frontend/history.html` y `frontend/history.js`: Vista completa de historial de ejecuciones, filtros por fecha y reutilización de temas antiguos.
3. Servir la interfaz estática utilizando `python3 -m http.server 5173 --bind 127.0.0.1 --directory frontend` dentro del script unificado [`run.sh`](file:///Users/luis/desktop/PROYECTOS/trending/run.sh).

## Justificación
*(Inferencia técnica basada en la arquitectura resultante del repositorio)*
- **Cero dependencias de Node.js:** Al descartar Astro, el proyecto elimina por completo la necesidad de instalar Node.js, npm, `node_modules` (que suelen superar los 200 MB) y procesos de compilación adicionales.
- **Simplicidad de ejecución con un solo comando:** Con `./run.sh`, cualquier compañero en Windows, macOS o Linux levanta FastAPI y el Frontend con el intérprete de Python que ya tiene instalado.
- **Portabilidad y velocidad de arranque:** No hay tiempo de bundling ni transpilación; cualquier cambio en el HTML/CSS se ve al recargar el navegador.
- **Coherencia con las reglas del proyecto:** Cumple la regla de oro de [`docs/ARQUITECTURA_Y_NORMAS.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/ARQUITECTURA_Y_NORMAS.md): *"Si hay dos opciones, una compleja y otra simple y suficiente, se debe elegir la simple y suficiente"*.

## Alternativas consideradas
- **Astro + TailwindCSS:** Alternativa original descrita en `docs/PLAN_COMPLETO.md`. Requería Node.js, compilación estática y configuración de entorno heterogénea.
- **React / Vite SPA:** Descartada por complejidad y sobrecarga de librerías para una herramienta de administración interna.

## Consecuencias positivas
- El repositorio es 100% Python y estándares web nativos.
- Despliegue instantáneo sin paso de `npm install` ni `npm run build`.
- Interfaz moderna, reactiva y elegante con soporte para modo claro/oscuro nativo mediante variables CSS.

## Consecuencias negativas
- Falta de un sistema de componentes formales como el que ofrece Astro (fragmentos compartidos deben manejarse en el mismo archivo o vía DOM en JS).
- `frontend/index.html` acumula más de 2000 líneas combinadas de estructura, estilos y lógica.

## Componentes afectados
- [`frontend/index.html`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/index.html): Dashboard del pipeline.
- [`frontend/history.html`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/history.html) y [`frontend/history.js`](file:///Users/luis/desktop/PROYECTOS/trending/frontend/history.js): Historial y reutilización.
- [`run.sh`](file:///Users/luis/desktop/PROYECTOS/trending/run.sh): Servidor estático en puerto 5173.
- [`Makefile`](file:///Users/luis/desktop/PROYECTOS/trending/Makefile): Target `make dev`.

## Evidencias
- Archivos reales en [`frontend/`](file:///Users/luis/desktop/PROYECTOS/trending/frontend) y ausencia total de `package.json` o archivos `.astro`.
- [`run.sh`](file:///Users/luis/desktop/PROYECTOS/trending/run.sh#L211-L213): Comando de servicio HTTP con Python nativo.
- [`docs/windows-setup-guide.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/windows-setup-guide.md#L13-L17): Especificación de Frontend en puerto `5173`.

## Trazabilidad
- **Fase:** Frontend / Fase 7 / Presentación.
- **Fecha verificable:** Julio de 2026.
- **Decisiones relacionadas:** [ADR-0001](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0001-fastapi-backend.md), [ADR-0013](file:///Users/luis/desktop/PROYECTOS/trending/docs/adr/ADR-0013-local-audit-metrics.md).

## Observaciones
**Decisión Pendiente de Confirmación del Desarrollador:**
Si bien la presencia del código y la ausencia de Node.js confirman la adopción fáctica de HTML/CSS/JS vanilla, no se encontró un acta formal o registro en `CONTROL_CAMBIOS.md` que explique por qué se abandonó Astro. La justificación técnica aquí expuesta es una deducción arquitectónica fundada. Requiere que el creador del repositorio confirme formalmente si este diseño es definitivo o una etapa transitoria.
