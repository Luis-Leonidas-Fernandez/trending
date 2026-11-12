# Guía de Resolución de Problemas (Troubleshooting)

Este documento recopila los incidentes, errores y advertencias más habituales durante la instalación, ejecución y operación del **Sistema Trending**, junto con sus causas y soluciones directas.

---

## 1. Problemas de Inicio y Puertos

### Error: `el puerto 8000 ya está en uso` o `el puerto 5173 ya está en uso`
* **Causa:** Hay otra instancia de FastAPI, Uvicorn, Vite o un proceso anterior corriendo en segundo plano.
* **Solución:**
  1. Identificar y matar el proceso en conflicto (macOS/Linux):
     ```bash
     lsof -i :8000
     kill -9 <PID>
     lsof -i :5173
     kill -9 <PID>
     ```
  2. O iniciar en puertos alternativos usando variables de entorno:
     ```bash
     PORT=8010 FRONTEND_PORT=5174 ./run.sh
     ```

### Error: `No encontré Python ejecutable en: .venv/bin/python`
* **Causa:** El entorno virtual no fue creado o fue borrado accidentalmente.
* **Solución:** Ejecutar el instalador automático:
  ```bash
  ./run.sh --install --check
  ```

---

## 2. Problemas con el Pipeline y Estados de Ejecución

### El pipeline reporta estado `draft` en vez de `success`
* **Causa:** Uno de los pasos del pipeline activó un mecanismo de fallback determinístico o no superó todas las auditorías:
  - **Fase 2:** Google Trends no respondió (timeout o error de red) y usó los títulos de fallback.
  - **Fase 3:** Todos los temas descubiertos ya existían y estaban usados en la base de datos.
  - **Fase 5:** Spartan Provider no estaba levantado o faltaba la clave `SPARTAN_APP_CLIENT_API_KEY`, generando contenido con `DryRunAIClient`.
  - **Fase 6:** No se ejecutó la simulación de publicación (`/publish-simulated`).
* **Solución:** Inspeccionar el archivo JSON de la fase afectada en `output/participante-X/` o consultar la sección `errors` y `warnings` en el modal de auditoría de la interfaz web para ver el motivo exacto.

### Error: `El pipeline ya está ejecutándose` (HTTP 409 Conflict)
* **Causa:** Se intentó reutilizar un tema o lanzar una nueva corrida mientras una ejecución previa seguía en curso con `status = "running"`.
* **Solución:**
  1. Si la ejecución quedó trabada, cancelarla desde la UI o mediante `POST /api/pipeline/cancel`.
  2. Si el proceso ya no corre pero el archivo de estado quedó en `running`, reiniciar el estado:
     ```bash
     .venv/bin/python tools/pipeline_state.py reset
     # o vía Make:
     make state-reset
     ```

### El historial web muestra una corrida pero no carga la imagen
* **Causa:**
  1. La generación de imágenes estaba deshabilitada (`AI_IMAGE_ENABLED=false`).
  2. O el archivo físico `.png` en `output/participante-5/assets/` fue borrado.
* **Solución:** Verificar que en `.env` esté `AI_IMAGE_ENABLED=true` y que el archivo referenciado en `image_file` exista en disco.

---

## 3. Problemas con Spartan Provider e Inteligencia Artificial

### Error: `Spartan Gateway requiere SPARTAN_APP_CLIENT_API_KEY`
* **Causa:** Se configuró `AI_DRY_RUN=false` pero no se definió la clave de autenticación en el archivo `.env`.
* **Solución:** Asignar una clave válida en `.env`:
  ```ini
  SPARTAN_APP_CLIENT_API_KEY=tu_clave_aqui
  ```
  O si solo deseas probar localmente sin credenciales, volver a modo offline:
  ```ini
  AI_DRY_RUN=true
  ```

### Error: `Connection refused` conectando a `http://127.0.0.1:20128`
* **Causa:** El servicio auxiliar Spartan Provider no está levantado en la máquina local.
* **Solución:**
  1. Levantar el servicio Spartan Provider en otra terminal en el puerto `20128`.
  2. O verificar su estado desde el backend navegando a `http://127.0.0.1:8000/api/ai/providers/status`.

---

## 4. Problemas con la Base de Datos SQLite

### Error: `FOREIGN KEY constraint failed` (`sqlite3.IntegrityError`)
* **Causa:** Se intentó crear un post referenciando un `topic_id` inexistente o una bitácora referenciando un `post_id` inexistente.
* **Solución:** Asegurarse de que el tema o post haya sido insertado previamente y que la transacción haya hecho commit. En pruebas, utilizar las funciones de los repositorios que manejan la transacción correctamente.

### Base de datos bloqueada: `database is locked`
* **Causa:** Un proceso externo o una herramienta de inspección SQLite (como DB Browser) tiene abierta una transacción sin confirmar.
* **Solución:** Cerrar la aplicación externa que inspecciona `python_backend/database/trending.sqlite`.
