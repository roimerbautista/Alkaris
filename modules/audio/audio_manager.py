import tempfile
import os
import pygame
from gtts import gTTS
import noisereduce as nr
import numpy as np
import soundfile as sf
import librosa
from utils.audio_utils import normalizar_audio
import traceback

class AudioManager:
    def __init__(self, acento_asistente, audio_lock):
        self.acento_asistente = acento_asistente
        self.audio_lock = audio_lock
        pygame.mixer.init()
        self.reproduciendo_audio = False
        self.detener_audio = False
        self.audio_thread = None

    def responder_con_audio(self, respuesta, idioma=None):
        if not idioma:
            idioma = self.acento_asistente

        with self.audio_lock:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
                    archivo_audio = tmpfile.name
                
                tts = gTTS(text=respuesta, lang=idioma)
                tts.save(archivo_audio)
                print(f"Audio guardado en: {archivo_audio}")
                
                pygame.mixer.music.load(archivo_audio)
                pygame.mixer.music.play()
                print(f"Reproduciendo audio desde: {archivo_audio}")

                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                pygame.mixer.music.unload()
                os.remove(archivo_audio)
                print(f"Archivo temporal eliminado: {archivo_audio}")
            except Exception as e:
                print(f"Error al responder con audio: {e}")
                traceback.print_exc()

    def reducir_ruido(self, audio):
        try:
            audio_data = np.frombuffer(audio.get_wav_data(), dtype=np.int16)
            energia_señal_original = np.sum(audio_data ** 2)
            energia_ruido_original = 0.1 * energia_señal_original
            reduced_noise_audio = nr.reduce_noise(y=audio_data, sr=audio.sample_rate)
            energia_señal_procesada = np.sum(reduced_noise_audio ** 2)
            snr_antes = energia_señal_original / energia_ruido_original
            snr_despues = energia_señal_procesada / energia_ruido_original

            print(f"SNR antes de la reducción de ruido: {snr_antes}")
            print(f"SNR después de la reducción de ruido: {snr_despues}")

            return reduced_noise_audio, audio.sample_rate
        except Exception as e:
            print(f"Error al reducir el ruido: {e}")
            return None, None

    def detener_reproduccion_audio(self):
        """
        Detiene la reproducción del audio si está en curso.
        """
        if self.reproduciendo_audio:
            print("Deteniendo reproducción de audio...")
            self.detener_audio = True
            pygame.mixer.music.stop()
            if self.audio_thread and self.audio_thread.is_alive():
                self.audio_thread.join()
            self.reproduciendo_audio = False
        else:
            print("No hay audio reproduciéndose.")
