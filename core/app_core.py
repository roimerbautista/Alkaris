
import base64  # Moved import base64 to the top
import json
import os
import traceback
import threading
import tempfile
import time
import Levenshtein as lv
import pygame
import requests
import pyttsx3  # Keeping pyttsx3 import for comparison/fallback, can be removed if purely Gemini voice is desired
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import speech_recognition as sr
from googleapiclient.discovery import build
import tkinter as tk
from threading import Thread, Lock
from itertools import groupby
import unidecode
import re
import librosa
import soundfile as sf
import numpy as np
from dotenv import load_dotenv
from PIL import ImageGrab  # For screen capture
import sounddevice as sd  # For audio capture
from scipy.io.wavfile import write  # For saving audio
import asyncio # Import asyncio for async operations with Gemini Live API
import wave # Import wave for handling WAV audio files for Gemini Live API

from modules.audio.audio_manager import AudioManager # Keep AudioManager for potential fallback or other audio management
from modules.spotify.spotify_controller import SpotifyController
from modules.youtube.youtube_controller import YoutubeController
from modules.gestures.gesture_control import ControlGestual
from config.config_manager import ConfigManager
from modules.weather.weather_service import WeatherService
from modules.jokes.joke_generator import JokeGenerator
from modules.media_players.mpv_player import MPVPlayer
from modules.media_players.vlc_player import VLCPlayer
from utils.audio_utils import normalizar_audio
from gui.main_gui import MainGUI  # Importamos MainGUI aquí

from google import genai
from google.genai import types # Import types for Gemini API configuration


class SpotifyVoiceControl:


    def __init__(self):
        load_dotenv_result = load_dotenv()
        if not load_dotenv_result:
            print("Error loading .env file. Check if it exists and is correctly configured.")

        self.SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
        self.SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
        self.WEATHERMAP_API_KEY = os.getenv('WEATHERMAP_API_KEY')
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

        if not self.GEMINI_API_KEY:
            print("GEMINI_API_KEY not found in environment variables.")
            raise ValueError("GEMINI_API_KEY not found in environment variables.")

        self.client = genai.Client(api_key=self.GEMINI_API_KEY) # Initialize Gemini client

        pygame.mixer.init()
        self.audio_lock = Lock()
        self.config_manager = ConfigManager("spotify_voice_control_config.json")
        config = self.config_manager.load_config()

        self.asistente_nombre = config.get("asistente_nombre", "Alkaris")
        self.acento_asistente = config.get("acento_asistente", 'es')
        self.energy_threshold = config.get("energy_threshold", 5000)

        self.audio_manager = AudioManager(self.acento_asistente, self.audio_lock) # Keep AudioManager, might be useful for fallback
        self.spotify_controller = SpotifyController(self.SPOTIFY_CLIENT_ID, self.SPOTIFY_CLIENT_SECRET, self.audio_manager)
        self.mpv_player = MPVPlayer() # Instantiate MPVController
        self.vlc_player = VLCPlayer() # Instantiate VLCPlayer
        self.youtube_controller = YoutubeController(self.YOUTUBE_API_KEY, self.mpv_player, self.vlc_player, self.audio_manager)
        self.weather_service = WeatherService(self.WEATHERMAP_API_KEY)
        self.joke_generator = JokeGenerator()

        self.engine = pyttsx3.init() # Keep pyttsx3 engine init, could be used as fallback
        selected_voice_id = config.get("selected_voice_index", None)
        if selected_voice_id:
            self.engine.setProperty('voice', selected_voice_id) # Keep pyttsx3 voice setting, potentially for fallback

        self.control_gestual = ControlGestual(self)
        self.iniciar_control_gestual()

        self.error_log_file = "error_log.txt"
        self.is_internet_available = True
        self.energy_threshold = 5000
        self.energy_threshold_slider = None # Inicializado en init_gui
        self.label_nombre_asistente = None # Inicializado en init_gui
        self.entry_cancion = None # Inicializado en init_gui
        self.canvas = None # Inicializado en init_gui
        self.estado_circulo = None # Inicializado en init_gui


        self.main_gui = MainGUI(self) # Inicializamos la GUI aquí, pasando la instancia de SpotifyVoiceControl
        self.root = self.main_gui.root # Obtenemos la referencia al root de Tkinter

        self.main_gui.init_ui() # Inicializar los elementos de la GUI usando el método en MainGUI
        self.load_config_to_gui() # Cargar la configuración a los elementos de la GUI


    def load_config_to_gui(self):
        """Carga la configuración a los elementos de la GUI."""
        if self.energy_threshold_slider:
            self.energy_threshold_slider.set(self.energy_threshold)
        if self.label_nombre_asistente:
            self.label_nombre_asistente.config(text=f"Asistente: {self.asistente_nombre}")


    def iniciar_en_hilo(self):
        """
        Inicia la lógica principal en un hilo separado para no bloquear la GUI.
        """
        Thread(target=self.ejecutar, daemon=True).start()

    def actualizar_estado_escucha(self, escuchando):
        """
        Actualiza el color del indicador en la GUI para mostrar si está escuchando.
        """
        color = "green" if escuchando else "red"
        if self.canvas and self.estado_circulo:
            self.canvas.itemconfig(self.estado_circulo, fill=color)

    def on_closing(self):
        """
        Acciones a realizar al cerrar la ventana.
        """
        print("Cerrando aplicación...")
        self.root.destroy()


    def autenticar_spotify(self):
        self.spotify_controller.autenticar_spotify(self.verificar_cuenta_premium, self.mostrar_dispositivos_disponibles)

    def verificar_cuenta_premium(self):
        return self.spotify_controller.verificar_cuenta_premium()

    def mostrar_dispositivos_disponibles(self):
        self.spotify_controller.mostrar_dispositivos_disponibles()

    def precalentar_spotify(self):
        self.spotify_controller.precalentar_spotify()

    def ajustar_volumen_para_escuchar(self):
        self.spotify_controller.ajustar_volumen_para_escuchar()

    def restaurar_volumen_original(self):
        self.spotify_controller.restaurar_volumen_original()

    def limpiar_comando(self, comando):
        palabras = comando.split()
        resultado = [k for k, g in groupby(palabras)]
        return ' '.join(resultado)

    def reducir_ruido(self, audio):
        return self.audio_manager.reducir_ruido(audio)

    def capture_screen(self):
        """Captures the screen and saves it to a temporary file."""
        try:
            screenshot = ImageGrab.grab()
            temp_filename = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
            screenshot.save(temp_filename)
            print(f"Screenshot saved to {temp_filename}")
            return temp_filename
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None

    def capture_audio(self, duration=5, samplerate=44100):
        """Captures audio from the microphone and saves it to a temporary file."""
        try:
            print("Recording audio...")
            recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
            sd.wait()
            temp_filename = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
            write(temp_filename, samplerate, recording)
            print(f"Audio saved to {temp_filename}")
            return temp_filename
        except Exception as e:
            print(f"Error capturing audio: {e}")
            return None

    def generar_variaciones_nombre(self, nombre):
        """
        Genera automáticamente variaciones fonéticas y de pronunciación para cualquier nombre del asistente.
        Esto permite un reconocimiento más flexible independientemente del nombre configurado.
        """
        nombre_lower = nombre.lower()
        variaciones = [nombre_lower]
        
        # Remover acentos para variaciones
        nombre_sin_acentos = unidecode.unidecode(nombre_lower)
        if nombre_sin_acentos != nombre_lower:
            variaciones.append(nombre_sin_acentos)
        
        # Variaciones específicas para nombres comunes
        if nombre_lower == "alkaris":
            variaciones.extend([
                "al karis", "al caris", "alcaris", "al kari", "al cari",
                "alkari", "al karis", "al karis", "al caris"
            ])
        
        # Separaciones comunes con espacios
        if len(nombre_lower) > 3:
            # Separar después de 2 caracteres
            if len(nombre_lower) > 2:
                variaciones.append(f"{nombre_lower[:2]} {nombre_lower[2:]}")
            # Separar después de 3 caracteres
            if len(nombre_lower) > 3:
                variaciones.append(f"{nombre_lower[:3]} {nombre_lower[3:]}")
            # Separación por mitad
            mitad = len(nombre_lower) // 2
            variaciones.append(f"{nombre_lower[:mitad]} {nombre_lower[mitad:]}")
        
        # Variaciones fonéticas comunes
        variaciones_foneticas = {
            'k': ['c', 'qu'],
            'c': ['k', 'qu'],
            'qu': ['k', 'c'],
            'z': ['s'],
            's': ['z'],
            'b': ['v'],
            'v': ['b'],
            'y': ['i', 'll'],
            'll': ['y', 'i'],
            'j': ['g'],
            'g': ['j'],
            'r': ['rr'],
            'rr': ['r']
        }
        
        # Aplicar variaciones fonéticas
        variaciones_base = variaciones.copy()
        for variacion_base in variaciones_base:
            for original, reemplazos in variaciones_foneticas.items():
                if original in variacion_base:
                    for reemplazo in reemplazos:
                        nueva_variacion = variacion_base.replace(original, reemplazo)
                        variaciones.append(nueva_variacion)
        
        # Variaciones con errores comunes de reconocimiento
        variaciones_base = variaciones.copy()
        for variacion_base in variaciones_base:
            # Agregar/quitar vocales al final
            if variacion_base.endswith(('a', 'e', 'i', 'o', 'u')):
                variaciones.append(variacion_base[:-1])  # Sin vocal final
            else:
                for vocal in ['a', 'e', 'i', 'o', 'u']:
                    variaciones.append(variacion_base + vocal)  # Con vocal agregada
        
        # Variaciones con 'al' al inicio (muy común en reconocimiento de voz)
        variaciones_base = variaciones.copy()
        for variacion_base in variaciones_base:
            if not variacion_base.startswith('al'):
                variaciones.append(f"al {variacion_base}")
                variaciones.append(f"al{variacion_base}")
        
        # Eliminar duplicados, espacios extra y retornar
        variaciones_limpias = []
        for var in variaciones:
            var_limpia = ' '.join(var.split())  # Eliminar espacios extra
            if var_limpia and var_limpia not in variaciones_limpias:
                variaciones_limpias.append(var_limpia)
        
        return variaciones_limpias


    def reconocimiento_de_voz(self, timeout=50):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone(device_index=0) as source:
                current_threshold = self.energy_threshold_slider.get()
                recognizer.energy_threshold = current_threshold
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
                self.actualizar_estado_escucha(True)
                print("Escuchando...")
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
                self.actualizar_estado_escucha(False)

            processed_audio_data, processed_sample_rate = self.reducir_ruido(audio)
            if processed_audio_data is None:
                return False, ""

            temp_filename = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                    temp_filename = tmpfile.name
                sf.write(temp_filename, processed_audio_data, processed_sample_rate)

                with sr.AudioFile(temp_filename) as source_file:
                    processed_audio = recognizer.record(source_file)

                comando_completo = recognizer.recognize_google(processed_audio, language="es-ES").lower()
                print(f"Comando reconocido: {comando_completo}")

                comando_completo = self.limpiar_comando(comando_completo)

            finally:
                if temp_filename:
                    os.remove(temp_filename)

            comando_completo = comando_completo.replace("de tener", "detener")
            
            # Generar variaciones automáticamente para el nombre actual
            variaciones_nombre = self.generar_variaciones_nombre(self.asistente_nombre)
            
            print(f"Buscando variaciones de '{self.asistente_nombre}': {variaciones_nombre[:5]}...")  # Mostrar solo las primeras 5
            
            nombre_encontrado = None
            for variacion in variaciones_nombre:
                if variacion in comando_completo:
                    nombre_encontrado = variacion
                    print(f"Nombre encontrado: '{variacion}'")
                    break
            
            if nombre_encontrado:
                comando = comando_completo.replace(nombre_encontrado, "", 1).strip()
                return True, comando
            else:
                print(f"El nombre del asistente no fue mencionado: {comando_completo}")
                return False, ""

        except sr.UnknownValueError as e:
            print("No se pudo entender el audio, posiblemente solo fue ruido:", e)
            self.actualizar_estado_escucha(False)
            return False, ""
        except sr.RequestError as e:
            print("No se pudo solicitar resultados desde el servicio de Google Speech Recognition:", e)
            self.actualizar_estado_escucha(False)
            return False, ""
        except Exception as e:
            print(f"Error al procesar el audio: {e}")
            self.actualizar_estado_escucha(False)
            return False, ""

    def first_time_setup(self):
        """
        Configuración inicial en la primera ejecución.
        Se programa para ejecutarse después de que la interfaz gráfica esté completamente cargada.
        """
        self.root.after(100, self.presentar_aplicacion)
        self.root.after(100, self.save_config)

    def presentar_aplicacion(self):
        """
        Presenta la aplicación al usuario, explicando brevemente su propósito y las características disponibles,
        así como el estado actual de desarrollo.
        """
        introduccion = """
        Hola, soy Bahuro, el creador de apifusionx. Esta aplicación está diseñada para permitirte controlar Spotify con tu voz,
        así como disfrutar de otras funcionalidades. Con apifusionx, no solo puedes reproducir tu música favorita, sino que también
        puedes ver videos en YouTube, consultar el clima, escuchar un chiste para alegrar tu día o incluso cambiar mi nombre si así lo deseas.
        Actualmente, apifusionx está en desarrollo, lo que significa que podrías encontrarte con algunas imperfecciones.
        Estoy trabajando constantemente para mejorar y actualizar la aplicación. Cualquier comentario o sugerencia que puedas
        ofrecer será bien recibido y muy apreciado. ¡Espero que disfrutes utilizando apifusionx tanto como yo disfruté creándola!
        """
        self.responder_con_audio(introduccion)

    def save_config(self):
        config_data = {
            "first_run": False,
            "selected_voice_index": self.engine.getProperty('voice'),
            "asistente_nombre": self.asistente_nombre,
            "acento_asistente": self.acento_asistente,
            "energy_threshold": self.energy_threshold_slider.get()
        }
        self.config_manager.save_config(config_data)


    def load_config(self):
        config_data = self.config_manager.load_config()
        if config_data:
            self.asistente_nombre = config_data.get("asistente_nombre", self.asistente_nombre)
            self.acento_asistente = config_data.get("acento_asistente", self.acento_asistente)
            selected_voice_id = config_data.get("selected_voice_index", None)
            energy_threshold = config_data.get("energy_threshold", 5000)

            if selected_voice_id:
                self.engine.setProperty('voice', selected_voice_id)
            if self.energy_threshold_slider:
                self.energy_threshold_slider.set(energy_threshold)


    def set_voice(self, voice_index):
        voices = self.engine.getProperty('voices')
        if 0 <= voice_index < len(voices):
            self.engine.setProperty('voice', voices[voice_index].id)
            print("Voz cambiada correctamente.")
        else:
            print("Índice de voz no válido.")

    def cambiar_voz_asistente(self):
        voces = self.engine.getProperty('voices')
        print("Voces disponibles:")
        for i, voz in enumerate(voces):
            genero = "Masculino" if "male" in voz.name.lower() else "Femenino"
            print(f"Índice: {i}, Nombre: {voz.name}, Género: {genero}")

        try:
            indice_voz = int(input("Ingresa el índice de la voz deseada: "))
            if 0 <= indice_voz < len(voces):
                self.engine.setProperty('voice', voces[indice_voz].id)
                self.responder_con_audio("Voz cambiada correctamente.")
                self.set_voice(indice_voz)
                self.save_config()
            else:
                print("Índice fuera de rango. No se cambió la voz.")
        except ValueError:
            print("Entrada inválida. Por favor, ingresa un número de índice válido.")

    def cambiar_acento_asistente(self):
        acentos_disponibles = {
            1: ('es', 'Español (España)'),
            2: ('es-us', 'Español (Estados Unidos)'),
            3: ('en', 'Inglés (Reino Unido)'),
            4: ('en-us', 'Inglés (Estados Unidos)'),

        }

        print("Acentos disponibles:")
        for key, value in acentos_disponibles.items():
            print(f"{key}. {value[1]}")

        try:
            eleccion = int(input("Selecciona el número del acento deseado: "))
            if eleccion in acentos_disponibles:
                self.acento_asistente = acentos_disponibles[eleccion][0]
                self.responder_con_audio("Acento del asistente cambiado correctamente.", idioma=self.acento_asistente)
                self.save_config()
            else:
                print("Selección no válida.")
                self.responder_con_audio("Selección no válida.", idioma=self.acento_asistente)
        except ValueError:
            print("Por favor, introduce un número válido.")
            self.responder_con_audio("Por favor, introduce un número válido.", idioma=self.acento_asistente)

    def reiniciar_configuracion(self):
        """
        Restablece la configuración del asistente a los valores predeterminados.
        """
        self.asistente_nombre = "Alkaris"
        self.acento_asistente = 'es'
        self.energy_threshold = 5000
        self.save_config()

        if self.label_nombre_asistente:
            self.label_nombre_asistente.config(text=f"Asistente: {self.asistente_nombre}")

        self.responder_con_audio("La configuración del asistente ha sido reiniciada a los valores predeterminados.")

    def verificar_conexion_internet(self):
        try:
            respuesta = requests.get("http://www.google.com", timeout=5)
            if respuesta.status_code == 200:
                self.is_internet_available = True
            else:
                self.is_internet_available = False
        except requests.ConnectionError:
            self.is_internet_available = False
        except requests.Timeout:
            self.is_internet_available = False

    def procesar_comando_buscar(self, consulta):
        try:
            if not consulta.strip():
                self.responder_con_audio("La consulta de búsqueda está vacía.")
                return
            self.spotify_controller.buscar_y_reproducir_cancion(consulta)
        except Exception as e:
            self.responder_con_audio("Ocurrió un error al procesar el comando de búsqueda.")
            print(f"Error al procesar el comando de búsqueda: {e}")

    def procesar_comando_control(self, comando):
        try:
            if comando == "detener":
                if self.spotify_controller.verificar_estado_reproduccion(playing=True):
                    self.spotify_controller.pause_playback()
                    self.responder_con_audio("Reproducción detenida.")
                else:
                    self.responder_con_audio("No se puede detener la reproducción porque ya está detenida.")
            elif comando == "siguiente":
                self.spotify_controller.next_track()
                self.responder_con_audio("Reproduciendo la siguiente canción.")
            elif comando == "anterior":
                self.spotify_controller.previous_track()
                self.responder_con_audio("Reproduciendo la canción anterior.")
            elif comando == "reproducir":
                if not self.spotify_controller.verificar_estado_reproduccion(playing=True):
                    dispositivos = self.spotify_controller.obtener_dispositivos()
                    if len(dispositivos['devices']) == 1:
                        device_id = dispositivos['devices'][0]['id']
                        self.spotify_controller.start_playback(device_id=device_id)
                        self.responder_con_audio("Reproducción iniciada.")
                    elif len(dispositivos['devices']) > 1:
                        self.responder_con_audio("Tienes más de un dispositivo disponible. Por favor, elige uno.")
                        self.elegir_y_forzar_dispositivo()
                    else:
                        self.responder_con_audio("No se encontraron dispositivos disponibles para reproducir.")
                else:
                    self.responder_con_audio("No se puede reproducir la canción porque ya hay una canción reproduciéndose.")
        except Exception as e:
            self.responder_con_audio("Ocurrió un error al ejecutar el comando.")
            print(f"Error al ejecutar el comando {comando}: {e}")


    def obtener_device_id_activo(self):
        return self.spotify_controller.obtener_device_id_activo()

    def elegir_dispositivo(self):
        self.spotify_controller.elegir_dispositivo(self.responder_con_audio)

    def elegir_y_forzar_dispositivo(self):
        self.spotify_controller.elegir_y_forzar_dispositivo(self.responder_con_audio)

    def buscar_y_reproducir_cancion(self, cancion):
        self.spotify_controller.buscar_y_reproducir_cancion(cancion, self.responder_con_audio)

    def mostrar_dispositivos_disponibles(self):
        self.spotify_controller.mostrar_dispositivos_disponibles()

    # Modified responder_con_audio to use Gemini's voice
    def responder_con_audio(self, respuesta, idioma=None):
       # """Responde con audio utilizando la voz de Gemini Live API."""
       ## asyncio.run(self._responder_con_audio_gemini_async(respuesta, idioma))
        print("Falling back to pyttsx3 text-to-speech...")
        self.audio_manager.responder_con_audio(respuesta, idioma) 

    async def _responder_con_audio_gemini_async(self, respuesta, idioma=None):
        """Asynchronous function to respond with audio using Gemini Live API."""
        temp_filename = None
        try:
            # **IMPORTANT:** Double-check the model name in the Gemini API documentation.
            # "gemini-2.0-flash-exp" might be outdated or incorrect.
            # Refer to: https://ai.google.dev/api/python/google/generativeai/client#google.generativeai.client.LiveClient.connect
            model_name = "gemini-2.0-flash" # Keep this for now, but VERIFY in docs!

            # Configure Gemini Live API for audio response
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore") # You can change voice_name, e.g., "Aoede"
                    )
                )
            )

            print(f"Attempting to connect to Gemini Live API with model: {model_name}") # Debug print

            async with self.client.aio.live.connect(model=model_name, config=config) as session: # Use the model_name variable
                print("Successfully connected to Gemini Live API session.") # Debug print
                await session.send(input=respuesta, end_of_turn=True)

                temp_filename = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
                wf = wave.open(temp_filename, "wb")
                wf.setnchannels(1)
                wf.setsampwidth(2) # 16-bit audio
                wf.setframerate(24000) # Gemini Live API audio output is 24kHz

                async for response in session.receive():
                    if response.data:
                        wf.writeframes(response.data)

                wf.close()

                if os.path.exists(temp_filename):
                    pygame.mixer.music.load(temp_filename)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10) # Keep main thread alive while playing

        except Exception as e:
            print(f"Error using Gemini Text-to-Speech: {e}")
            print(f"Error Type: {type(e)}") # Print the specific error type
            print(f"Error Arguments: {e.args}") # Print error arguments, might contain more details

            if isinstance(e, requests.exceptions.HTTPError): # Check for HTTPError specifically
                http_error = e
                print(f"HTTP Error Details:")
                print(f"  Status Code: {http_error.response.status_code}") # Print status code if available
                print(f"  Response Text: {http_error.response.text}")     # Print response text if available
                print(f"  Response Headers: {http_error.response.headers}") # Print headers if available


            # Fallback to pyttsx3 if Gemini voice fails (optional)
            print("Falling back to pyttsx3 text-to-speech...")
            self.audio_manager.responder_con_audio(respuesta, idioma) # Use fallback if Gemini voice fails
        finally:
            if temp_filename and os.path.exists(temp_filename):
                os.remove(temp_filename) # Clean up temporary audio file


    def detener_reproduccion_audio(self):
        pygame.mixer.music.stop() # Stop pygame music directly, should stop Gemini voice immediately # Keep detener_reproduccion_audio, might be needed for fallback or other audio

    def esperar_por_asistente(self):
        while True:
            try:
                reconocido, comando = self.reconocimiento_de_voz()

                if reconocido and self.asistente_nombre.lower() in comando.lower():
                    return comando
            except Exception as e:
                print(f"Error al esperar por el comando '{self.asistente_nombre}': {e}")
                self.verificar_conexion_internet()
                time.sleep(5)


    def listar_comandos_disponibles(self):
        self.ajustar_volumen_para_escuchar()
        comandos = """
        Aquí están los comandos de voz disponibles que puedes usar:
        - 'Reproduce [nombre de la canción o artista]': Busca y reproduce la canción o artista especificado.
        - 'Detener': Detiene la reproducción actual en Spotify.
        - 'Siguiente': Salta a la siguiente canción en la lista de reproducción.
        - 'Anterior': Regresa a la canción anterior en la lista de reproducción.
        - 'Reproducir': Reanuda la reproducción si está pausada.
        - 'Elegir dispositivo': Permite seleccionar un dispositivo específico para la reproducción.
        - 'Validar cuenta': Reautentica tu cuenta de Spotify para verificar el acceso.
        - 'Cambia el nombre del asistente': Permite cambiar el nombre por el cual se activa el asistente.
        - 'Cambia el acento del asistente': Cambia el acento de voz del asistente.
        - 'Cambia la voz del asistente': Permite seleccionar una nueva voz para el asistente.
        - 'Cuéntame un chiste': El asistente narrará un chiste aleatorio.
        - 'Busca en YouTube [consulta]': Busca un video en YouTube y lo reproduce.
        - '¿Cómo se llama esta canción?': Identifica la canción que se está reproduciendo actualmente.
        - 'Agrega a favoritos': Añade la canción actual a tu lista de canciones guardadas en Spotify.
        - 'Reproducir favoritos': Reproduce las canciones que has marcado como favoritas en Spotify.
        - 'Muestra mis playlists': Lista tus playlists actuales y permite seleccionar una para reproducir.
        - 'Sube/Baja el volumen': Ajusta el volumen de reproducción en Spotify.
        - 'Reiniciar configuración': Restablece la configuración del asistente a los valores predeterminados.
        - 'Salir': Cierra la aplicación.
        - 'Activar gestos': Activa el control por gestos.
        - 'Desactivar gestos': Desactiva el control por gestos.
        - '¿Qué ves en mi pantalla?': Describe lo que ve en la pantalla.
        - 'Escucha audio': Analiza el audio capturado del micrófono.
        - 'Escucha audio y dime qué canción es': Identifica la canción del audio capturado.
        """
        self.responder_con_audio(comandos)
        self.restaurar_volumen_original()

    def reautenticar_spotify(self):
        self.spotify_controller.reautenticar_spotify(self.verificar_cuenta_premium, self.responder_con_audio)

    def encontrar_comando_similar(self, comando_pronunciado):
        comandos_conocidos = {
            "reproduce": ["reproduce", "pon", "tocar", "play", "iniciar"],
            "detener": ["detener", "stop", "pausar", "pause", "parar"],
            "siguiente": ["siguiente", "avanza", "next", "próxima", "adelante"],
            "anterior": ["anterior", "previo", "before", "atrás", "regresar"],
            "reproducir": ["reproducir", "continuar", "resume", "reanudar"],
            "elegir dispositivo": ["elegir dispositivo", "seleccionar dispositivo", "choose device", "cambiar dispositivo"],
            "validar cuenta": ["validar cuenta", "verificar cuenta", "validate account", "confirmar cuenta"],
            "mostrar mis playlist": ["mostrar playlist", "ver playlist", "show playlist", "listar playlist"],
            "salir": ["salir", "exit", "cerrar", "terminar"],
            "cambiar acento del asistente": ["cambiar acento", "change accent", "modificar acento"],
            "cambiar voz del asistente": ["cambiar voz", "change voice", "ajustar voz"],
            "cambiar nombre del asistente": ["cambiar nombre", "change name", "nuevo nombre"],
            "cuéntame un chiste": ["chiste", "un chiste", "cuéntame un chiste", "dime un chiste"],
            "busca en youtube": ["busca en youtube", "search on youtube", "buscar video"],
            # Comandos de video
            "pausa video": ["pausa video", "pausar video", "pause video", "detener video"],
            "play video": ["play video", "reproducir video", "iniciar video", "continuar video"],
            "establece volumen": ["establece volumen", "volumen video", "cambiar volumen video"],
            "segundo": ["segundo", "adelantar", "retroceder", "navegar video"],
            "cómo se llama esta canción": ["qué canción es", "nombre de la canción", "what song is this", "identificar canción"],
            "eliminar de favoritos": ["eliminar de favoritos", "quitar de favoritos", "remove favorite", "no me gusta"],
            "agregar a favoritos": ["agregar a favoritos", "favorito", "like", "añadir a favoritos"],
            "vlc": ["vlc música", "con vlc", "reproduce con vlc", "pon en vlc"],
            "reiniciar configuración": ["reiniciar configuración", "restablecer configuración", "reset configuration", "reinicia configuración"],
            "reproducir favoritos": ["reproducir favoritos", "play favorites", "canciones favoritas","mis canciones favoritas"],
            "activar gestos": ["activar gestos", "iniciar control gestual","activa control gestual", "comenzar gestos"],
            "desactivar gestos": ["desactiva control gestual", "detener control gestual", "parar gestos"],
            "qué ves en mi pantalla": ["qué ves en mi pantalla", "describe mi pantalla", "ver pantalla", "pantalla"], # New command
            "escucha audio": ["escucha audio", "analiza audio", "oir audio", "audio"], # New command
            "escucha audio y dime qué canción es": ["escucha audio y dime qué canción es", "identifica canción audio", "canción audio"], # New command

            # Modos de reproducción
            "activar aleatorio": ["activar aleatorio", "modo aleatorio", "shuffle on", "activa shuffle"],
            "desactivar aleatorio": ["desactivar aleatorio", "quitar aleatorio", "shuffle off", "desactiva shuffle"],
            "cambiar aleatorio": ["cambiar aleatorio", "alternar aleatorio", "toggle shuffle", "invertir aleatorio"],
            "repetir canción": ["repetir canción", "repetir track", "repeat song", "loop song"],
            "repetir álbum": ["repetir álbum", "repetir lista", "repeat context", "loop album"],
            "desactivar repetición": ["desactivar repetición", "sin repetición", "repeat off", "quitar repetición"],
            "cambiar repetición": ["cambiar repetición", "alternar repetición", "toggle repeat", "ciclar repetición"],

            # Reproducción de álbumes
            "reproducir album": ["reproducir album", "pon album", "play album", "escuchar álbum"],

            # Recomendaciones
            "recomienda canciones": ["recomienda canciones", "sugerir canciones", "recommend tracks", "descubrir música"],
            "recomienda artistas": ["recomienda artistas", "sugerir artistas", "recommend artists", "descubrir artistas"]
        }

        comando_pronunciado = re.sub(r'\W+', '', comando_pronunciado.lower().strip())
        mejor_coincidencia = None
        mejor_puntuacion = 0

        for comando, sinonimos in comandos_conocidos.items():
            for sinonimo in sinonimos:
                sinonimo = re.sub(r'\W+', '', sinonimo.lower().strip())
                puntuacion = lv.ratio(comando_pronunciado, sinonimo)
                if puntuacion > mejor_puntuacion:
                    mejor_puntuacion = puntuacion
                    mejor_coincidencia = comando

        return mejor_coincidencia if mejor_puntuacion > 0.8 else None

    def contar_chiste(self):
        chiste_text = self.joke_generator.get_joke()
        self.responder_con_audio(chiste_text)

    def pausar_spotify_si_es_necesario(self):
        return self.spotify_controller.pausar_spotify_si_es_necesario(self.responder_con_audio)

    def buscar_youtube_y_reproducir(self, query):
        self.youtube_controller.buscar_youtube_y_reproducir(query, self.pausar_spotify_si_es_necesario, self.responder_con_audio)

    def play_video(self):
        self.youtube_controller.resume_video()

    def pause_video(self):
        self.youtube_controller.pause_video()

    def set_video_volume(self, volume):
        self.youtube_controller.set_video_volume(volume)

    def seek_video(self, seconds):
        self.youtube_controller.seek_video(seconds)

    def buscar_youtube_y_reproducir_con_vlc(self, query):
        self.youtube_controller.buscar_youtube_y_reproducir_con_vlc(query, self.pausar_spotify_si_es_necesario, self.responder_con_audio)

    def buscar_youtube_y_reproducir_desde_ui(self):
        """Función para buscar y reproducir una canción en YouTube usando VLC basada en la entrada del usuario."""
        cancion = self.entry_cancion.get()
        if cancion.strip():
            self.buscar_youtube_y_reproducir_con_vlc(cancion)
            self.entry_cancion.delete(0, tk.END)
        else:
            self.responder_con_audio("Por favor, introduce el nombre de una canción para buscar.")
            self.entry_cancion.delete(0, tk.END)

    def vlc_play_pause(self):
        self.youtube_controller.vlc_play_pause()

    def vlc_set_volume(self, volume):
        self.youtube_controller.vlc_set_volume(volume)

    def guardar_comando(self, comando):
        with open("comandos.txt", "a") as file:
            file.write(comando + "\n")

    def ejecutar(self):
        try:
            self.autenticar_spotify()
            while True:

                comando_reconocido, comando_pronunciado = self.reconocimiento_de_voz()
                if comando_reconocido:

                    comando_normalizado = unidecode.unidecode(comando_pronunciado.lower()).strip()
                    print(f"Comando normalizado: '{comando_normalizado}'")

                    comando_similar = self.encontrar_comando_similar(comando_normalizado)
                    print(f"Comando similar encontrado: '{comando_similar}'")

                    if comando_similar:
                        comando = comando_similar
                    else:
                        comando = comando_normalizado
                        self.guardar_comando(comando_normalizado)
                    if comando.startswith("reproduce"):
                        consulta = comando_pronunciado.replace("reproduce", "", 1).strip() if comando_similar else " ".join(comando_pronunciado.split()[1:])
                        if consulta:
                            self.procesar_comando_buscar(consulta)

                    elif "cuéntame un chiste" in comando:
                        self.ajustar_volumen_para_escuchar()
                        self.contar_chiste()
                        self.restaurar_volumen_original()
                    elif "play video" in comando :
                        self.play_video()
                    elif "reiniciar configuración"in comando:
                        self.reiniciar_configuracion()
                    elif "pausa video" in comando:
                        self.pause_video()
                    elif comando.startswith("establece volume"):
                        volume = self.extraer_numero(comando)
                        if volume is not None:
                            self.set_video_volume(volume)
                        else:
                            print("No se especificó un volumen válido.")
                    elif comando.startswith("segundo"):
                        seconds = self.extraer_numero(comando)
                        if seconds is not None:
                            self.seek_video(seconds)
                        else:
                            print("No se especificaron segundos válidos para buscar.")
                    elif comando.startswith("busca en youtube"):
                        busqueda = comando_pronunciado.replace("busca en youtube", "", 1).strip() if comando_similar else " ".join(comando_pronunciado.split()[1:])
                        if busqueda:
                         self.buscar_youtube_y_reproducir(busqueda)
                    elif comando.startswith("vlc"):
                        video = comando_pronunciado.replace("vlc", "", 1).strip() if comando_similar else " ".join(comando_pronunciado.split()[1:])
                        if video:
                            self.buscar_youtube_y_reproducir_con_vlc(video)

                    elif comando in ["pausa vlc", "continuar vlc", "vlc pausa", "vlc continuar"]:
                        self.vlc_play_pause()
                    elif comando.startswith("vlc volumen") or comando.startswith("volumen vlc"):
                        palabras = comando.split()
                        numero = None
                        for palabra in palabras:
                            if palabra.isdigit():
                                numero = int(palabra)
                                break
                        if numero is not None:
                            self.vlc_set_volume(numero)
                        else:
                            self.responder_con_audio("Por favor, indica un número después de 'volumen' para establecer el volumen.")

                    elif "reproducir favoritos" in comando:
                            self.ajustar_volumen_para_escuchar()
                            self.reproducir_canciones_favoritas()
                            self.restaurar_volumen_original()

                    elif comando in ["cállate", "callate", "silencio", "detente"]:
                        self.detener_reproduccion_audio()
                        print("Reproducción de audio detenida.")
                        continue


                    elif comando == "activar gestos":
                        self.activar_control_gestual()
                    elif comando == "desactivar gestos":
                        self.desactivar_control_gestual()
                    elif comando in ["detener", "siguiente", "anterior", "reproducir"]:
                        self.ajustar_volumen_para_escuchar()
                        self.procesar_comando_control(comando)
                        self.restaurar_volumen_original()
                    elif "agregar a favoritos" in comando:
                        self.agregar_cancion_a_favoritos()
                    elif "eliminar de favoritos" in comando:
                        self.spotify_controller.eliminar_de_favoritos()

                    # Comandos de modos de reproducción
                    elif comando == "activar aleatorio":
                        self.spotify_controller.activar_desactivar_aleatorio(True)
                    elif comando == "desactivar aleatorio":
                        self.spotify_controller.activar_desactivar_aleatorio(False)
                    elif comando == "cambiar aleatorio":
                        self.spotify_controller.cambiar_aleatorio()
                    elif comando == "repetir canción":
                        self.spotify_controller.modo_repeticion('track')
                    elif comando == "repetir álbum":
                        self.spotify_controller.modo_repeticion('context')
                    elif comando == "desactivar repetición":
                        self.spotify_controller.modo_repeticion('off')
                    elif comando == "cambiar repetición":
                        self.spotify_controller.cambiar_repeticion()
                    elif comando.startswith("reproducir album"):
                        album_nombre = comando_pronunciado.replace("reproducir album", "", 1).replace("reproducir álbum", "", 1).strip()
                        self.spotify_controller.reproducir_album(album_nombre)
                     # Comandos de recomendaciones
                    elif comando == "recomienda canciones":
                        self.spotify_controller.obtener_recomendaciones('track')
                    elif comando == "recomienda artistas":
                        self.spotify_controller.obtener_recomendaciones('artist')
                    elif "elegir dispositivo" in comando:
                        self.elegir_y_forzar_dispositivo()
                    elif "validar cuenta" in comando:
                        self.reautenticar_spotify()
                    elif "mostrar mis playlist" in comando:
                        self.procesar_comando_mostrar_playlists()

                    elif "cómo se llama esta canción" in comando:
                        self.ajustar_volumen_para_escuchar()
                        self.obtener_nombre_cancion_actual()
                        self.restaurar_volumen_original()

                    elif comando == "cambiar acento del asistente":
                         self.cambiar_acento_asistente()
                    elif comando == "cambiar voz del asistente":
                         self.cambiar_voz_asistente()
                    elif "clima" in comando_pronunciado:
                        self.ajustar_volumen_para_escuchar()
                        self.procesar_comando_clima(comando_pronunciado)
                        self.restaurar_volumen_original()
                    elif comando.startswith("dime"):
                        partes_comando = comando.split()
                        if "en" in partes_comando:
                            aspecto = " ".join(partes_comando[1:partes_comando.index("en")])
                            ciudad = " ".join(partes_comando[partes_comando.index("en") + 1:])
                            mensaje_clima = self.obtener_clima_de(ciudad, aspecto.strip())
                            self.responder_con_audio(mensaje_clima) # Now using Gemini voice
                    elif "subir volumen" in comando or "bajar volumen" in comando:
                        self.procesar_comando_volumen(comando)
                    elif "volumen" in comando:

                        comando_limpio = re.sub(r'[^0-9\s]','',comando)

                        palabras = comando_limpio.split()
                        numero = None
                        for i, palabra in enumerate(palabras):
                            if palabra.isdigit():
                                numero = int(palabra)
                                break
                        if numero is not None:
                            self.ajustar_volumen(numero)
                        else:
                            self.responder_con_audio("Por favor, indica un número después de 'volumen' para establecer el volumen.") # Now using Gemini voice
                    elif "salir" in comando:
                        self.responder_con_audio("Saliendo de la aplicación") # Now using Gemini voice
                        self.root.destroy()
                        break

                    elif comando == "cambiar nombre del asistente":
                        self.cambiar_nombre_asistente()

                    elif comando == "qué ves en mi pantalla": # New command handling
                        screen_file = self.capture_screen()
                        if screen_file:
                            # Execute Gemini processing in a separate thread
                            thread = threading.Thread(target=self._procesar_comando_no_reconocido_thread, args=("Describe lo que ves en esta imagen", screen_file, None, False))
                            thread.daemon = True
                            thread.start()
                        else:
                            self.responder_con_audio("No pude capturar la pantalla.") # Now using Gemini voice

                    elif comando == "escucha audio": # New command handling
                        audio_file = self.capture_audio()
                        if audio_file:
                            # Execute Gemini processing in a separate thread
                            thread = threading.Thread(target=self._procesar_comando_no_reconocido_thread, args=("Analiza este audio", None, audio_file, False))
                            thread.daemon = True
                            thread.start()
                        else:
                            self.responder_con_audio("No pude capturar el audio.") # Now using Gemini voice

                    elif comando == "escucha audio y dime qué canción es": # New command handling
                        audio_file = self.capture_audio()
                        if audio_file:
                            # Execute Gemini processing in a separate thread
                            thread = threading.Thread(target=self._procesar_comando_no_reconocido_thread, args=("¿Qué canción es esta?", None, audio_file, True))
                            thread.daemon = True
                            thread.start()
                        else:
                            self.responder_con_audio("No pude capturar el audio.") # Now using Gemini voice


                    else:
                        if self.es_consulta_valida(comando):
                            # Execute Gemini processing in a separate thread
                            thread = threading.Thread(target=self._procesar_comando_no_reconocido_thread, args=(comando_pronunciado, None, None, False))
                            thread.daemon = True
                            thread.start()
                        else:
                            print("Comando no reconocido y no es una consulta válida.")

                else:
                 print("Comando no reconocido o no destinado al asistente.")
        except Exception as e:
            print(f"Error inesperado: {e}")
            self.responder_con_audio("Ocurrió un error inesperado. Por favor, intenta nuevamente más tarde.") # Now using Gemini voice

    def _procesar_comando_no_reconocido_thread(self, texto, video_file=None, audio_file=None, is_music_query=False):
        """
        Función para ejecutar procesar_comando_no_reconocido en un hilo separado.
        """
        self.procesar_comando_no_reconocido(texto, audio_file, video_file, is_music_query)


    def procesar_comando_no_reconocido(self, texto, audio_file=None, video_file=None, is_music_query=False):
        """Procesa un comando no reconocido utilizando Gemini API, ahora con manejo de archivos."""
        contents = [] # Initialize contents as empty list

        if video_file:
            # Prompt específico para describir la pantalla de manera más natural en español
            prompt_descripcion_pantalla = """
            Describe la imagen de la pantalla que te envío en español. Intenta ser natural y conversacional, como si le estuvieras explicando a una persona qué hay en la pantalla.
            Describe los elementos principales, su función o propósito, y el diseño general.
            Evita ser demasiado técnico o literal en la descripción. Enfócate en lo que sería útil para una persona entender al ver esta pantalla.
            Responde en español.
            """
            contents.append(prompt_descripcion_pantalla) # Use the detailed prompt for screen description
            try:
                uploaded_file = self.client.files.upload(file=video_file) # Upload image/video file # Changed to client.files.upload and file=
                contents.append(uploaded_file) # Add file reference to contents
            except Exception as e:
                print(f"Error uploading or processing image file: {e}")
                self.responder_con_audio("No pude procesar la imagen.") # Now using Gemini voice
                return

        elif audio_file: # Keep the original logic for audio files
            contents.append(texto) # Add the original text prompt for audio analysis
            try:
                uploaded_file = self.client.files.upload(file=audio_file) # Upload audio file # Changed to client.files.upload and file=
                contents.append(uploaded_file) # Add file reference to contents
            except Exception as e:
                print(f"Error uploading or processing audio file: {e}")
                self.responder_con_audio("No pude procesar el audio.") # Now using Gemini voice
                return
        else:
            contents.append(texto) # If no file, just use the text prompt


        try:
            response = self.client.models.generate_content( # Changed to client.models.generate_content
                model='gemini-2.0-flash',
                contents=contents
            )

            respuesta = response.text # ACCESS response.text DIRECTLY
            respuesta_limpia = re.sub(r'[\*\_]', '', respuesta)
            if is_music_query: # Specific handling for music query
                if "is:" in respuesta_limpia.lower() and len(respuesta_limpia.split("is:")) > 1: # Basic check if the response identifies a song
                    song_title = respuesta_limpia.split("is:")[1].strip()
                    self.responder_con_audio(f"Según lo que escucho, la canción podría ser: {song_title}") # Now using Gemini voice
                else:
                    self.responder_con_audio(respuesta_limpia) # Now using Gemini voice
            else:
                self.responder_con_audio(respuesta_limpia) # Now using Gemini voice

        except Exception as e:
            print(f"Error al conectar con la API de Gemini o procesar respuesta: {e}")
            self.responder_con_audio("Hubo un error al procesar tu solicitud.") # Now using Gemini voice
        finally:
            if video_file and os.path.exists(video_file):
                os.remove(video_file) # Clean up temporary image file
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file) # Clean up temporary audio file


    def agregar_cancion_a_favoritos(self):
        self.spotify_controller.agregar_cancion_a_favoritos(self.responder_con_audio) # Now using Gemini voice

    def reproducir_canciones_favoritas(self):
        self.spotify_controller.reproducir_canciones_favoritas(self.responder_con_audio) # Now using Gemini voice

    def obtener_nombre_cancion_actual(self):
        self.spotify_controller.obtener_nombre_cancion_actual(self.responder_con_audio) # Now using Gemini voice

    def procesar_comando_clima(self, comando_pronunciado):
        ciudad, aspecto = self.weather_service.extraer_ciudad_aspecto(comando_pronunciado)
        if not ciudad:
            self.responder_con_audio("Por favor, especifica la ciudad para la que deseas conocer el clima.") # Now using Gemini voice
            return

        mensaje_clima = self.obtener_clima_de(ciudad, aspecto)
        self.responder_con_audio(mensaje_clima) # Now using Gemini voice

    def obtener_clima_de(self, ciudad, aspecto):
        return self.weather_service.obtener_clima_de(ciudad, aspecto, self.responder_con_audio) # Now using Gemini voice


    def mostrar_playlists_disponibles(self, limit=50, offset=0):
        self.spotify_controller.mostrar_playlists_disponibles(limit, offset, self.responder_con_audio) # Now using Gemini voice

    def reproducir_primera_cancion_playlist(self, playlist_uri):
        self.spotify_controller.reproducir_primera_cancion_playlist(playlist_uri, self.responder_con_audio) # Now using Gemini voice

    def reproducir_playlist_por_numero(self, numero_playlist):
        self.spotify_controller.reproducir_playlist_por_numero(numero_playlist, self.responder_con_audio) # Now using Gemini voice

    def procesar_comando_mostrar_playlists(self):
        self.mostrar_playlists_disponibles()
        try:
            numero_playlist = int(input("Ingresa el número correspondiente a la playlist: "))
            self.reproducir_playlist_por_numero(numero_playlist)
        except ValueError:
            print("Por favor, ingresa un número válido.")
            self.responder_con_audio("Por favor, ingresa un número válido para elegir la playlist.") # Now using Gemini voice


    def guardar_error(self, error_msg):
        try:
            with open(self.error_log_file, "a") as f:
                f.write(error_msg + "\n")
                traceback.print_exc(file=f)
                f.write("\n")
            print("Error guardado en el archivo de registro.")
        except Exception as e:
            print(f"No se pudo guardar el error en el archivo: {e}")

    def procesar_comando_volumen(self, comando):
        try:
            if "subir volumen" in comando:
                self.subir_volumen()
            elif "bajar volumen" in comando:
                self.bajar_volumen()
            else:
                numero = self.extraer_numero(comando)
                if numero is not None:
                    self.ajustar_volumen(numero)
                else:
                    self.responder_con_audio("Comando de volumen no reconocido.") # Now using Gemini voice
        except Exception as e:
            print(f"Error al procesar comando de volumen: {e}")
            self.responder_con_audio("Ocurrió un error al procesar el comando de volumen.") # Now using Gemini voice

    def subir_volumen(self):
        self.spotify_controller.subir_volumen(self.responder_con_audio) # Now using Gemini voice

    def bajar_volumen(self):
        self.spotify_controller.bajar_volumen(self.responder_con_audio) # Now using Gemini voice

    def ajustar_volumen(self, volumen):
        self.spotify_controller.ajustar_volumen(volumen, self.responder_con_audio) # Now using Gemini voice

    def extraer_numero(self, texto):
        try:
            numero = None
            palabras = texto.split()
            for palabra in palabras:
                if palabra.isdigit():
                    numero = int(palabra)
                    break
            return numero
        except Exception as e:
            print(f"Error al extraer número del texto: {e}")
            return None

    def on_threshold_change(self, event):
        """Guarda la configuración cuando el valor del energy_threshold cambia."""
        self.save_config()
        print(f"Nuevo umbral de energía guardado: {self.energy_threshold_slider.get()}")

    def cambiar_nombre_asistente(self):
        nuevo_nombre = input("Ingresa el nuevo nombre para el asistente: ").strip()
        if nuevo_nombre:
            self.asistente_nombre = nuevo_nombre
            self.label_nombre_asistente.config(text=f"Asistente: {nuevo_nombre}")
            self.responder_con_audio(f"Nombre del asistente cambiado a {nuevo_nombre}.") # Now using Gemini voice
            self.save_config()
        else:
            self.responder_con_audio("El nombre del asistente no se ha cambiado porque la entrada estaba vacía.") # Now using Gemini voice

    def iniciar_control_gestual(self):
        """Inicia el hilo de control gestual si no está corriendo."""
        if not hasattr(self, 'thread_gestual') or not self.thread_gestual.is_alive():
            self.thread_gestual = threading.Thread(target=self.control_gestual.iniciar_control)
            self.thread_gestual.daemon = True
            self.thread_gestual.start()

    def activar_control_gestual(self):
        """Activa el control gestual y comienza la captura de video."""
        self.control_gestual.activar()
        self.responder_con_audio("Control gestual activado.") # Now using Gemini voice
        self.iniciar_control_gestual()

    def desactivar_control_gestual(self):
        """Desactiva el control gestual y detiene la captura de video."""
        self.control_gestual.desactivar()
        self.responder_con_audio("Control gestual desactivado.") # Now using Gemini voice
        if hasattr(self, 'thread_gestual') and self.thread_gestual.is_alive():
            self.thread_gestual.join()

    def es_consulta_valida(self, comando):
        """
        Determina si el comando es una consulta válida que debe enviarse a Gemini.
        Utiliza patrones para identificar preguntas o solicitudes comunes.
        """
        patrones = [
            r'^dime\b',
            r'^cuentame\b',
             r'^sabes\b',
            r'^busca\b',
            r'^que es\b',
            r'^como\b',
            r'^quién\b',
            r'^qué\b',
            r'^por favor\b',
            r'^ayuda\b',
            r'^explica\b',
            r'^informame\b',

        ]
        for patron in patrones:
            if re.match(patron, comando):
                return True
        return False


    def siguiente_cancion(self):
        self.spotify_controller.siguiente_cancion(self.responder_con_audio) # Now using Gemini voice

    def anterior_cancion(self):
        self.spotify_controller.anterior_cancion(self.responder_con_audio) # Now using Gemini voice

    def pausar_reproduccion(self):
        self.spotify_controller.pausar_reproduccion(self.responder_con_audio) # Now using Gemini voice

    def reanudar_reproduccion(self):
        self.spotify_controller.reanudar_reproduccion(self.responder_con_audio) # Now using Gemini voice


if __name__ == "__main__":
    app = SpotifyVoiceControl()
    app.root.mainloop()