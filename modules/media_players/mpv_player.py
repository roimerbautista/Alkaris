# START OF FILE mpv_player.py ---
# Description: Controlador simple para el reproductor MPV.
import os
import subprocess
import logging
import psutil
import platform # Import platform module

class MPVPlayer:
    def __init__(self):
        self.logger = self._setup_logger()
        self.current_process = None
        self.current_url = None

    def _setup_logger(self):
        logger = logging.getLogger('mpv_player')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def play_video(self, url):
        """Reproduce un video URL en MPV asegurando una sola instancia."""
        if self.current_url == url and self.is_playing():
            self.logger.info("El video ya se está reproduciendo en MPV.")
            return True

        # Si hay un proceso previo, lo cerramos
        self.stop()

        cmd = ['mpv', url]
        try:
            self.logger.info(f"Reproduciendo en MPV: {' '.join(cmd)}")
            self.current_process = subprocess.Popen(cmd, stdin=subprocess.PIPE)  # <== stdin agregado aquí
            self.current_url = url
            return True
        except Exception as e:
            self.logger.error(f"Error al reproducir URL en MPV: {e}")
            return False

        
    def pause(self):
        """Pausa la reproducción en MPV si está reproduciendo."""
        if self.is_playing():
            try:
                self.logger.info("Pausando MPV.")
                self.current_process.stdin.write(b"p\n")  # Comando "p" para pausar
                self.current_process.stdin.flush()  # Asegura el envío del comando
            except Exception as e:
                self.logger.error(f"Error al pausar MPV: {e}")

    def resume(self):
        """Reanuda la reproducción en MPV si está pausada."""
        if self.is_playing():
            try:
                self.logger.info("Reanudando MPV.")
                self.current_process.stdin.write(b"p\n")  # El mismo comando "p" reanuda
                self.current_process.stdin.flush()  # Asegura el envío del comando
            except Exception as e:
                self.logger.error(f"Error al reanudar MPV: {e}")




    def is_playing(self):
        """Verifica si hay una reproducción activa en MPV."""
        return self.current_process is not None and self.current_process.poll() is None

    def stop(self):
        """Detiene la reproducción actual de MPV si está activa."""
        if self.is_playing():
            self.logger.info("Deteniendo reproducción actual de MPV.")
            self.current_process.terminate()  # Terminamos el proceso MPV
            try:
                self.current_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning("El proceso MPV no respondió. Matando el proceso...")
                self.current_process.kill()
            finally:
                self.current_process = None
                self.current_url = None

    def close(self):
        """Detiene y libera recursos."""
        self.stop()
        self.logger.info("MPV player cerrado.")
