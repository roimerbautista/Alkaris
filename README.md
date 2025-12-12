# Alkaris

Alkaris es un asistente por voz en Python orientado principalmente al control de reproducción en Spotify y con funcionalidades adicionales (YouTube, clima, chistes, identificación de canciones, captura y descripción de pantalla/audio, avatar 3D y control por gestos). Está diseñado para escuchar comandos por micrófono, procesarlos (reglas / matching) y, cuando corresponde, usar una API generativa para manejar consultas abiertas y generar respuestas en lenguaje natural con síntesis de voz.

---

## Contenido y estructura del repositorio

- `.gitignore`
- `README.md` (actual — este documento propuesto)
- `main.py` — punto de entrada; crea la instancia `SpotifyVoiceControl` y arranca la escucha continua.
- `requirements.txt` — dependencias del proyecto (revisar para versiones exactas).
- `spotify_voice_control_config.json` — configuración persistente (voz seleccionada, nombre del asistente, umbral de energía, etc.).
- `config/` — gestor de configuración (ej. `ConfigManager`).
- `core/`
  - `app_core.py` — clase principal `SpotifyVoiceControl` con la mayor parte de la lógica: reconocimiento de voz, manejo de comandos, integración con Spotify, manejo de avatar y control gestual, integración con la API generativa (Gemini), TTS y fallbacks.
  - `command_handler.py` — mapeo / lógica para ejecutar comandos concretos.
- `modules/` — controladores modulares (ejemplos detectados):
  - `modules/spotify/spotify_controller.py` — integración con la API de Spotify.
  - `modules/youtube/youtube_controller.py` — búsqueda y reproducción en YouTube.
  - `modules/audio/audio_manager.py` — gestión/transformación de audio.
  - `modules/weather/weather_service.py` — consultas meteorológicas.
  - `modules/jokes/joke_generator.py` — generador de chistes.
  - `modules/avatar/avatar_integration.py` — integración avatar 3D (visualización, logs, eventos).
  - `modules/gestures/gesture_control.py` — control por gestos.
  - `modules/media_players/` — integración con reproductores (MPV, VLC).
- `gui/` — implementaciones de interfaz (en la versión actual el GUI tkinter fue deshabilitado y reemplazado por el avatar).
- `utils/` — utilidades, normalización de audio, helpers, etc.

---

## Tecnologías y librerías (utilizadas / importadas en `core/app_core.py`)

Observadas en el código:
- Python 3.x
- Reconocimiento de voz: `speech_recognition`
- Captura/playback de audio: `sounddevice`, `pygame`, `scipy.io.wavfile.write`, `soundfile` (sf), `librosa`
- TTS local / fallback: `pyttsx3`
- Integración Spotify: `spotipy` (y `spotipy.oauth2.SpotifyOAuth`)
- YouTube / Google APIs: `googleapiclient.discovery` (Google API client)
- Generative AI (Gemini): `google.generativeai` (usa cliente/configuración, modelos y Live API)
- Manejo de imágenes/pantalla: `PIL.ImageGrab` (Pillow)
- Utilidades: `python-dotenv` (`load_dotenv`), `unidecode`, `Levenshtein`, `requests`, `numpy`, `scipy`, `threading`, `tkinter` (parte removida), `tempfile`, `os`, `re`.
- Otros: módulos propios dentro de `modules/` y `utils/`.

Revisa `requirements.txt` para la lista y versiones concretas antes de instalar.

---

## Funcionalidades principales

- Escucha continua por micrófono y detección de activación por nombre del asistente (con generación de variaciones fonéticas del nombre para mayor robustez).
- Detección y normalización de comandos (fuzzy matching con Levenshtein para mapear sinónimos).
- Control completo de Spotify: autenticar, reproducir/pausar, siguiente/anterior, elegir dispositivos, manejar listas de reproducción, favoritos y volumen.
- Búsqueda y reproducción de YouTube (con posibilidad de usar MPV o VLC).
- Comandos del asistente: listar comandos, cambiar nombre/voz/acento, contar chistes, mostrar playlists, gestionar modo aleatorio/repetición, etc.
- Captura de pantalla y envío a la API generativa para describir lo que aparece.
- Captura de audio y envío a la API generativa para analizar o identificar canciones.
- Control gestual (módulo separado que corre en hilo).
- Avatar 3D integrado para mostrar estado, logs y visualizaciones de música.
- Persistencia de configuración en `spotify_voice_control_config.json`.
- Manejo de errores con log en archivo `error_log.txt`.
- Fallback de TTS a pyttsx3 / AudioManager si la voz generativa falla.

---

## Uso de IA / Integración con Gemini (confirmado)

Sí: el proyecto integra la API generativa (Gemini) y la usa de varias maneras:

- Lectura de variables de entorno:
  - `GEMINI_API_KEY` — imprescindible (el código levanta una excepción si no está presente).
  - También usa `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `YOUTUBE_API_KEY`, `WEATHERMAP_API_KEY`.

- Inicialización y configuración:
  - Se importa `google.generativeai` (alias `genai`) y `types`.
  - `genai.configure(api_key=...)` y `self.model = genai.GenerativeModel('gemini-pro')` (crea un modelo/cliente).
  - Además hay uso de un cliente con llamadas tipo `self.client.models.generate_content(...)` y `self.client.files.upload(...)` (subida de archivos: audio/imagen).

- Uso para texto / consultas abiertas:
  - Cuando un comando no es reconocido como comando conocido o es una consulta válida (patrones tipo 'dime', 'cuéntame', 'qué', etc.), el texto se envía a la API generativa (`procesar_comando_no_reconocido`) para obtener una respuesta en lenguaje natural y luego devolverla por TTS.

- Uso con archivos multimedia:
  - Soporta subir imágenes (captura de pantalla) y audios (capturados con `sounddevice`) a la API generativa para que los procese (describir pantalla, analizar audio, identificar canciones, etc.). Tras procesar, limpia y elimina archivos temporales.

- Gemini Live API (síntesis de voz):
  - Hay una implementación asíncrona (`_responder_con_audio_gemini_async`) que intenta conectarse al "Gemini Live API" (`client.aio.live.connect`) para generar respuesta en modalidad AUDIO.
  - Se configura `LiveConnectConfig` con `response_modalities=["AUDIO"]` y `SpeechConfig` → `VoiceConfig`, y se graba la salida WAV recibida para reproducirla con `pygame`.
  - Si la síntesis/Live API falla, hay fallback a pyttsx3 / `AudioManager.responder_con_audio(...)`.

- Modelos mencionados (en código):
  - `gemini-pro` (creación de `GenerativeModel`)
  - `gemini-2.0-flash` (usado para `models.generate_content` y para sesiones Live). Nota: los nombres de modelos deben confirmarse según la documentación pública de la API que uses.

- Manejo de errores y fallback:
  - Captura excepciones al usar Gemini y vuelve a TTS local si la conexión falla o se produce error HTTP.
  - Limpieza de archivos temporales tras uso.

En resumen: sí hay integración con Gemini, tanto para generación de texto como para síntesis de voz y análisis multimedia. El proyecto depende de una API key (`GEMINI_API_KEY`) y usa la librería oficial (o un cliente) para comunicarse con los endpoints generativos y Live.

---

## Variables de entorno requeridas (mínimo observado)

- GEMINI_API_KEY (obligatorio según el código)
- SPOTIFY_CLIENT_ID
- SPOTIFY_CLIENT_SECRET
- YOUTUBE_API_KEY
- WEATHERMAP_API_KEY

Se utiliza `python-dotenv` para cargar `.env`, por lo que puedes poner estas variables en un archivo `.env` local que no debe subirse al repositorio.

---

## Instalación y ejecución (resumen)

1. Clona el repo:
   git clone https://github.com/roimerbautista/Alkaris.git
2. Crea y activa un entorno virtual:
   python -m venv venv
   source venv/bin/activate  # Linux / macOS
   venv\Scripts\activate     # Windows
3. Instala dependencias:
   pip install -r requirements.txt
4. Configura variables de entorno (`.env`) con las claves necesarias.
5. Ajusta `spotify_voice_control_config.json` si quieres cambiar voz, nombre o umbral.
6. Ejecuta:
   python main.py

Nota: En Windows la configuración de voz base usa un identificador SAPI registrado en el registro (ej.: `TTS_MS_ES-MX_SABINA_11.0`), por lo que la selección de voz puede depender del sistema operativo.

---

## Conclusiones

- El código integra una capa de IA (Gemini) que se usa para:
  - Responder preguntas abiertas.
  - Analizar/describir imágenes y audios.
  - Generar respuestas habladas usando la Live API (con fallback local).
- El asistente está orientado a español (configuración por defecto y voces detectadas), pero tiene opciones de acento/voz.
- El flujo principal empieza en `main.py` que invoca `SpotifyVoiceControl.iniciar_escucha_continua()` y mantiene el loop principal hasta que se interrumpe.
