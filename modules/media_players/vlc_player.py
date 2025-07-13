# START OF FILE vlc_player.py ---
# Description: Controlador mejorado para el reproductor VLC utilizando la biblioteca python-vlc.
import platform
import os
import sys
import vlc
import logging
import psutil
import subprocess
import time

class VLCPlayer:
    """
    Controlador mejorado para el reproductor VLC utilizando la biblioteca python-vlc.
    Maneja el inicio y cierre del proceso VLC y logging.
    """
    def __init__(self):
        self._setup_vlc_path()
        self.instance = vlc.Instance('--no-video')  # Configurar VLC para no mostrar video inicialmente
        self.player = self.instance.media_player_new()
        self.is_playing = False
        self.logger = self._setup_logger()
        self.vlc_process = None # To track the VLC process, if we start it
        self.current_url = None
        

    def _setup_logger(self):
        logger = logging.getLogger('vlc_player')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _setup_vlc_path(self):
        """Configura la ruta para VLC si es necesario (especialmente en Windows)."""
        if platform.system() == "Windows":
            user_profile_path = os.environ.get('USERPROFILE', '')
            vlc_lib_path = os.path.join(user_profile_path, 'scoop', 'apps', 'vlc', 'current')

            if os.path.exists(vlc_lib_path):
                if vlc_lib_path not in os.environ['PATH']:
                    os.environ['PATH'] += ';' + vlc_lib_path

                if sys.version_info >= (3, 8):
                    try:
                        os.add_dll_directory(vlc_lib_path)
                    except Exception as e:
                        self.logger.warning(f"Error al agregar DLL directory para VLC: {e}")


    def _ensure_vlc_running(self):
        """Verifica si VLC está en ejecución, si no, intenta iniciarlo."""
        if not self.is_vlc_process_running():
            self._start_vlc_process()
        return self.is_vlc_process_running()


    def is_vlc_process_running(self):
        """Verifica si algún proceso vlc está en ejecución."""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'vlc' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def _start_vlc_process(self):
        """Inicia el proceso VLC (basic start, might need more sophisticated approach)."""
        vlc_path = self._find_vlc_path()
        if vlc_path:
            cmd = [vlc_path, "--intf", "dummy"] # Start with dummy interface, no GUI
            try:
                self.logger.info(f"Iniciando VLC process: {' '.join(cmd)}")
                self.vlc_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                time.sleep(1) # Give it a moment to start
            except Exception as e:
                self.logger.error(f"Error starting VLC process: {e}")
                self.vlc_process = None
        else:
            self.logger.error("No se pudo encontrar la ruta de VLC para iniciar el proceso.")


    def _find_vlc_path(self):
        """Encuentra la ruta del ejecutable VLC según el sistema operativo."""
        sys_platform = platform.system()
        if sys_platform == "Windows":
            possible_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
                os.path.expanduser("~") + r"\scoop\apps\vlc\current\vlc.exe",
                "vlc.exe" # Check PATH
            ]
        elif sys_platform == "Linux":
            possible_paths = ["/usr/bin/vlc", "/usr/local/bin/vlc", "vlc"] # Check PATH
        elif sys_platform == "Darwin": # macOS
            possible_paths = ["/Applications/VLC.app/Contents/MacOS/VLC", "/usr/bin/vlc", "vlc"] # Check PATH
        else:
            possible_paths = ["vlc"] # Fallback to PATH

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None # Not found

    def play(self, url):
        """Carga un URL y lo reproduce."""
        if not self._ensure_vlc_running():
            self.logger.error("VLC no está en ejecución.")
            return False
        try:
            media = self.instance.media_new(url)
            self.player.set_media(media)
            result = self.player.play()
            if result == -1:
                self.logger.error(f"Error al reproducir URL: VLC error code {result}")
                return False
            self.is_playing = True
            self.current_url = url
            self.logger.info(f"Reproduciendo URL: {url}")
            return True
        except Exception as e:
            self.logger.error(f"Error reproduciendo URL en VLC: {e}")
            return False

    def play_youtube_audio(self, youtube_url):
        """Reproduce audio de YouTube usando yt-dlp, asegurando una sola instancia."""
        if self.is_playing and self.current_url == youtube_url:
            self.logger.info("El video ya se está reproduciendo.")
            return True  # Ya se está reproduciendo el mismo video
        
        if not self._ensure_vlc_running():
            self.logger.error("VLC no está en ejecución.")
            return False

        try:
            ydl_command = [
                "yt-dlp",
                "-f", "bestaudio",
                "-o", "-",  # Output to stdout
                "--no-playlist",
                youtube_url
            ]
            self.logger.info(f"Ejecutando yt-dlp: {' '.join(ydl_command)}")
            ydl_process = subprocess.Popen(ydl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Comprobar si ya hay algo reproduciéndose
            if self.is_playing:
                self.logger.info("Cambiando de URL en la instancia existente de VLC.")
                self.player.stop()  # Detenemos la reproducción actual

            vlc_media = self.instance.media_new_fd(ydl_process.stdout.fileno())  # Play from file descriptor
            self.player.set_media(vlc_media)

            result = self.player.play()
            if result == -1:
                error_output = ydl_process.stderr.read().decode('utf-8')
                self.logger.error(f"Error al reproducir stream de YouTube: VLC error code {result}, yt-dlp error: {error_output}")
                return False

            self.is_playing = True
            self.current_url = youtube_url
            self.logger.info(f"Reproduciendo audio de YouTube URL: {youtube_url}")
            return True

        except FileNotFoundError:
            self.logger.error("yt-dlp no encontrado. Asegúrate de que esté instalado y en el PATH.")
            return False
        except Exception as e:
            self.logger.error(f"Error al reproducir audio de YouTube con VLC: {e}")
            return False



    def pause_or_resume(self):
        """Pausa o reanuda la reproducción."""
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.logger.info("Pausado VLC.")
        else:
            self.player.play()
            self.is_playing = True
            self.logger.info("Reanudando VLC.")

    def stop(self):
        """Detiene la reproducción."""
        self.player.stop()
        self.is_playing = False
        self.logger.info("Detenido VLC.")
        self.current_url = None

    def set_volume(self, volume):
        """Establece el volumen (0-100)."""
        if not isinstance(volume, (int, float)) or not (0 <= volume <= 100):
            self.logger.warning(f"Volumen inválido: {volume}. Debe estar entre 0 y 100.")
            return False
        vlc_volume = int((volume / 100) * 255) # VLC volume is in range 0-255
        self.player.audio_set_volume(vlc_volume)
        self.logger.info(f"Volumen establecido a {volume}% (VLC: {vlc_volume}).")

    def get_state(self):
        """Obtiene el estado actual de VLC."""
        state = self.player.get_state()
        state_name = {
            vlc.State.NothingSpecial: 'Nothing Special',
            vlc.State.Opening: 'Opening',
            vlc.State.Buffering: 'Buffering',
            vlc.State.Playing: 'Playing',
            vlc.State.Paused: 'Paused',
            vlc.State.Stopped: 'Stopped',
            vlc.State.Ended: 'Ended',
            vlc.State.Error: 'Error'
        }
        return state_name.get(state, 'Unknown')

    def get_time(self):
        """Obtiene el tiempo de reproducción actual en segundos."""
        return self.player.get_time() / 1000.0 # VLC time is in milliseconds

    def get_length(self):
        """Obtiene la duración total del medio en segundos."""
        return self.player.get_length() / 1000.0 # VLC length is in milliseconds

    def seek(self, seconds):
        """Avanza o retrocede el tiempo de reproducción en segundos."""
        if not isinstance(seconds, (int, float)):
            self.logger.warning(f"Valor de seek inválido: {seconds}. Debe ser un número.")
            return False
        current_time_ms = self.player.get_time()
        seek_time_ms = int(current_time_ms + seconds * 1000)
        if seek_time_ms < 0:
            seek_time_ms = 0
        self.player.set_time(seek_time_ms)
        self.logger.info(f"Seek VLC a {seconds} segundos. Nuevo tiempo: {seek_time_ms / 1000.0} segundos.")
        return True

    def is_playing_youtube(self):
        """Verifica si actualmente se está reproduciendo un URL de YouTube."""
        if self.current_url and "youtube.com" in self.current_url:
            return True
        return False


    def close(self):
        """Detiene la reproducción y libera recursos."""
        self.stop()
        if self.vlc_process and self.vlc_process.poll() is None:
            try:
                self.vlc_process.terminate()
                self.vlc_process.wait(timeout=5)
                self.logger.info("Proceso VLC terminado.")
            except subprocess.TimeoutExpired:
                self.vlc_process.kill()
                self.logger.warning("Proceso VLC matado a la fuerza.")
            except Exception as e:
                self.logger.error(f"Error al terminar proceso VLC: {e}")
            finally:
                self.vlc_process = None
        self.logger.info("VLC player closed.")

    def __del__(self):
        """Asegura que VLC se cierre cuando el objeto Python se elimina."""
        self.close()

    # Métodos adicionales para la clase VLCPlayer

    def get_volume(self):
        """Obtiene el volumen actual (0-100)."""
        vlc_volume = self.player.audio_get_volume()
        volume = int((vlc_volume / 255) * 100)  # Convertir de escala VLC (0-255) a porcentaje (0-100)
        self.logger.info(f"Volumen actual: {volume}%")
        return volume

    def mute(self):
        """Silencia el audio."""
        self.player.audio_set_mute(True)
        self.logger.info("Audio silenciado.")
        return True

    def unmute(self):
        """Desactiva el silencio del audio."""
        self.player.audio_set_mute(False)
        self.logger.info("Audio activado.")
        return True

    def is_muted(self):
        """Verifica si el audio está silenciado."""
        return self.player.audio_get_mute()

    def set_position(self, position):
        """
        Establece la posición de reproducción como un porcentaje (0.0 - 1.0).
        
        Args:
            position (float): Valor entre 0.0 y 1.0 que representa la posición relativa.
        
        Returns:
            bool: True si se estableció correctamente, False en caso contrario.
        """
        if not isinstance(position, (int, float)) or not (0 <= position <= 1):
            self.logger.warning(f"Posición inválida: {position}. Debe estar entre 0.0 y 1.0.")
            return False
        
        self.player.set_position(float(position))
        self.logger.info(f"Posición establecida a {position*100}%")
        return True

    def get_position(self):
        """
        Obtiene la posición actual de reproducción como un porcentaje (0.0 - 1.0).
        
        Returns:
            float: Valor entre 0.0 y 1.0 que representa la posición relativa.
        """
        position = self.player.get_position()
        self.logger.info(f"Posición actual: {position*100:.2f}%")
        return position

    def get_media_info(self):
        """
        Obtiene información sobre el medio actual.
        
        Returns:
            dict: Diccionario con información del medio actual.
        """
        if not self.player.get_media():
            self.logger.warning("No hay medio cargado actualmente.")
            return {}
        
        media = self.player.get_media()
        info = {
            'duration': self.get_length(),
            'state': self.get_state(),
            'url': self.current_url,
            'is_playing': self.is_playing,
            'current_time': self.get_time()
        }
        
        # Intentar obtener metadata (título, artista, etc.)
        media.parse()
        info['title'] = media.get_meta(vlc.Meta.Title)
        info['artist'] = media.get_meta(vlc.Meta.Artist)
        info['album'] = media.get_meta(vlc.Meta.Album)
        info['track_number'] = media.get_meta(vlc.Meta.TrackNumber)
        info['genre'] = media.get_meta(vlc.Meta.Genre)
        
        self.logger.info(f"Información del medio obtenida: {info}")
        return info

    def set_rate(self, rate):
        """
        Establece la velocidad de reproducción.
        
        Args:
            rate (float): Velocidad de reproducción (1.0 es normal, 2.0 es doble velocidad, etc.)
        
        Returns:
            bool: True si se estableció correctamente, False en caso contrario.
        """
        if not isinstance(rate, (int, float)) or rate <= 0:
            self.logger.warning(f"Velocidad inválida: {rate}. Debe ser un número positivo.")
            return False
        
        self.player.set_rate(float(rate))
        self.logger.info(f"Velocidad establecida a {rate}x")
        return True

    def get_rate(self):
        """
        Obtiene la velocidad de reproducción actual.
        
        Returns:
            float: Velocidad de reproducción actual.
        """
        rate = self.player.get_rate()
        self.logger.info(f"Velocidad actual: {rate}x")
        return rate

    def toggle_fullscreen(self):
        """
        Alterna el modo de pantalla completa.
        
        Returns:
            bool: True si se activó la pantalla completa, False si se desactivó.
        """
        is_fullscreen = self.player.get_fullscreen()
        self.player.set_fullscreen(not is_fullscreen)
        new_state = not is_fullscreen
        self.logger.info(f"Pantalla completa: {'activada' if new_state else 'desactivada'}")
        return new_state

    def play_playlist(self, urls):
        """
        Reproduce una lista de URLs como una playlist.
        
        Args:
            urls (list): Lista de URLs para reproducir.
        
        Returns:
            bool: True si se inició la reproducción, False en caso contrario.
        """
        if not isinstance(urls, list) or not urls:
            self.logger.warning("Lista de URLs inválida.")
            return False
        
        try:
            # Crear una lista de reproducción
            playlist = self.instance.media_list_new()
            for url in urls:
                media = self.instance.media_new(url)
                playlist.add_media(media)
            
            # Crear un reproductor de lista
            list_player = self.instance.media_list_player_new()
            list_player.set_media_list(playlist)
            list_player.set_media_player(self.player)
            
            # Iniciar reproducción
            list_player.play()
            self.is_playing = True
            self.logger.info(f"Reproduciendo playlist con {len(urls)} elementos.")
            return True
        except Exception as e:
            self.logger.error(f"Error al reproducir playlist: {e}")
            return False

    def add_event_listener(self, event_type, callback):
        """
        Agrega un listener para un evento específico.
        
        Args:
            event_type (vlc.EventType): Tipo de evento a escuchar.
            callback (function): Función callback a llamar cuando ocurra el evento.
        
        Returns:
            bool: True si se agregó correctamente, False en caso contrario.
        """
        try:
            event_manager = self.player.event_manager()
            event_manager.event_attach(event_type, callback)
            self.logger.info(f"Listener agregado para evento {event_type}")
            return True
        except Exception as e:
            self.logger.error(f"Error al agregar listener de evento: {e}")
            return False

    def remove_event_listener(self, event_type, callback):
        """
        Elimina un listener para un evento específico.
        
        Args:
            event_type (vlc.EventType): Tipo de evento.
            callback (function): Función callback a eliminar.
        
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario.
        """
        try:
            event_manager = self.player.event_manager()
            event_manager.event_detach(event_type, callback)
            self.logger.info(f"Listener eliminado para evento {event_type}")
            return True
        except Exception as e:
            self.logger.error(f"Error al eliminar listener de evento: {e}")
            return False

    def get_audio_tracks(self):
        """
        Obtiene una lista de pistas de audio disponibles.
        
        Returns:
            list: Lista de pistas de audio disponibles.
        """
        tracks = []
        media = self.player.get_media()
        if media:
            for i in range(self.player.audio_get_track_count()):
                track_info = self.player.audio_get_track_description(i)
                if track_info:
                    tracks.append({
                        'id': track_info[0],
                        'name': track_info[1].decode('utf-8') if isinstance(track_info[1], bytes) else track_info[1]
                    })
        self.logger.info(f"Pistas de audio disponibles: {tracks}")
        return tracks

    def set_audio_track(self, track_id):
        """
        Establece la pista de audio a utilizar.
        
        Args:
            track_id (int): ID de la pista de audio.
        
        Returns:
            bool: True si se estableció correctamente, False en caso contrario.
        """
        if not isinstance(track_id, int):
            self.logger.warning(f"ID de pista inválido: {track_id}. Debe ser un entero.")
            return False
        
        result = self.player.audio_set_track(track_id)
        if result == 0:
            self.logger.info(f"Pista de audio establecida a {track_id}")
            return True
        else:
            self.logger.error(f"Error al establecer pista de audio {track_id}: {result}")
            return False

    def download_youtube_audio(self, youtube_url, output_file):
        """
        Descarga el audio de un video de YouTube.
        
        Args:
            youtube_url (str): URL del video de YouTube.
            output_file (str): Ruta donde guardar el archivo de audio.
        
        Returns:
            bool: True si se descargó correctamente, False en caso contrario.
        """
        try:
            ydl_command = [
                "yt-dlp",
                "-f", "bestaudio",
                "-o", output_file,
                "--no-playlist",
                youtube_url
            ]
            self.logger.info(f"Ejecutando yt-dlp para descargar: {' '.join(ydl_command)}")
            process = subprocess.Popen(ydl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.logger.info(f"Audio descargado exitosamente a {output_file}")
                return True
            else:
                self.logger.error(f"Error al descargar audio: {stderr.decode('utf-8')}")
                return False
        except FileNotFoundError:
            self.logger.error("yt-dlp no encontrado. Asegúrate de que esté instalado y en el PATH.")
            return False
        except Exception as e:
            self.logger.error(f"Error al descargar audio de YouTube: {e}")
            return False