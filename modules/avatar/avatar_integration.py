import threading
import time
import numpy as np
import pygame
from .avatar_3d import Avatar3D

class AvatarManager:
    """Gestor del avatar 3D integrado con el asistente de voz"""
    
    def __init__(self):
        self.avatar = None
        self.avatar_thread = None
        self.is_running = False
        self.audio_level = 0.0
        self.is_speaking = False
        self.is_listening = False
        
    def start_avatar(self, app_instance=None):
        """Iniciar el avatar 3D en un hilo separado"""
        if not self.is_running:
            self.is_running = True
            self.avatar_thread = threading.Thread(target=self._run_avatar, args=(app_instance,))
            self.avatar_thread.daemon = True
            self.avatar_thread.start()
            print("Avatar 3D iniciado")
    
    def _run_avatar(self, app_instance=None):
        """Ejecutar el avatar en un hilo separado"""
        try:
            self.avatar = Avatar3D(1200, 800, app_instance)
            self.avatar.running = True  # Activar el avatar
            
            # Sincronizar configuración inicial
            if app_instance:
                self.avatar.slider_value = app_instance.energy_threshold
                self.avatar.energy_threshold = app_instance.energy_threshold
            
            # Ejecutar el bucle principal del avatar
            self.avatar.run()
                
        except Exception as e:
            print(f"Error en avatar: {e}")
        finally:
            if self.avatar:
                self.avatar.stop()
    
    def on_speech_start(self):
        """Llamar cuando el asistente comience a hablar"""
        self.is_speaking = True
        if self.avatar:
            self.avatar.start_speaking(0.7)
    
    def on_speech_end(self):
        """Llamar cuando el asistente termine de hablar"""
        self.is_speaking = False
        if self.avatar:
            self.avatar.stop_speaking()
    
    def on_listening_start(self):
        """Llamar cuando el asistente comience a escuchar"""
        self.is_listening = True
        if self.avatar:
            # Indicar que está escuchando
            self.avatar.set_listening(True)
    
    def on_listening_end(self):
        """Llamar cuando el asistente termine de escuchar"""
        self.is_listening = False
        if self.avatar:
            # Ya no está escuchando
            self.avatar.set_listening(False)
    
    def update_audio_level(self, level):
        """Actualizar el nivel de audio para animaciones"""
        self.audio_level = max(0.0, min(1.0, level))
        if self.avatar and self.is_speaking:
            self.avatar.update_audio_level(self.audio_level)
    
    def make_blink(self):
        """Hacer que el avatar parpadee"""
        if self.avatar:
            self.avatar.blink()
    
    def set_emotion(self, emotion):
        """Cambiar la expresión del avatar según la emoción"""
        if not self.avatar:
            return
            
        # Usar el método set_emotion del avatar
        self.avatar.set_emotion(emotion)
    
    def stop_avatar(self):
        """Detener el avatar"""
        self.is_running = False
        if self.avatar:
            self.avatar.running = False
            self.avatar.stop()
        if self.avatar_thread:
            self.avatar_thread.join(timeout=2.0)
        print("Avatar 3D detenido")
    
    def is_avatar_running(self):
        """Verificar si el avatar está ejecutándose"""
        return self.is_running and self.avatar is not None

# Instancia global del gestor de avatar
avatar_manager = AvatarManager()

# Funciones de conveniencia para integración
def start_3d_avatar(app_instance=None):
    """Iniciar el avatar 3D"""
    avatar_manager.start_avatar(app_instance)

def stop_3d_avatar():
    """Detener el avatar 3D"""
    avatar_manager.stop_avatar()

def on_assistant_speaking():
    """Notificar que el asistente está hablando"""
    avatar_manager.on_speech_start()

def on_assistant_silent():
    """Notificar que el asistente está en silencio"""
    avatar_manager.on_speech_end()

def on_assistant_listening():
    """Notificar que el asistente está escuchando"""
    avatar_manager.on_listening_start()

def on_assistant_not_listening():
    """Notificar que el asistente no está escuchando"""
    avatar_manager.on_listening_end()

def update_speech_level(level):
    """Actualizar el nivel de audio del habla"""
    avatar_manager.update_audio_level(level)

def set_avatar_emotion(emotion):
    """Cambiar la emoción del avatar"""
    avatar_manager.set_emotion(emotion)

def make_avatar_blink():
    """Hacer que el avatar parpadee"""
    avatar_manager.make_blink()