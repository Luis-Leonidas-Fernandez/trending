# Flujo de Datos y Ciclo de Vida del Pipeline

Este documento describe cómo se transforman los datos a lo largo de las distintas fases del sistema, los estados por los que transiciona una corrida del pipeline y el ciclo de vida de una publicación.

---

## 1. Diagrama de Secuencia de Ejecución Completa

El siguiente diagrama detalla la interacción entre el Frontend, el Backend FastAPI, los Servicios de Fase, la Base de Datos SQLite y los Servicios Externos:

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuario (Dashboard)
    participant UI as Frontend Web (5173)
    participant API as Pipeline Router (8000)
    participant SrvTrends as Fase 2 (Trends)
    participant SrvDup as Fase 3 (Duplicates)
    participant SrvSel as Fase 4 (Selector)
    participant SrvAI as Fase 5 (Spartan AI)
    participant SrvPub as Fase 6 (Instagram)
    participant SrvMet as Fase 7 (Metrics)
    participant DB as SQLite (trending.sqlite)
    participant Ext as Google Trends / Spartan

    User->>UI: Clic en "Ejecutar todo"
    UI->>API: POST /api/pipeline/run
    API->>API: Inicializa pipeline_state.json (status: running)

    %% Fase 2
    API->>SrvTrends: save_trends_output()
    SrvTrends->>Ext: GET RSS (trends.google.com)
    Ext-->>SrvTrends: XML con tendencias
    SrvTrends->>SrvTrends: Normaliza títulos y scores
    SrvTrends-->>API: Escribe output/participante-2/trends_v1_{id}.json

    %% Fase 3
    API->>SrvDup: process_trends_output(trends_path)
    SrvDup->>DB: Consulta temas existentes (get_all_topics)
    SrvDup->>SrvDup: Deduplica contra lote y contra DB
    SrvDup->>DB: Guarda solo temas nuevos (used=0)
    SrvDup-->>API: Escribe output/participante-3/duplicates_v1_{id}.json

    %% Fase 4
    API->>SrvSel: process_duplicates_output(duplicates_path)
    SrvSel->>SrvSel: Selecciona primer tema válido (used=0)
    Note over SrvSel: NO modifica SQLite en esta fase
    SrvSel-->>API: Escribe output/participante-4/topic_selector_v1_{id}.json

    %% Fase 5
    API->>SrvAI: process_topic_selector_output(selector_path)
    SrvAI->>Ext: POST /v1/chat/completions (Spartan 20128)
    Ext-->>SrvAI: JSON: headline, caption (3 párrafos), hashtags
    SrvAI->>Ext: POST /v1/images/generations (Spartan)
    Ext-->>SrvAI: JSON con b64_json
    SrvAI->>SrvAI: Decodifica y guarda PNG en output/participante-5/assets/
    SrvAI-->>API: Escribe output/participante-5/ai_v1_{id}.json

    %% Fase 6
    API->>SrvPub: process_ai_output(ai_path)
    SrvPub->>DB: Crea post en SQLite (status: draft)
    SrvPub-->>API: Escribe output/participante-6/instagram_v1_{id}.json

    API->>SrvPub: process_simulated_publication(post_id)
    SrvPub->>DB: Actualiza post a 'published_simulated'
    SrvPub->>DB: Crea registro en 'publication_logs'
    SrvPub->>DB: Marca topic.used = 1
    SrvPub-->>API: Escribe output/participante-6/instagram_v1_{id}_simulated.json

    %% Fase 7
    API->>SrvMet: process_instagram_output(pub_path)
    SrvMet->>DB: Audita integridad de post, log y topic
    SrvMet->>SrvMet: Calcula Score de Calidad (0-100%)
    SrvMet-->>API: Escribe output/participante-7/metrics_v1_{id}.json

    API->>DB: Upsert corrida en tabla 'pipeline_runs'
    API->>API: Actualiza pipeline_state.json (status: success)
    API-->>UI: Respuesta JSON con estado final y métricas
    UI-->>User: Muestra post final, imagen y score en dashboard
```

---

## 2. Estados de una Corrida del Pipeline

El archivo [`output/pipeline_state.json`](file:///Users/luis/desktop/PROYECTOS/trending/output/pipeline_state.json) y la tabla `pipeline_runs` mantienen sincronizado el estado del proceso:

```mermaid
stateDiagram-v2
    [*] --> idle: Creación o reset
    idle --> running: Inicia ejecución (batch o individual)
    running --> success: Todos los pasos completaron OK
    running --> draft: Algún paso completó con advertencias/fallback
    running --> error: Excepción o fallo irrecuperable
    running --> cancelled: Usuario canceló vía /pipeline/cancel

    success --> idle: Reset o nueva corrida
    draft --> idle: Reset o reintento
    error --> running: Reintento del paso fallido
    cancelled --> idle: Reset
```

* **`idle`:** El pipeline está en reposo, listo para iniciar una corrida o con un tema preparado para reutilizar.
* **`running`:** Uno o varios pasos están activamente en ejecución.
* **`success`:** La corrida finalizó completamente sin advertencias y con calidad 100%.
* **`draft`:** La corrida completó, pero alguna fase previa recurrió a un fallback determinístico (ej. Google Trends no respondió o Spartan generó texto en modo offline).
* **`error`:** Ocurrió un error grave de validación de contrato o fallo irrecuperable de persistencia.
* **`cancelled`:** La ejecución fue interrumpida cooperativamente a petición del usuario.

---

## 3. Estados de una Publicación (`GeneratedPost`)

A lo largo del pipeline, una publicación pasa por los siguientes estados dentro de SQLite y en los outputs:

```mermaid
stateDiagram-v2
    [*] --> draft: Creado en Fase 6A desde output de IA
    draft --> published_simulated: Ejecución de simulación (Fase 6B)
    published_simulated --> [*]: Auditado por Fase 7
```

1. **`draft`:** El post fue generado por la IA y persistido en `generated_posts`. Contiene `caption`, `image_url` y `hashtags`, pero aún no se ha cerrado la publicación ni se ha marcado el tema como usado.
2. **`published_simulated`:** Se ejecutó `simulate_publication()`. Se verificó que el post tiene caption e imagen, se creó la bitácora en `publication_logs` y se actualizó `topic.used = 1`.
3. *(Futuro)* **`published_instagram`:** Reservado para cuando se incorpore la llamada real a la Graph API de Meta en un release posterior.

---

## 4. Contratos de Datos y Archivos de Salida

Cada paso produce un archivo inmutable que alimenta al paso siguiente:

| Paso Origen | Archivo Producido | Consumidor Directo | Contenido Clave Transferido |
|---|---|---|---|
| **Fase 2** | `output/participante-2/trends_v1_{id}.json` | Fase 3 | Lista de tendencias (`items`) con `title`, `normalized_title`, `score`, `country`. |
| **Fase 3** | `output/participante-3/duplicates_v1_{id}.json` | Fase 4 | Temas deduplicados y guardados (`items`), con sus IDs de SQLite asignados. |
| **Fase 4** | `output/participante-4/topic_selector_v1_{id}.json` | Fase 5 | Objeto único `selected_topic` (`id`, `title`, `normalized_title`, `used=0`). |
| **Fase 5** | `output/participante-5/ai_v1_{id}.json` | Fase 6 | Textos (`headline`, `caption`, `description`, `hashtags`) y ruta a `image_file`. |
| **Fase 5B**| `output/participante-5/assets/ai_v1_{id}.png` | Fase 6 / UI | Archivo físico binario PNG decodificado desde Base64. |
| **Fase 6** | `output/participante-6/instagram_v1_{id}.json` | Fase 7 | Objeto `post` con ID de SQLite, estado (`draft` o `published_simulated`). |
| **Fase 7** | `output/participante-7/metrics_v1_{id}.json` | Dashboard / UI | Diccionario de auditoría técnica con `score` (0-100%) y lista de advertencias. |
