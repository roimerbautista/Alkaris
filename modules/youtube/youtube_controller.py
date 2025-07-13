#sTART OF FILE youtube_controller.py ---
from googleapiclient.discovery import build
import subprocess
import logging
import time
from threading import Thread
from modules.media_players.mpv_player import MPVPlayer
from modules.media_players.vlc_player import VLCPlayer

class YoutubeController:
    def __init__(self, youtube_api_key, mpv_player=None, vlc_player=None, audio_manager=None):
        self.youtube_api_key = youtube_api_key

        # Inicializar los reproductores si no se pasan como parámetros
        self.mpv_player = mpv_player if mpv_player else MPVPlayer()
        self.vlc_player = vlc_player if vlc_player else VLCPlayer()
        self.audio_manager = audio_manager
        self.logger = self._setup_logger()

        try:
            self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            self.logger.info("YouTube API client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize YouTube API client: {e}")
            raise
    def pause_video(self):
        """Pausa la reproducción en MPV."""
        if not self.mpv_player:
            self.logger.warning("El reproductor MPV no está inicializado.")
            return

        try:
            self.mpv_player.pause()
            self.logger.info("Comando ejecutado: Pausar MPV.")
        except Exception as e:
            self.logger.error(f"Error al pausar MPV: {e}")

    def resume_video(self):
        """Reanuda la reproducción en MPV."""
        if not self.mpv_player:
            self.logger.warning("El reproductor MPV no está inicializado.")
            return

        try:
            self.mpv_player.resume()
            self.logger.info("Comando ejecutado: Reanudar MPV.")
        except Exception as e:
            self.logger.error(f"Error al reanudar MPV: {e}")

    def stop_video(self):
        """Detiene completamente la reproducción en MPV."""
        if not self.mpv_player:
            self.logger.warning("El reproductor MPV no está inicializado.")
            return

        try:
            self.mpv_player.stop()
            self.logger.info("Comando ejecutado: Detener MPV.")
        except Exception as e:
            self.logger.error(f"Error al detener MPV: {e}")


    def _setup_logger(self):
        logger = logging.getLogger('youtube_controller')
        logger.setLevel(logging.DEBUG) # Changed to DEBUG for more info
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def buscar_youtube_y_reproducir(self, query, pausar_spotify_callback, responder_con_audio_callback):
        try:
            pausado = pausar_spotify_callback()
            self.logger.info(f"Buscando en YouTube: {query}")

            request = self.youtube.search().list(q=query, part='snippet', type='video', maxResults=1)
            response = request.execute()

            if response['items']:
                video_id = response['items'][0]['id']['videoId']
                video_title = response['items'][0]['snippet']['title']
                video_url = f'https://www.youtube.com/watch?v={video_id}'
                self.logger.info(f"Reproduciendo {video_title} ({video_url}) en MPV")

                responder_con_audio_callback(f"Reproduciendo {video_title}")
                self.mpv_player.play_video(video_url)  # Llamada al método actualizado
            else:
                self.logger.warning(f"No se encontraron resultados para: {query}")
                responder_con_audio_callback("No se encontraron resultados.")
        except Exception as e:
            self.logger.error(f"Error al buscar en YouTube y reproducir: {e}")
            responder_con_audio_callback("Ocurrió un error al buscar el video.")


    def _reproducir_video_en_thread(self, video_url):
        try:
            self.logger.info(f"Iniciando proceso MPV para {video_url}")
            self.mpv_player.play_video(video_url) # Use play_video method in MPVPlayer
        except Exception as e:
            self.logger.error(f"Error al reproducir el video con MPV: {e}")



    def buscar_youtube_y_reproducir_con_vlc(self, query, pausar_spotify_callback, responder_con_audio_callback):
        """
        Busca en YouTube y reproduce el primer resultado con VLC reutilizando la misma instancia,
        usando yt-dlp para streamear el audio directamente a VLC.
        """
        try:
            pausado = pausar_spotify_callback()
            self.logger.info(f"Buscando en YouTube para VLC: {query}")

            request = self.youtube.search().list(q=query, part='snippet', type='video', maxResults=1)
            response = request.execute()

            if response['items']:
                video_id = response['items'][0]['id']['videoId']
                video_title = response['items'][0]['snippet']['title']
                video_url = f'https://www.youtube.com/watch?v={video_id}'
                self.logger.info(f"Reproduciendo solo audio de {video_title} ({video_url}) en VLC usando yt-dlp stream")
                responder_con_audio_callback(f"Reproduciendo {video_title} en VLC")

                success = self.vlc_player.play_youtube_audio(video_url)  # Llamada actualizada

                if not success:
                    self.logger.error("Error al reproducir audio de YouTube con VLC.")
                    responder_con_audio_callback("Error al reproducir audio.")

            else:
                self.logger.warning(f"No se encontraron resultados para: {query}")
                responder_con_audio_callback("No se encontraron resultados.")
        except Exception as e:
            self.logger.error(f"Error al buscar en YouTube y reproducir con VLC: {e}")
            responder_con_audio_callback("Ocurrió un error al buscar o reproducir el audio.")


    def manejar_cierre_manual_vlc(self, responder_con_audio_callback=None):
        """
        Detecta si VLC se cerró manualmente y lo maneja apropiadamente.
        """
        try:
            status = self.vlc_player.get_state() # Use get_state() not get_status()
            if status is None or status in ['Stopped', 'Ended', 'Error']: # Verificar estados que sugieren reinicio o cierre
                self.logger.info("VLC parece haberse cerrado manualmente o está en un estado final. Reinicializando...")
                self.vlc_player = VLCPlayer()  # Re-inicializar usando el módulo importado
                if responder_con_audio_callback:
                    responder_con_audio_callback("Ventana de VLC cerrada o finalizada. Reinicializado.")
                return True
            return False
        except Exception as e:
            self.logger.info(f"Error al verificar estado de VLC. Asumiendo cierre manual: {e}")
            self.vlc_player = VLCPlayer()  # Re-inicializar usando el módulo importado
            if responder_con_audio_callback:
                responder_con_audio_callback("Ventana de VLC cerrada. Reinicializado.")
            return True

    def vlc_play_pause(self):
            """Pausa o reanuda la reproducción en VLC."""
            if not self.vlc_player:
                self.logger.warning("El reproductor VLC no está inicializado")
                return

            try:
                self.vlc_player.pause_or_resume() # Use pause_or_resume() not play_pause()
                self.logger.info("Comando ejecutado: Pausar/Reanudar VLC.")
            except AttributeError as e:
                self.logger.error(f"Error: el reproductor VLC no tiene el método pause_or_resume: {e}") # Ya no aplica, se usa el método pause_or_resume()
            except Exception as e:
                self.logger.error(f"Error al pausar/reanudar VLC: {e}")

    def vlc_set_volume(self, volume):
            """Ajusta el volumen del reproductor VLC."""
            if not self.vlc_player:
                self.logger.warning("El reproductor VLC no está inicializado")
                return

            try:
                if not isinstance(volume, (int, float)) or volume < 0 or volume > 100:
                    self.logger.warning(f"Volumen inválido: {volume}. Debe ser un número entre 0 y 100")
                    return

                self.vlc_player.set_volume(volume) # Use set_volume() not vlc_set_volume()
                self.logger.info(f"Volumen de VLC ajustado a {volume}%.")
            except AttributeError as e:
                self.logger.error(f"Error: el reproductor VLC no tiene el método set_volume: {e}") # Ya no aplica, se usa el método set_volume()
            except Exception as e:
                self.logger.error(f"Error al ajustar el volumen de VLC: {e}")