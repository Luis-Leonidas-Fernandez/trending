# Control de cambios

Este archivo sirve como historial manual del proyecto mientras el equipo todavía no usa Git o GitHub.

## 2026-05-25

### Coordinación inicial
- Se definió trabajar solo el alcance del Participante 1 en esta primera etapa.
- Se dejó preparado el proyecto base para futuras integraciones.

### Backend base
- Se creó la estructura inicial del backend con Express, SQLite y MVC simple.
- Se agregaron rutas, controladores, modelos, validadores y esquema SQL.
- La carpeta principal del servidor pasó de `src/` a `backend/`.

### Validación y seguridad
- Se incorporó Zod para validación de JSON.
- Se fijó `sqlite3` en versión exacta.
- Se actualizó `express` a una versión segura.
- El proyecto quedó con `0 vulnerabilities` luego de actualizar dependencias.

### Documentación
- Se creó `COMANDOS_PROYECTO.md`.
- Se creó la carpeta `docs/`.
- Se agregaron diagramas de flujo y entidad-relación en `.md` y `.svg`.

### Preparación para trabajo en equipo
- Se crearon carpetas de servicios por responsabilidad futura.
- Se agregaron archivos de coordinación manual para trabajar sin Git ni GitHub.

## 2026-05-31

### Migración gradual a Python + FastAPI
- Se creó `python_backend/` como backend paralelo oficial en Python + FastAPI.
- Se replicaron los endpoints base existentes del backend Node/Express.
- Se agregó conexión SQLite con schema equivalente.
- Se agregaron routers, repositories y schemas Pydantic.
- Se actualizaron README, responsabilidades, plan completo y prompts para trabajar sobre Python.
- Durante la migración, el backend Node quedó temporalmente como referencia legacy.

### Placeholders por participante
- Se agregaron placeholders mínimos para Participantes 2 a 6 en `python_backend/services/`.
- Se agregó `frontend/.gitkeep` para conservar la carpeta del Participante 7 sin implementar frontend todavía.
- Los placeholders no implementan features completas; solo marcan contrato y ubicación de trabajo.

### Limpieza final del proyecto
- Se eliminó el backend Node/Express legacy.
- Se eliminaron `package.json`, `package-lock.json` y `.npmrc`.
- El proyecto quedó centrado solo en Python + FastAPI.

### Capa de datos con SQLAlchemy
- Se migró el acceso a datos desde `sqlite3` directo a SQLAlchemy.
- Se agregaron `models/` ORM para topics, posts y logs.
- Se mantuvo el contrato de la API sin romper endpoints.

### Runtime y entorno
- Se actualizó el proyecto a Python `3.14.5`.
- Se recreó `.venv` con la nueva versión.
- Se agregó `.python-version` para fijar el runtime recomendado.

### Contrato de arquitectura y prompts
- Se creó `docs/ARQUITECTURA_Y_NORMAS.md` como contrato principal del proyecto.
- Se reforzaron los prompts por participante para evitar sobre-implementación y respetar responsabilidad única.

### Outputs versionados
- Se creó la carpeta `output/` con subcarpetas por participante.
- Se agregó un contrato Pydantic para outputs JSON versionados.
- Se agregó `tools/validate_output.py` para validar outputs.
- Se documentó el uso de `run_id` UUID y la convención de nombres `{stage}_v1_{uuid-corto}.json`.
## 2026-07-27

### Intervención administrativa — Fase 3
- El administrador completó la Fase 3 porque el entregable estaba pendiente y la regla arquitectónica vigente habilita avanzar con entregables faltantes.
- Se implementó `python_backend/services/duplicates/duplicates_service.py` para consumir outputs de Fase 2, descartar duplicados por `normalized_title` y persistir sólo temas nuevos en SQLite.
- Se agregó `tests/test_duplicates_service.py` con pruebas unitarias y una integración con SQLite temporal.
- No se modificaron routers, modelos, repositorios ni schemas.

### Intervención administrativa — Fase 4
- El administrador completó la Fase 4 porque el entregable estaba pendiente y la regla arquitectónica vigente habilita avanzar con entregables faltantes.
- Se implementó `python_backend/services/topic_selector/topic_selector_service.py` como selector puro: consume outputs de Fase 3, preserva orden y selecciona el primer tema válido con `used` en `0` o `false`.
- Se decidió no modificar SQLite ni marcar `used` en esta fase; ese cambio queda reservado para después de persistir exitosamente el post en una fase posterior.
- Se agregó `tests/test_topic_selector_service.py` con pruebas unitarias y de procesamiento de archivos.
- No se modificaron routers, modelos, repositorios ni schemas.

### Intervención administrativa — Fase 5
- El administrador conectó la Fase 5 porque el entregable estaba pendiente y la regla arquitectónica vigente habilita avanzar con entregables faltantes.
- Se implementó `python_backend/services/ai/ai_service.py` con `DryRunAIClient` y `SpartanAIClient`.
- La generación real usa Spartan Provider por HTTP en `/v1/chat/completions`; si falta auth o falla el provider, se genera un fallback determinístico en estado `draft` y se registra el error original.
- Se conectó el paso `crear` en `python_backend/routers/pipeline_router.py` para que el pipeline pueda ejecutar Fase 5 desde API/UI.
- Se agregaron variables de entorno en `.env.example` para controlar provider, dry-run, fallback, modelo, app-client key y timeout.
- Se agregó `tests/test_ai_service.py` y una prueba de router para el paso `crear`.
- No se agregaron dependencias nuevas ni se ejecutó build.

### Intervención administrativa — Fase 6A
- El administrador implementó la persistencia del post generado porque el entregable estaba pendiente y la regla arquitectónica vigente permite avanzar con entregables faltantes.
- Se reemplazó el placeholder de `python_backend/services/instagram/instagram_service.py` por una operación que consume `participante-5 / ai`, persiste el post en SQLite como `draft` y genera `output/participante-6/instagram_v1_{uuid-corto}.json`.
- El paso `publicar` del pipeline quedó conectado como preparación/persistencia, no como publicación externa real.
- No se marca `topic.used=1` en esta subfase; queda reservado para después de completar una publicación/preparación final exitosa.
- Se agregaron pruebas unitarias y de router, sin dependencias nuevas ni build.


### Intervención administrativa — Fase 6B simulada y auditoría

- Se agregó una publicación simulada local para cerrar el flujo sin llamar a Instagram real.
- La simulación crea `publication_logs`, cambia el post a `published_simulated` y marca el tema asociado como usado.
- Se agregó una vista UI de auditoría en `frontend/index.html` para revisar imagen, caption, hashtags, estado y log del post finalizado.
- Se expone `output/participante-5/assets/` como assets estáticos desde `/assets/participante-5/` para previsualizar imágenes manuales en la UI.

### Intervención administrativa — Fase 5B imágenes vía Spartan

- Se acopló Fase 5 a `POST /v1/images/generations` de Spartan Provider.
- La generación de contenido ahora intenta crear un asset PNG desde `data.image_prompt` y guardarlo en `output/participante-5/assets/`.
- El output de Participante 5 expone `data.image_file`, `image_source`, `image_model`, `image_revised_prompt`, `image_used_fallback` e `image_error`.
- Si Spartan falla generando imagen, Fase 5 queda en `draft` y conserva el error como `image_generation: ...` sin ocultarlo.
