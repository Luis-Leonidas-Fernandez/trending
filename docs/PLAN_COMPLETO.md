# Plan completo — Sistema IA de Posts Trending para Instagram v1

> Fuente original: `/Users/luis/Desktop/plan_actualizado_trending_instagram.docx`

## Objetivo del proyecto

Crear un sistema automático que:

- busque tendencias en Google Trends
- valide temas no repetidos
- genere imágenes y captions usando inteligencia artificial en la nube
- publique automáticamente en Instagram

## Tecnologías

- **Frontend:** Astro + TailwindCSS
- **Backend:** Python + FastAPI
- **Base de datos:** SQLite
- **IA en nube:** OpenAI / Gemini / Replicate
- **Scheduler futuro:** APScheduler o tareas programadas en Python

## Flujo del sistema

1. El usuario solicita crear un post trending.
2. El backend consulta Google Trends usando IA o APIs externas.
3. La IA devuelve un JSON estructurado con temas trending.
4. El sistema revisa si los temas ya existen en SQLite.
5. Los temas válidos se guardan en la base de datos.
6. El sistema selecciona automáticamente el primer tema válido.
7. La IA genera una imagen viral, caption, hashtags y descripción.
8. El post generado se guarda en SQLite.
9. El sistema publica automáticamente en Instagram.

## División del proyecto entre hasta 7 participantes

### Participante 1 — Backend con Python, FastAPI y SQLite

- Configurar Python + FastAPI
- Configurar SQLite
- Crear tablas principales
- Crear estructura de rutas y controladores
- Crear endpoints base

### Participante 2 — Búsqueda en Google Trends y normalización JSON

- Integrar Google Trends
- Convertir resultados a JSON estructurado
- Crear servicio `trends.service.js`
- Devolver título, fuente, categoría y fecha
- Enviar datos al backend

### Participante 3 — Validación de duplicados y guardado de tema

- Detectar temas duplicados
- Normalizar títulos
- Guardar temas válidos en SQLite

### Participante 4 — Selector automático de temas

- Seleccionar automáticamente el primer tema válido
- Aplicar filtros básicos
- Preparar tema para generación IA

### Participante 5 — Generador IA de imagen

- Generar imagen viral
- Generar caption para Instagram
- Generar hashtags
- Configurar tamaño y calidad de imagen
- Integrar APIs IA en nube

### Participante 6 — Gestiona publicación en Instagram

- Integrar Instagram Graph API
- Guardar post generado
- Publicar imágenes automáticamente
- Manejar estados de publicación
- Guardar logs de publicación

### Participante 7 — Frontend Astro

- Crear dashboard
- Mostrar tendencias
- Mostrar posts generados
- Mostrar estado de publicaciones
- Crear configuración visual

## Tablas recomendadas SQLite

### Tabla `trending_topics`

- `id`
- `title`
- `normalized_title`
- `source`
- `score`
- `used`
- `created_at`

### Tabla `generated_posts`

- `id`
- `topic_id`
- `image_url`
- `caption`
- `description`
- `hashtags`
- `status`
- `created_at`

### Tabla `publication_logs`

- `id`
- `post_id`
- `platform`
- `status`
- `response_json`
- `error_message`
- `created_at`

## MVP recomendado

- Buscar tendencias desde Google Trends
- Guardar temas en SQLite
- Evitar temas repetidos
- Seleccionar automáticamente un tema
- Generar imagen y caption usando IA
- Publicar automáticamente en Instagram
- Visualizar resultados desde Astro
