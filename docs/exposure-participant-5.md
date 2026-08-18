# Guía de exposición — Participante 5: Crear contenido con IA

Objetivo: Su responsabilidad es recibir el tema elegido por el Participante 4 y transformarlo en contenido listo para un post: título, caption, descripción, hashtags, prompt de imagen e imagen generada.

## Resumen

“Mi participante se encarga de la fase Crear. Toma el tema seleccionado, llama a Spartan(coneccion a Open AI) para generar el contenido del post y también pide una imagen. Si Spartan o la generación de imagen fallan, el sistema no se cae: queda un output auditable en draft con fallback controlado.”

## Qué problema resuelve

Hasta esta fase el pipeline sólo tiene un tema. El Participante 5 convierte ese tema en una pieza publicable: texto para Instagram, hashtags, prompt visual y archivo de imagen.

## Qué hace técnicamente

| Punto | Explicación para exposición |
|---|---|
| Entrada | Consume el output del Participante 4 (`stage: topic_selector`). |
| Validación | Verifica que exista `selected_topic` con `id`, `title` y `normalized_title`. |
| Texto | Genera `headline`, `caption`, `description`, `hashtags` e `image_prompt`. |
| Provider | Usa Spartan Provider por HTTP. |
| Imagen | Llama a `/v1/images/generations` en Spartan y guarda un PNG. |
| Fallback | Si falla el provider, usa contenido determinístico para no romper el pipeline. |
| Output | Guarda un JSON versionado en `output/participante-5/`. |
| Assets | Guarda imágenes en `output/participante-5/assets/`. |

## Flujo de la fase

1. La fase **Elegir** deja un `selected_topic`.
2. El usuario ejecuta la card **Crear** o el pipeline completo.
3. El backend valida el output del Participante 4.
4. Se llama a Spartan para generar texto del post.
5. Se normaliza el contenido recibido.
6. Se llama a Spartan para generar imagen usando `image_prompt`.
7. Se guarda la imagen como archivo PNG.
8. Se genera el output de `participante-5` para que lo consuma **Publicar**.

## Guia demo

- La card **Crear** en el dashboard.
- Que se ejecuta después de **Elegir**.
- El archivo generado en `output/participante-5/`.
- El archivo PNG generado en `output/participante-5/assets/`.
- Que el JSON contiene `participant: participante-5` y `stage: ai`.
- Los campos `headline`, `caption`, `description`, `hashtags`, `image_prompt` e `image_file`.
- Si hubo fallback, mostrar `used_fallback`, `provider_error`, `image_used_fallback` o `image_error`.

## Archivo principal que lo implementa

```text
/Users/luis/Desktop/PROYECTOS/trending/python_backend/services/ai/ai_service.py
```

Funciones y clases importantes:

```text
process_topic_selector_output()
SpartanAIClient
SpartanImageClient
DryRunAIClient
_normalize_content()
_normalize_caption_text()
_write_image_asset()
```

## Endpoint relacionado

```http
POST /pipeline/create
```

Este endpoint ejecuta la fase `crear` dentro del pipeline.

## Configuración relacionada

Variables relevantes:

```text
AI_PROVIDER=spartan
AI_DRY_RUN=false //significa no usar contenido falso o local
SPARTAN_PROVIDER_BASE_URL=http://127.0.0.1:20128
SPARTAN_PROVIDER_MODEL=gpt-5
SPARTAN_APP_CLIENT_API_KEY=...
AI_IMAGE_ENABLED=true
SPARTAN_PROVIDER_IMAGE_MODEL=...
SPARTAN_PROVIDER_IMAGE_SIZE=1024x1024
SPARTAN_PROVIDER_TIMEOUT_SECONDS=20
SPARTAN_PROVIDER_IMAGE_TIMEOUT_SECONDS=120
```

## Forma del output

Ejemplo simplificado:

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "participant": "participante-5",
  "stage": "ai",
  "status": "success",
  "data": {
    "selected_topic": {
      "id": 46,
      "title": "Banco de la Nación Argentina",
      "normalized_title": "banco de la nacion argentina"
    },
    "headline": "Banco Nación: tendencia del día",
    "caption": "Párrafo 1...

Párrafo 2...

Párrafo 3...",
    "description": "Explicación interna del enfoque editorial del post.",
    "hashtags": ["#BancoNacion", "#BNA", "#Finanzas"],
    "image_prompt": "Diseño editorial para Instagram...",
    "image_file": "output/participante-5/assets/ai_v1_xxxxxxxx.png",
    "provider": "spartan",
    "model": "gpt-5",
    "used_fallback": false,
    "image_used_fallback": false
  },
  "errors": []
}
```

## Reglas del texto generado

| Campo | Regla actual |
|---|---|
| `headline` | Máximo 70 caracteres. |
| `caption` | Entre 500 y 750 caracteres. |
| Párrafos | Caption dividido en 3 párrafos. |
| `description` | Entre 180 y 260 caracteres. |
| `hashtags` | Entre 2 y 4 etiquetas relevantes. |

## Qué significan los estados

| Estado | Qué significa |
|---|---|
| `success` | Texto e imagen se generaron sin fallback. |
| `draft` | Hubo fallback heredado, fallo de provider o fallo de imagen, pero se generó output auditable. |
| `error` | No había tema válido o no se pudo construir un output utilizable. |

## Fallbacks importantes

| Campo | Qué indica |
|---|---|
| `used_fallback` | El texto vino del cliente dry-run o fallback. |
| `provider_error` | Error ocurrido al llamar a Spartan para texto. |
| `image_used_fallback` | La imagen no se generó correctamente. |
| `image_error` | Error ocurrido al llamar a Spartan para imagen. |

## Explicacion final

“Mi fase es donde el tema se convierte finalmente en contenido. Hasta ahora el pipeline descubrió, filtró y eligió un tema. Yo recibo ese `selected_topic` y genero la pieza para Instagram.

Primero valido que el tema tenga estructura correcta. Después llamo a Spartan para pedir un JSON con headline, caption, descripción, hashtags y prompt de imagen. El caption tiene reglas editoriales: debe ser claro, tener tres párrafos y no venir como un bloque de texto.

Luego uso el `image_prompt` para pedir una imagen a Spartan. La respuesta llega en base64, se decodifica y se guarda como PNG dentro de `output/participante-5/assets/`.

Si algo falla, el pipeline no queda ciego. El output registra el error y puede quedar en draft con fallback. Eso permite auditar qué pasó y evita que una caída externa rompa toda la demo.”

## Frase clave para cerrar

“Mi participante transforma el tema elegido en una pieza concreta de contenido: texto, hashtags, prompt visual e imagen lista para publicar.”

## Preguntas 

### ¿Esta fase publica en Instagram?

No. Sólo crea contenido e imagen. La publicación o simulación pertenece al Participante 6.

### ¿Qué pasa si Spartan falla?

Si `AI_FALLBACK_ON_ERROR` está activo, se usa fallback determinístico y el output queda en `draft` con el error registrado.

### ¿Dónde queda guardada la imagen?

En `output/participante-5/assets/`, y el JSON la referencia en `data.image_file`.

### ¿Por qué el caption tiene tres párrafos?

Porque un caption largo en un solo bloque es difícil de leer. La fase normaliza el texto para preservar o reconstruir párrafos.

### ¿Qué consume la fase siguiente?

El Participante 6 consume el JSON de `participante-5`, especialmente `caption`, `hashtags`, `description` e `image_file`.

## Checklist 

- [ ] Ejecutar antes **Descubrir**, **Filtrar** y **Elegir**.
- [ ] Ejecutar **Crear**.
- [ ] Verificar que Spartan esté levantado si se quiere generación real.
- [ ] Abrir el output en `output/participante-5/`.
- [ ] Mostrar `headline`, `caption`, `hashtags` e `image_prompt`.
- [ ] Mostrar `image_file` y el PNG en `output/participante-5/assets/`.
- [ ] Explicar qué significa `success` vs `draft`.
- [ ] Aclarar que la siguiente fase, **Publicar**, toma este contenido.
