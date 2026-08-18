# Guía Windows — Cómo levantar Trending App

Esta guía explica cómo instalar y levantar el proyecto en Windows usando PowerShell. Está pensada para compañeros que sólo necesitan correr la app y probar el pipeline desde el navegador.

## Qué van a levantar

La app tiene dos partes:

| Parte | Para qué sirve | URL |
|---|---|---|
| Backend FastAPI | Ejecuta el pipeline y guarda datos | http://127.0.0.1:8000 |
| Frontend web | Pantalla visual del dashboard | http://127.0.0.1:5173 |

> Importante: si van a generar texto o imágenes reales con IA, Spartan también debe estar levantado aparte en `http://127.0.0.1:20128`.

## Requisitos

Instalar antes:

1. **Python 3.14** o una versión compatible reciente de Python 3.
2. **Git for Windows**.
3. **Visual Studio Code**.
4. Abrir los comandos con **PowerShell**.

Para verificar Python:

```powershell
python --version
```

Para verificar Git:

```powershell
git --version
```

## Antes de compartir el proyecto

No compartir estos archivos o carpetas:

```text
.env
.venv/
python_backend/database/*.sqlite
python_backend/database/*.sqlite-shm
python_backend/database/*.sqlite-wal
```

El archivo `.env` puede tener credenciales reales. Para compañeros, compartir sólo `.env.example` y pedir que cada uno cree su propio `.env`.

Si se comparte por ZIP, revisar manualmente que `.env` no esté dentro del ZIP.

## Paso 1 — Descargar el proyecto

En PowerShell:

```powershell
git clone <URL_DEL_REPOSITORIO>
cd trending
```

Si el proyecto se comparte como ZIP:

1. Descomprimir el ZIP.
2. Entrar a la carpeta `trending`.
3. Abrir PowerShell dentro de esa carpeta.

## Paso 2 — Crear el entorno virtual

Dentro de la carpeta del proyecto:

```powershell
python -m venv .venv
```

Activar el entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, ejecutar una vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Cerrar y abrir PowerShell de nuevo, volver a la carpeta del proyecto y activar:

```powershell
.\.venv\Scripts\Activate.ps1
```

Cuando está activo, debería verse algo parecido a:

```text
(.venv) PS C:\...\trending>
```

## Paso 3 — Instalar dependencias

Con el entorno virtual activo:

```powershell
python -m pip install --upgrade pip
python -m pip install -r python_backend\requirements.txt
```

## Paso 4 — Configurar variables de entorno

El proyecto ya incluye archivos `.env` y `.env.example`.

### Qué es `SPARTAN_APP_CLIENT_API_KEY`

`SPARTAN_APP_CLIENT_API_KEY` es la clave que Trending usa para pedirle permiso a Spartan. No es una clave que se inventa en este proyecto y no debería ser la OpenAI API key directa.

Flujo simple:

```text
Trending App -> SPARTAN_APP_CLIENT_API_KEY -> Spartan -> OpenAI configurado dentro de Spartan
```

Para compañeros, el responsable de Spartan debe generar o entregar una key de cliente para la demo. Cada compañero la pega en su `.env` local.

En `.env.example` debe quedar vacía:

```env
SPARTAN_APP_CLIENT_API_KEY=
```

En el `.env` de cada máquina va el valor real:

```env
SPARTAN_APP_CLIENT_API_KEY=clave_entregada_por_el_responsable_de_spartan
```

> No poner acá la OpenAI API key personal. La OpenAI key queda configurada dentro de Spartan, no en el proyecto Trending que se comparte.

### Variables del `.env`, una por una

| Variable | Qué significa | Qué poner |
|---|---|---|
| `PYTHON_DB_FILE` | Ruta de la base SQLite local. | `./python_backend/database/trending.sqlite` |
| `AI_PROVIDER` | Provider que usa Trending para IA. | `spartan` |
| `AI_DRY_RUN` | Si usa contenido de prueba en vez de IA real. | `true` para demo sin IA, `false` para IA real. |
| `AI_FALLBACK_ON_ERROR` | Si el pipeline debe seguir con fallback cuando falla la IA. | `true` |
| `AI_IMAGE_ENABLED` | Si intenta generar imagen real. | `false` para demo simple, `true` para IA real. |
| `SPARTAN_PROVIDER_BASE_URL` | URL local de Spartan. | `http://127.0.0.1:20128` |
| `SPARTAN_PROVIDER_MODEL` | Modelo de texto que Trending pide a Spartan. | `gpt-5` o el modelo configurado en Spartan. |
| `SPARTAN_PROVIDER_IMAGE_MODEL` | Modelo de imagen. Si queda vacío, usa el modelo principal. | Vacío o el modelo de imagen configurado en Spartan. |
| `SPARTAN_PROVIDER_IMAGE_SIZE` | Tamaño de imagen. | `1024x1024` |
| `SPARTAN_PROVIDER_TIMEOUT_SECONDS` | Tiempo máximo para texto. | `20` |
| `SPARTAN_PROVIDER_IMAGE_TIMEOUT_SECONDS` | Tiempo máximo para imagen. | `120` |
| `SPARTAN_AUTH_TIMEOUT_SECONDS` | Tiempo máximo para chequear auth/providers. | `10` |
| `SPARTAN_APP_CLIENT_API_KEY` | Key de cliente entregada por Spartan. | Vacía en `.env.example`; real sólo en `.env`. |

Para una prueba simple sin IA real, usar:

```env
AI_PROVIDER=spartan
AI_DRY_RUN=true
AI_IMAGE_ENABLED=false
```

Para usar Spartan/OpenAI real, usar algo como:

```env
AI_PROVIDER=spartan
AI_DRY_RUN=false
AI_IMAGE_ENABLED=true
SPARTAN_PROVIDER_BASE_URL=http://127.0.0.1:20128
SPARTAN_PROVIDER_MODEL=gpt-5
SPARTAN_PROVIDER_IMAGE_SIZE=1024x1024
SPARTAN_PROVIDER_TIMEOUT_SECONDS=20
SPARTAN_PROVIDER_IMAGE_TIMEOUT_SECONDS=120
SPARTAN_APP_CLIENT_API_KEY=clave_entregada_por_el_responsable_de_spartan
```

> No compartir API keys en grupos, capturas o commits. Cada máquina debe configurar su propia clave.

## Paso 5 — Levantar el backend

En una terminal PowerShell, con `.venv` activo:

```powershell
python -m uvicorn python_backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Dejar esta terminal abierta.

Probar backend en el navegador:

```text
http://127.0.0.1:8000/api/health
```

También pueden abrir la documentación automática:

```text
http://127.0.0.1:8000/docs
```

## Paso 6 — Levantar el frontend

Abrir una segunda terminal PowerShell en la misma carpeta del proyecto.

Activar el entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Levantar servidor web estático:

```powershell
python -m http.server 5173 --bind 127.0.0.1 --directory frontend
```

Dejar esta segunda terminal abierta.

Abrir la app en el navegador:

```text
http://127.0.0.1:5173
```

## Paso 7 — Probar la app

En el dashboard:

1. Tocar **Ejecutar todo**.
2. Tocar **Correr selección**.
3. Esperar que pasen las cards:
   - Descubrir
   - Filtrar
   - Elegir
   - Crear
   - Publicar
   - Medir
4. Revisar el post final.
5. Entrar a **Historial** para ver corridas anteriores.

## Cómo apagar la app

En cada terminal donde quedó corriendo un servidor:

```text
Ctrl + C
```

Si pregunta si querés terminar el proceso, responder:

```text
S
```

o:

```text
Y
```

según el idioma de Windows.

## Problemas comunes

### PowerShell no deja activar `.venv`

Ejecutar:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Después cerrar y abrir PowerShell otra vez.

### El puerto 8000 o 5173 está ocupado

Cerrar otras terminales abiertas del proyecto. Si sigue ocupado, reiniciar la PC suele resolverlo para una demo rápida.

### El backend responde, pero la IA falla

Verificar si Spartan está levantado:

```text
http://127.0.0.1:20128/health
```

Si no responde, levantar Spartan o usar modo prueba:

```env
AI_DRY_RUN=true
AI_IMAGE_ENABLED=false
```

### La página abre pero no corre el pipeline

Verificar que el backend esté abierto en:

```text
http://127.0.0.1:8000/api/health
```

Si no responde, falta levantar FastAPI.

## Comandos rápidos

Terminal 1 — Backend:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn python_backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 — Frontend:

```powershell
.\.venv\Scripts\Activate.ps1
python -m http.server 5173 --bind 127.0.0.1 --directory frontend
```

URLs:

```text
Backend: http://127.0.0.1:8000/api/health
Docs:    http://127.0.0.1:8000/docs
App:     http://127.0.0.1:5173
```
