# Configuración del Sistema y Variables de Entorno

Este documento describe todas las variables de configuración disponibles en el archivo `.env` del proyecto **Trending**, sus valores por defecto y cómo interactúan con Spartan Provider y el pipeline.

---

## 1. Plantilla `.env.example`

El archivo canónico [`.env.example`](file:///Users/luis/desktop/PROYECTOS/trending/.env.example) en la raíz contiene las siguientes variables:

```ini
PYTHON_DB_FILE=./python_backend/database/trending.sqlite

AI_PROVIDER=spartan
AI_DRY_RUN=true
AI_FALLBACK_ON_ERROR=true
AI_IMAGE_ENABLED=false

SPARTAN_PROVIDER_BASE_URL=http://127.0.0.1:20128
SPARTAN_PROVIDER_MODEL=gpt-5
SPARTAN_PROVIDER_IMAGE_MODEL=
SPARTAN_PROVIDER_IMAGE_SIZE=1024x1024
SPARTAN_PROVIDER_TIMEOUT_SECONDS=20
SPARTAN_PROVIDER_IMAGE_TIMEOUT_SECONDS=120
SPARTAN_AUTH_TIMEOUT_SECONDS=10
SPARTAN_APP_CLIENT_API_KEY=
```

---

## 2. Descripción Detallada de Variables

### 2.1. Persistencia y Base de Datos
* **`PYTHON_DB_FILE`:**
  - **Propósito:** Ruta absoluta o relativa al archivo de base de datos SQLite.
  - **Default:** `./python_backend/database/trending.sqlite`.
  - **Uso:** Permite en entornos de test o CI/CD apuntar a una base temporal sin alterar la base de desarrollo.

### 2.2. Configuración General de IA (Fase 5)
* **`AI_PROVIDER`:**
  - **Propósito:** Nombre del proveedor de IA.
  - **Valores soportados:** `"spartan"`.
  - **Default:** `"spartan"`.
* **`AI_DRY_RUN`:**
  - **Propósito:** Controla si el servicio de IA ejecuta llamadas reales a la red o utiliza contenido determinístico sintético.
  - **Valores:** `true` (modo offline/dry-run) | `false` (modo inferencia real).
  - **Default:** `true`.
  - **Recomendación:** Dejar en `true` si no se dispone de Spartan Provider o para correr tests rápidos.
* **`AI_FALLBACK_ON_ERROR`:**
  - **Propósito:** Habilita el mecanismo de fallback de seguridad ante errores.
  - **Valores:** `true` | `false`.
  - **Default:** `true`.
  - **Comportamiento:** Si es `true` y la llamada HTTP a Spartan falla por timeout o credencial inválida, el sistema conmuta automáticamente a `DryRunAIClient` y marca el output como `draft`, evitando que el pipeline se rompa.
* **`AI_IMAGE_ENABLED`:**
  - **Propósito:** Habilita o deshabilita la generación de imágenes por difusión en Fase 5B.
  - **Valores:** `true` | `false`.
  - **Default:** `false`.
  - **Comportamiento:** Si es `false`, la Fase 5 solo genera texto y no invoca a `/v1/images/generations`. Para generar assets PNG reales, debe establecerse en `true` y `AI_DRY_RUN=false`.

### 2.3. Parámetros de Conexión a Spartan Provider
* **`SPARTAN_PROVIDER_BASE_URL`:**
  - **Propósito:** URL base del servidor gateway de Spartan.
  - **Default:** `http://127.0.0.1:20128`.
* **`SPARTAN_APP_CLIENT_API_KEY`:**
  - **Propósito:** Clave de autenticación de aplicación cliente para Spartan Gateway.
  - **Default:** Vacía (`""`).
  - **Importante:** Requerida obligatoriamente cuando `AI_DRY_RUN=false`. Si está vacía y se ejecuta en modo real, el sistema dispara el fallback determinístico de seguridad.
* **`SPARTAN_PROVIDER_MODEL`:**
  - **Propósito:** Nombre del modelo para chat completions de texto.
  - **Default:** `gpt-5`.
* **`SPARTAN_PROVIDER_IMAGE_MODEL`:**
  - **Propósito:** Nombre específico del modelo para generación de imágenes (si se omite, utiliza el valor de `SPARTAN_PROVIDER_MODEL`).
  - **Default:** Vacío.
* **`SPARTAN_PROVIDER_IMAGE_SIZE`:**
  - **Propósito:** Dimensiones de la imagen generada.
  - **Default:** `1024x1024`.
* **`SPARTAN_PROVIDER_TIMEOUT_SECONDS`:**
  - **Propósito:** Tiempo máximo de espera en segundos para la respuesta de texto.
  - **Default:** `20`.
* **`SPARTAN_PROVIDER_IMAGE_TIMEOUT_SECONDS`:**
  - **Propósito:** Tiempo máximo de espera en segundos para la generación de imagen (los modelos de difusión requieren mayor tiempo).
  - **Default:** `120`.
* **`SPARTAN_AUTH_TIMEOUT_SECONDS`:**
  - **Propósito:** Timeout para comprobaciones de estado de autenticación de proveedores OAuth en Spartan.
  - **Default:** `10`.

---

## 3. Modos de Ejecución Recomendados

| Escenario | `AI_DRY_RUN` | `AI_IMAGE_ENABLED` | `SPARTAN_APP_CLIENT_API_KEY` | Requiere Spartan Corriendo |
|---|---|---|---|---|
| **Desarrollo Offline / Sin IA** | `true` | `false` | No requerida | No |
| **Pruebas de Texto con Spartan** | `false` | `false` | Requerida | Sí (en puerto 20128) |
| **Generación Completa (Texto + PNG)** | `false` | `true` | Requerida | Sí (en puerto 20128) |
| **Ejecución de Pruebas Automáticas (`pytest`)** | `true` (aislado) | `false` | Mockeada en tests | No |
