# Sistema Trending para Instagram — Backend Python y Dashboard Web

Este proyecto implementa un sistema automatizado para descubrir tendencias, filtrar duplicados, generar piezas editoriales con inteligencia artificial y auditar su calidad, desarrollado sobre **Python 3.14.5 + FastAPI + SQLAlchemy + SQLite** y una interfaz web multi-página estática en **Vanilla HTML5, CSS y JavaScript nativo**.

El objetivo original del proyecto fue estructurar un flujo modular en cascada dividido en **7 fases de responsabilidad única**, permitiendo que distintos participantes o asistentes de IA colaboren sin pisarse mediante contratos Pydantic tipados y outputs JSON versionados en disco.

---

## 🗺️ Centro de Documentación Técnica y Arquitectura

Toda la documentación técnica profunda, decisiones de diseño, especificaciones de fase y guías operativas se encuentran centralizadas en el directorio [`docs/`](docs/README.md):

* **[Centro de Documentación (docs/README.md)](docs/README.md):** Mapa general de navegación y matriz de trazabilidad.
* **[Registro de Decisiones Arquitectónicas (docs/adr/)](docs/adr/README.md):** 16 registros formales en formato MADR que explican el *por qué* de las decisiones de diseño adoptadas.
* **[Visión General de Arquitectura](docs/architecture/overview.md)** y **[Componentes](docs/architecture/components.md):** Principios rectores, capas y responsabilidades.
* **[Flujo de Datos y Ciclo de Vida](docs/architecture/data-flow.md):** Secuencia temporal de llamadas, estados del pipeline y ciclo de vida de los posts.
* **[Base de Datos y Modelo Relacional](docs/architecture/database.md):** Esquema relacional SQLite con 4 tablas e índices de rendimiento.
* **[Especificación por Fases (1 a 7)](docs/phases/):**
  - [Fase 1: Backend Base y Persistencia](docs/phases/phase-01-backend.md)
  - [Fase 2: Descubrimiento de Tendencias (Google Trends)](docs/phases/phase-02-discovery.md)
  - [Fase 3: Filtrado de Duplicados y Persistencia Atómica](docs/phases/phase-03-duplicates.md)
  - [Fase 4: Selección Determinística de Tema y Reutilización](docs/phases/phase-04-selection.md)
  - [Fase 5: Generación de Contenido con IA (Texto e Imagen)](docs/phases/phase-05-ai.md)
  - [Fase 6: Persistencia y Simulación de Publicación](docs/phases/phase-06-publication.md)
  - [Fase 7: Medición, Auditoría de Calidad y Dashboard Web](docs/phases/phase-07-metrics-ui.md)
* **[Catálogo de Endpoints REST](docs/api/endpoints.md):** Especificación de más de 20 endpoints con ejemplos de carga y respuesta.
* **[Guía de Instalación y Despliegue](docs/operations/installation.md)** y **[Guía de Configuración (.env)](docs/operations/configuration.md)**.
* **[Guía de Resolución de Problemas (Troubleshooting)](docs/operations/troubleshooting.md)**.
* **[Informe de Auditoría y Trazabilidad](docs/DOCUMENTATION_AUDIT.md):** Registro de discrepancias históricas resueltas.

---

## 📌 Estado Operacional y Alcance Verificado

Para mantener la máxima transparencia técnica, el estado del software se clasifica distinguiendo entre lo implementado en código, las pruebas automatizadas, las validaciones manuales y las simulaciones:

| Fase / Componente | Estado de Implementación | Cobertura de Pruebas Automatizadas | Comportamiento y Modo Operacional |
|---|---|---|---|
| **Fase 1: Backend Base** | **Implementado** | [`test_python_backend.py`](tests/test_python_backend.py) | FastAPI + SQLite con `PRAGMA foreign_keys=ON` y SQLAlchemy 2.0. |
| **Fase 2: Descubrimiento** | **Implementado** | [`test_trends_service.py`](tests/test_trends_service.py) | Consulta Google Trends RSS (`AR`). Probado con mocks de XML y con fallback determinístico offline. |
| **Fase 3: Duplicados** | **Implementado** | [`test_duplicates_service.py`](tests/test_duplicates_service.py) | Deduplicación por `normalized_title` y persistencia atómica en `trending_topics`. |
| **Fase 4: Selector** | **Implementado** | [`test_topic_selector_service.py`](tests/test_topic_selector_service.py) | Selector puro `first_valid_unused`. Soporte para preparar reutilización manual histórica. |
| **Fase 5: IA (Texto e Imagen)** | **Implementado** | [`test_ai_service.py`](tests/test_ai_service.py)<br>[`test_spartan_auth_service.py`](tests/test_spartan_auth_service.py) | Cliente HTTP contra Spartan Provider (`127.0.0.1:20128`). Probado en CI/CD con mocks y modo `DryRunAIClient`. La generación real requiere Spartan activo. |
| **Fase 6: Publicación** | **Implementado (Simulación)** | [`test_instagram_service.py`](tests/test_instagram_service.py) | Subfase 6A persiste borrador en `generated_posts`. Subfase 6B **simula localmente la publicación**, crea log técnico y marca `topic.used = 1`. *(No publica en Meta Graph API real)*. |
| **Fase 7: Medición y UI** | **Implementado** | [`test_metrics_service.py`](tests/test_metrics_service.py)<br>[`test_pipeline_history_service.py`](tests/test_pipeline_history_service.py) | Scoring local de calidad (0 a 100%) y dos páginas web estáticas (`index.html` y `history.html`) servidas en puerto 5173. |
| **Transversal: Orquestador** | **Implementado** | [`test_pipeline_state_service.py`](tests/test_pipeline_state_service.py)<br>[`test_output_validation.py`](tests/test_output_validation.py) | Estado activo en `pipeline_state.json`, historial en tabla `pipeline_runs` y cancelación de sockets HTTP en vuelo. |

---

## ⚙️ Arquitectura en Capas

El backend en `python_backend/` respeta el principio de **Responsabilidad Única**:

* `routers/` → reciben peticiones HTTP, validan parámetros y retornan responses JSON estructuradas. Prohibido incluir SQL o lógica pesada.
* `schemas/` → validan contratos de datos de entrada y salida mediante Pydantic v2.
* `models/` → definen tablas, columnas, relaciones e índices mediante SQLAlchemy ORM.
* `repositories/` → encapsulan las consultas y escrituras a SQLite con transacciones controladas.
* `services/` → contienen la lógica de negocio pura de cada participante y la orquestación del pipeline.
* `database/` → administra la conexión al motor SQLite, sesiones y la referencia DDL en `schema.sql`.

---

## 🗄️ Esquema Relacional de Base de Datos

La base de datos SQLite vive por defecto en `python_backend/database/trending.sqlite` (configurable vía variable `PYTHON_DB_FILE`) y contiene 4 tablas:

1. **`trending_topics`:** Almacena los temas descubiertos, título normalizado, score y el campo `used` (0 = libre, 1 = usado).
2. **`generated_posts`:** Almacena los posts creados a partir de un tema (`topic_id`), textos, hashtags, ruta de imagen y estado (`draft`, `published_simulated`).
3. **`publication_logs`:** Registra las bitácoras técnicas de publicación simulada con metadatos de auditoría JSON.
4. **`pipeline_runs`:** Almacena el historial correlacionado de ejecuciones completas o por pasos, pasos seleccionados, outputs generados, errores y puntajes de calidad.

---

## 📦 Protocolo de Outputs Versionados (`output/`)

Cada fase genera evidencia persistida en disco bajo [`output/`](output/) siguiendo el formato determinístico:

```text
output/
├── participante-2/    # trends_v1_{uuid-corto}.json
├── participante-3/    # duplicates_v1_{uuid-corto}.json
├── participante-4/    # topic_selector_v1_{uuid-corto}.json
├── participante-5/    # ai_v1_{uuid-corto}.json
│   └── assets/        # ai_v1_{uuid-corto}.png (archivos binarios de imagen)
├── participante-6/    # instagram_v1_{uuid-corto}.json
├── participante-7/    # metrics_v1_{uuid-corto}.json
└── pipeline_state.json # Estado activo de la corrida en curso
```

Los outputs se validan mediante la herramienta CLI del proyecto:
```bash
.venv/bin/python tools/validate_output.py output/participante-2/trends_v1_02b0af11.json
```

---

## 🚀 Comandos de Instalación y Ejecución

Todos los comandos fueron verificados contra el [`Makefile`](Makefile) y el script [`run.sh`](run.sh):

### 1. Instalación y Preparación de Entorno
Crea el entorno virtual `.venv` si no existe, instala dependencias e inicializa SQLite:
```bash
# Vía Make:
make install

# O directamente vía shell:
./run.sh --install --check
```

### 2. Levantar la Aplicación en Modo Desarrollo
Inicia FastAPI con recarga en caliente en el puerto 8000 y el servidor web estático en el puerto 5173:
```bash
# Vía Make:
make dev

# O directamente vía shell:
./run.sh
```
* **Dashboard Web:** [http://127.0.0.1:5173](http://127.0.0.1:5173)
* **API FastAPI:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Documentación Interactiva Swagger:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 3. Ejecutar Pipeline Previo al Arranque
Para ejecutar automáticamente las Fases 2, 3 y 4 antes de levantar los servidores:
```bash
make pipeline
# o bien: ./run.sh --with-pipeline
```

### 4. Levantar Sólo el Backend (Sin Frontend)
```bash
make api
# o bien: ./run.sh --api-only
```

### 5. Control del Estado del Pipeline (`tools/pipeline_state.py`)
```bash
make state            # Muestra el estado activo de output/pipeline_state.json
make state-reset      # Reinicia el estado activo a idle con un nuevo run_id
make state-bootstrap  # Reconstruye el estado a partir de los últimos outputs en disco
make state-delete     # Elimina el archivo de estado
```

### 6. Ejecución de Pruebas y Linter
```bash
make test             # Ejecuta pytest sobre todas las suites de prueba
make lint             # Ejecuta Ruff para verificar estilo y consistencia
```

---

## 📄 Documentos Históricos de Referencia

Se conservan como referencia histórica de la evolución del proyecto:
* [`docs/PLAN_COMPLETO.md`](docs/PLAN_COMPLETO.md) — Plan original inicial del sistema.
* [`docs/ARQUITECTURA_Y_NORMAS.md`](docs/ARQUITECTURA_Y_NORMAS.md) — Contrato canónico de arquitectura y reglas por participante.
* [`CONTROL_CAMBIOS.md`](CONTROL_CAMBIOS.md) — Historial manual de evolución de mayo a agosto de 2026.
* [`RESPONSABILIDADES_PARTICIPANTES.md`](RESPONSABILIDADES_PARTICIPANTES.md) — Reparto original de responsabilidades.
* [`PLANTILLA_ENTREGA.md`](PLANTILLA_ENTREGA.md) — Plantilla de entrega por fase.
* [`docs/windows-setup-guide.md`](docs/windows-setup-guide.md) — Guía detallada paso a paso para entornos Windows PowerShell.
* `docs/exposure-participant-*.md` — Guías breves de exposición técnica por participante.
