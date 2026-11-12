# Guía de Instalación y Despliegue Local

Esta guía describe los requisitos de sistema y los pasos necesarios para instalar y ejecutar el proyecto **Trending** en entornos **macOS**, **Linux** y **Windows**.

---

## 1. Requisitos Previos

* **Python:** Versión oficial recomendada `Python 3.14.5` (compatible con versiones recientes de Python 3.11+).
* **Git:** Para clonar y gestionar el repositorio.
* **Make:** (Opcional, preinstalado en macOS y Linux).
* **Navegador Web:** Chrome, Firefox, Safari o Edge para interactuar con el Dashboard en `http://127.0.0.1:5173`.
* **Spartan Provider:** (Opcional) Necesario únicamente si se desea generar texto e imágenes reales con IA en lugar de usar el modo offline dry-run. Debe correr en `http://127.0.0.1:20128`.

---

## 2. Instalación en macOS y Linux

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/Luis-Leonidas-Fernandez/trending.git
cd trending
```

### Paso 2: Instalación Automática y Verificación
El script unificado [`run.sh`](file:///Users/luis/desktop/PROYECTOS/trending/run.sh) se encarga de crear el entorno virtual `.venv`, instalar las dependencias exactas desde [`python_backend/requirements.txt`](file:///Users/luis/desktop/PROYECTOS/trending/python_backend/requirements.txt) e inicializar la base de datos SQLite:

```bash
./run.sh --install --check
```
*Si tienes `make` disponible, puedes ejecutar equivalentemente:*
```bash
make install
```

### Paso 3: Configurar Variables de Entorno
Copia la plantilla de entorno:
```bash
cp .env.example .env
```
*(Consulta [configuration.md](file:///Users/luis/desktop/PROYECTOS/trending/docs/operations/configuration.md) para detalles sobre las variables).*

### Paso 4: Levantar la Aplicación
Para iniciar el servidor FastAPI (puerto 8000) y el Frontend Web estático (puerto 5173) en simultáneo:
```bash
./run.sh
# o con Make:
make dev
```

La consola confirmará el inicio de ambos servicios:
```text
[trending] Levantando FastAPI en http://127.0.0.1:8000
[trending] Levantando UI web en http://127.0.0.1:5173
[trending] API docs: http://127.0.0.1:8000/docs
[trending] UI: http://127.0.0.1:5173
```
Presiona `Ctrl + C` para detener ambos servicios de manera limpia.

---

## 3. Instalación en Windows (PowerShell)

Para usuarios de Windows, se recomienda consultar la guía especializada con capturas en [`docs/windows-setup-guide.md`](file:///Users/luis/desktop/PROYECTOS/trending/docs/windows-setup-guide.md).

### Resumen rápido para PowerShell:
1. Abrir PowerShell en el directorio del proyecto:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r python_backend\requirements.txt
```
2. Crear archivo `.env`:
```powershell
Copy-Item .env.example .env
```
3. Levantar FastAPI en una terminal:
```powershell
python -m uvicorn python_backend.main:app --host 127.0.0.1 --port 8000 --reload
```
4. Levantar la UI estática en otra terminal:
```powershell
python -m http.server 5173 --bind 127.0.0.1 --directory frontend
```
5. Abrir el navegador en `http://127.0.0.1:5173`.

---

## 4. Opciones Avanzadas de `run.sh`

El script [`run.sh`](file:///Users/luis/desktop/PROYECTOS/trending/run.sh) ofrece múltiples banderas operativas:

* `./run.sh --api-only`: Levanta exclusivamente el backend FastAPI sin el servidor web estático.
* `./run.sh --with-pipeline`: Ejecuta automáticamente las Fases 2, 3 y 4 antes de levantar el servidor.
* `./run.sh --no-reload`: Desactiva la recarga automática en caliente de Uvicorn (útil para mediciones de rendimiento).
* `PORT=8010 FRONTEND_PORT=5174 ./run.sh`: Permite personalizar los puertos de escucha para evitar conflictos.

---

## 5. Ejecución de Pruebas Automatizadas

Para validar que la instalación es correcta y que todos los componentes responden adecuadamente:
```bash
# Ejecutar todas las suites de prueba:
make test
# o directamente con pytest:
.venv/bin/python -m pytest -q

# Ejecutar el linter de código (Ruff):
make lint
```
