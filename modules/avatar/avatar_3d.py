#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Avatar 3D con OpenGL para el Asistente de Voz
Este módulo implementa un avatar 3D usando Pygame y OpenGL básico
"""

import pygame
import numpy as np
import math
import time
import threading
from typing import Optional, Tuple
try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    OPENGL_AVAILABLE = True
except ImportError:
    print("OpenGL no disponible, usando renderizado 2D")
    OPENGL_AVAILABLE = False
import json
import os

class Avatar3D:
    def __init__(self, width=700, height=500, app_instance=None):
        """Inicializar el avatar 3D mejorado"""
        self.width = width
        self.height = height
        self.running = False
        self.app_instance = app_instance  # Referencia a la aplicación principal
        
        # Estado del avatar
        self.is_speaking = False
        self.is_listening = False
        self.speech_level = 0.0
        self.blink_timer = 0.0
        self.head_rotation = 0.0
        self.emotion = "neutral"
        
        # Configuración de animación
        self.blink_duration = 0.15
        self.blink_interval = 3.0
        self.last_blink = time.time()
        
        # Variables de tiempo
        self.clock = pygame.time.Clock()
        self.start_time = time.time()
        
        # Variables de GUI integrada
        self.energy_threshold = 5000
        self.youtube_search_text = ""
        self.input_active = False
        self.slider_dragging = False
        self.slider_value = 5000
        
        # Panel de logs desplegable
        self.logs_panel_open = False
        self.logs_panel_height = 200
        self.logs_scroll_offset = 0
        self.command_logs = []
        self.max_logs = 50
        
        # Visualizador de música
        self.music_bars = [0.0] * 20  # 20 barras para el visualizador
        self.music_playing = False
        self.music_volume = 0.0
        
        # Posiciones de elementos GUI
        self.slider_rect = None
        self.input_rect = None
        self.button_rects = {}
        self.logs_toggle_rect = None
        
        # Inicializar pygame
        self._init_pygame()
        
        # Inicializar OpenGL si está disponible
        if OPENGL_AVAILABLE:
            self._init_opengl()
        else:
            self._init_2d_fallback()
    
    def _init_pygame(self):
        """Inicializar pygame"""
        pygame.init()
        if OPENGL_AVAILABLE:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.OPENGL | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Alkaris - Asistente 3D")
    
    def _init_opengl(self):
        """Configurar parámetros básicos de OpenGL"""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        
        # Configurar la luz
        glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        
        # Configurar la perspectiva
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, self.width/self.height, 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)
    
    def _init_2d_fallback(self):
        """Inicializar modo 2D de respaldo"""
        self.font = pygame.font.Font(None, 36)
        self.face_color = (255, 220, 177)  # Color piel
        self.eye_color = (0, 0, 0)  # Negro
        self.mouth_color = (200, 100, 100)  # Rojo
    
    def draw_sphere_opengl(self, radius=1.0, slices=20, stacks=20):
        """Dibujar una esfera usando OpenGL básico"""
        for i in range(stacks):
            lat1 = math.pi * (-0.5 + float(i) / stacks)
            lat2 = math.pi * (-0.5 + float(i + 1) / stacks)
            
            glBegin(GL_QUAD_STRIP)
            for j in range(slices + 1):
                lon = 2 * math.pi * float(j) / slices
                
                x1 = radius * math.cos(lat1) * math.cos(lon)
                y1 = radius * math.sin(lat1)
                z1 = radius * math.cos(lat1) * math.sin(lon)
                
                x2 = radius * math.cos(lat2) * math.cos(lon)
                y2 = radius * math.sin(lat2)
                z2 = radius * math.cos(lat2) * math.sin(lon)
                
                glNormal3f(x1/radius, y1/radius, z1/radius)
                glVertex3f(x1, y1, z1)
                
                glNormal3f(x2/radius, y2/radius, z2/radius)
                glVertex3f(x2, y2, z2)
            glEnd()
    
    def draw_circle_2d(self, surface, center, radius, color):
        """Dibujar un círculo en 2D"""
        pygame.draw.circle(surface, color, center, radius)
    
    def draw_ellipse_2d(self, surface, rect, color):
        """Dibujar una elipse en 2D"""
        pygame.draw.ellipse(surface, color, rect)
    
    def _draw_gradient_background(self):
        """Dibujar fondo con degradado"""
        for y in range(self.height):
            ratio = y / self.height
            r = int(15 + ratio * 35)  # De 15 a 50
            g = int(15 + ratio * 35)  # De 15 a 50
            b = int(50 + ratio * 50)  # De 50 a 100
            color = (r, g, b)
            pygame.draw.line(self.screen, color, (0, y), (self.width, y))
    
    def _draw_info_panel(self):
        """Dibujar panel de información lateral con controles integrados"""
        panel_width = 250  # Reducido para ventana más pequeña
        panel_height = self.height
        panel_x = self.width - panel_width
        panel_y = 0
        
        # Fondo del panel con transparencia
        panel_surface = pygame.Surface((panel_width, panel_height))
        panel_surface.set_alpha(180)
        panel_surface.fill((20, 25, 40))
        self.screen.blit(panel_surface, (panel_x, panel_y))
        
        # Borde del panel
        pygame.draw.rect(self.screen, (100, 120, 150), 
                        (panel_x, panel_y, panel_width, panel_height), 2)
        
        # Título
        title_font = pygame.font.Font(None, 28)
        asistente_name = self.app_instance.asistente_nombre if self.app_instance else "Alkaris"
        title_text = title_font.render(f"Asistente: {asistente_name}", True, (255, 255, 255))
        self.screen.blit(title_text, (panel_x + 10, panel_y + 10))
        
        # Información del estado
        info_font = pygame.font.Font(None, 20)
        y_offset = 50
        
        # Estado actual
        if self.is_speaking:
            status = "Hablando"
            status_color = (100, 255, 100)
        elif self.is_listening:
            status = "Escuchando"
            status_color = (100, 150, 255)
        else:
            status = "Inactivo"
            status_color = (200, 200, 200)
        
        status_text = info_font.render(f"Estado: {status}", True, status_color)
        self.screen.blit(status_text, (panel_x + 10, panel_y + y_offset))
        y_offset += 30
        
        # Nivel de audio
        audio_level = int(self.speech_level * 100)
        audio_text = info_font.render(f"Audio: {audio_level}%", True, (255, 255, 255))
        self.screen.blit(audio_text, (panel_x + 10, panel_y + y_offset))
        
        # Barra de nivel de audio
        bar_width = 200
        bar_height = 10
        bar_x = panel_x + 10
        bar_y = panel_y + y_offset + 25
        
        # Fondo de la barra
        pygame.draw.rect(self.screen, (50, 50, 50), 
                        (bar_x, bar_y, bar_width, bar_height))
        
        # Barra de progreso
        progress_width = int(bar_width * self.speech_level)
        if progress_width > 0:
            color = (100, 255, 100) if self.is_speaking else (100, 150, 255)
            pygame.draw.rect(self.screen, color, 
                            (bar_x, bar_y, progress_width, bar_height))
        
        y_offset += 50
        
        # Slider de supresión de ruido
        self._draw_noise_slider(panel_x, panel_y, y_offset)
        y_offset += 80
        
        # Campo de entrada para YouTube
        self._draw_youtube_input(panel_x, panel_y, y_offset)
        y_offset += 80
        
        # Botones de control
        self._draw_control_buttons(panel_x, panel_y, y_offset)
        y_offset += 120
        
        # Indicador de estado circular
        self._draw_status_circle(panel_x, panel_y, y_offset)
        y_offset += 80
        
        # Emoción y tiempo
        emotion_text = info_font.render(f"Emoción: {self.emotion.title()}", True, (255, 255, 255))
        self.screen.blit(emotion_text, (panel_x + 10, panel_y + y_offset))
        y_offset += 30
        
        # Tiempo activo
        active_time = int(time.time() - self.start_time)
        minutes = active_time // 60
        seconds = active_time % 60
        time_text = info_font.render(f"Tiempo: {minutes:02d}:{seconds:02d}", True, (255, 255, 255))
        self.screen.blit(time_text, (panel_x + 10, panel_y + y_offset))
        y_offset += 40
        
        # Visualizador de música
        self._draw_music_visualizer(panel_x, panel_y, y_offset)
        y_offset += 80
        
        # Botón de logs
        self._draw_logs_toggle_button(panel_x, panel_y, y_offset)
        y_offset += 40
    
    def _draw_noise_slider(self, panel_x, panel_y, y_offset):
        """Dibujar slider de supresión de ruido"""
        font = pygame.font.Font(None, 18)
        label = font.render("Supresión de ruido:", True, (255, 255, 255))
        self.screen.blit(label, (panel_x + 10, panel_y + y_offset))
        
        # Slider
        slider_x = panel_x + 20
        slider_y = panel_y + y_offset + 25
        slider_width = 180  # Ajustado para panel más pequeño
        slider_height = 20
        
        self.slider_rect = pygame.Rect(slider_x, slider_y, slider_width, slider_height)
        
        # Fondo del slider
        pygame.draw.rect(self.screen, (60, 60, 60), self.slider_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), self.slider_rect, 2)
        
        # Posición del handle
        handle_pos = slider_x + (self.slider_value / 10000) * (slider_width - 20)
        handle_rect = pygame.Rect(handle_pos, slider_y, 20, slider_height)
        
        # Handle del slider
        pygame.draw.rect(self.screen, (150, 150, 255), handle_rect)
        pygame.draw.rect(self.screen, (200, 200, 255), handle_rect, 2)
        
        # Valor actual
        value_text = font.render(f"{int(self.slider_value)}", True, (255, 255, 255))
        self.screen.blit(value_text, (panel_x + 210, panel_y + y_offset + 25))
    
    def _draw_youtube_input(self, panel_x, panel_y, y_offset):
        """Dibujar campo de entrada para YouTube"""
        font = pygame.font.Font(None, 18)
        label = font.render("Buscar en YouTube:", True, (255, 255, 255))
        self.screen.blit(label, (panel_x + 10, panel_y + y_offset))
        
        # Campo de entrada
        input_x = panel_x + 20
        input_y = panel_y + y_offset + 25
        input_width = 180  # Ajustado para panel más pequeño
        input_height = 25
        
        self.input_rect = pygame.Rect(input_x, input_y, input_width, input_height)
        
        # Fondo del input
        color = (80, 80, 120) if self.input_active else (60, 60, 80)
        pygame.draw.rect(self.screen, color, self.input_rect)
        pygame.draw.rect(self.screen, (150, 150, 200), self.input_rect, 2)
        
        # Texto
        text_surface = font.render(self.youtube_search_text, True, (255, 255, 255))
        self.screen.blit(text_surface, (input_x + 5, input_y + 5))
        
        # Cursor parpadeante
        if self.input_active and int(time.time() * 2) % 2:
            cursor_x = input_x + 5 + text_surface.get_width()
            pygame.draw.line(self.screen, (255, 255, 255), 
                           (cursor_x, input_y + 3), (cursor_x, input_y + input_height - 3), 2)
    
    def _draw_control_buttons(self, panel_x, panel_y, y_offset):
        """Dibujar botones de control"""
        font = pygame.font.Font(None, 18)
        button_width = 80
        button_height = 30
        button_spacing = 10
        
        buttons = [
            ("Escuchar", "listen", (100, 255, 100)),
            ("Parar", "stop", (255, 100, 100)),
            ("YouTube", "youtube", (255, 255, 100))
        ]
        
        for i, (text, key, color) in enumerate(buttons):
            button_x = panel_x + 20 + (i % 2) * (button_width + button_spacing)
            button_y = panel_y + y_offset + (i // 2) * (button_height + button_spacing)
            
            button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            self.button_rects[key] = button_rect
            
            # Fondo del botón
            pygame.draw.rect(self.screen, color, button_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), button_rect, 2)
            
            # Texto del botón
            text_surface = font.render(text, True, (0, 0, 0))
            text_x = button_x + (button_width - text_surface.get_width()) // 2
            text_y = button_y + (button_height - text_surface.get_height()) // 2
            self.screen.blit(text_surface, (text_x, text_y))
    
    def _draw_status_circle(self, panel_x, panel_y, y_offset):
        """Dibujar círculo de estado"""
        center_x = panel_x + 150
        center_y = panel_y + y_offset + 30
        radius = 25
        
        # Color según el estado
        if self.is_speaking:
            color = (100, 255, 100)
            status_text = "Hablando"
        elif self.is_listening:
            color = (100, 150, 255)
            status_text = "Escuchando"
        else:
            color = (200, 200, 200)
            status_text = "Inactivo"
        
        # Círculo principal
        pygame.draw.circle(self.screen, color, (center_x, center_y), radius)
        pygame.draw.circle(self.screen, (255, 255, 255), (center_x, center_y), radius, 3)
        
        # Texto del estado
        font = pygame.font.Font(None, 16)
        text_surface = font.render(status_text, True, (255, 255, 255))
        text_x = center_x - text_surface.get_width() // 2
        text_y = center_y + radius + 10
        self.screen.blit(text_surface, (text_x, text_y))
    
    def _draw_music_visualizer(self, panel_x, panel_y, y_offset):
        """Dibujar visualizador de música con barras"""
        font = pygame.font.Font(None, 18)
        label = font.render("Visualizador de Música:", True, (255, 255, 255))
        self.screen.blit(label, (panel_x + 10, panel_y + y_offset))
        
        # Área del visualizador
        viz_x = panel_x + 20
        viz_y = panel_y + y_offset + 25
        viz_width = 180
        viz_height = 40
        
        # Fondo del visualizador
        pygame.draw.rect(self.screen, (20, 20, 30), 
                        (viz_x, viz_y, viz_width, viz_height))
        pygame.draw.rect(self.screen, (100, 100, 120), 
                        (viz_x, viz_y, viz_width, viz_height), 2)
        
        # Dibujar barras
        bar_width = viz_width // len(self.music_bars)
        for i, bar_height in enumerate(self.music_bars):
            bar_x = viz_x + i * bar_width
            bar_actual_height = int(bar_height * viz_height)
            bar_y = viz_y + viz_height - bar_actual_height
            
            # Color de la barra según la altura
            if bar_height > 0.7:
                color = (255, 100, 100)  # Rojo para niveles altos
            elif bar_height > 0.4:
                color = (255, 255, 100)  # Amarillo para niveles medios
            else:
                color = (100, 255, 100)  # Verde para niveles bajos
            
            if bar_actual_height > 0:
                pygame.draw.rect(self.screen, color, 
                               (bar_x + 1, bar_y, bar_width - 2, bar_actual_height))
        
        # Indicador de estado de música
        status_text = "♪ Reproduciendo" if self.music_playing else "♪ Silencio"
        status_color = (100, 255, 100) if self.music_playing else (150, 150, 150)
        status_surface = font.render(status_text, True, status_color)
        self.screen.blit(status_surface, (panel_x + 10, panel_y + y_offset + 50))
    
    def _draw_logs_toggle_button(self, panel_x, panel_y, y_offset):
        """Dibujar botón para mostrar/ocultar logs"""
        button_width = 180
        button_height = 25
        button_x = panel_x + 20
        button_y = panel_y + y_offset
        
        self.logs_toggle_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        
        # Color del botón según el estado
        color = (100, 150, 200) if self.logs_panel_open else (80, 80, 120)
        pygame.draw.rect(self.screen, color, self.logs_toggle_rect)
        pygame.draw.rect(self.screen, (200, 200, 255), self.logs_toggle_rect, 2)
        
        # Texto del botón
        font = pygame.font.Font(None, 18)
        text = "▼ Ocultar Logs" if self.logs_panel_open else "▶ Mostrar Logs"
        text_surface = font.render(text, True, (255, 255, 255))
        text_x = button_x + (button_width - text_surface.get_width()) // 2
        text_y = button_y + (button_height - text_surface.get_height()) // 2
        self.screen.blit(text_surface, (text_x, text_y))
    
    def _draw_logs_panel(self):
        """Dibujar panel de logs desplegable"""
        if not self.logs_panel_open:
            return
        
        # Posición del panel de logs (parte inferior)
        panel_x = 10
        panel_y = self.height - self.logs_panel_height - 10
        panel_width = self.width - 20
        panel_height = self.logs_panel_height
        
        # Fondo del panel con transparencia
        logs_surface = pygame.Surface((panel_width, panel_height))
        logs_surface.set_alpha(220)
        logs_surface.fill((15, 15, 25))
        self.screen.blit(logs_surface, (panel_x, panel_y))
        
        # Borde del panel
        pygame.draw.rect(self.screen, (100, 150, 200), 
                        (panel_x, panel_y, panel_width, panel_height), 2)
        
        # Título del panel
        title_font = pygame.font.Font(None, 20)
        title_text = title_font.render("📋 Registro de Comandos y Respuestas", True, (255, 255, 255))
        self.screen.blit(title_text, (panel_x + 10, panel_y + 5))
        
        # Área de logs
        logs_area_y = panel_y + 30
        logs_area_height = panel_height - 35
        
        # Dibujar logs
        font = pygame.font.Font(None, 16)
        line_height = 18
        visible_lines = logs_area_height // line_height
        
        # Calcular qué logs mostrar
        start_index = max(0, len(self.command_logs) - visible_lines - self.logs_scroll_offset)
        end_index = min(len(self.command_logs), start_index + visible_lines)
        
        for i, log_entry in enumerate(self.command_logs[start_index:end_index]):
            y_pos = logs_area_y + i * line_height
            
            # Color según el tipo de log
            if log_entry['type'] == 'command':
                color = (150, 255, 150)  # Verde para comandos
                prefix = "🎤"
            elif log_entry['type'] == 'response':
                color = (150, 150, 255)  # Azul para respuestas
                prefix = "🔊"
            elif log_entry['type'] == 'error':
                color = (255, 150, 150)  # Rojo para errores
                prefix = "❌"
            else:
                color = (200, 200, 200)  # Gris para info
                prefix = "ℹ️"
            
            # Formatear el texto del log
            log_text = f"[{log_entry['timestamp']}] {prefix} {log_entry['message']}"
            
            # Truncar si es muy largo
            max_chars = (panel_width - 20) // 8  # Aproximación de caracteres por línea
            if len(log_text) > max_chars:
                log_text = log_text[:max_chars-3] + "..."
            
            text_surface = font.render(log_text, True, color)
            self.screen.blit(text_surface, (panel_x + 10, y_pos))
        
        # Indicador de scroll si hay más logs
        if len(self.command_logs) > visible_lines:
            scroll_indicator = f"({len(self.command_logs) - visible_lines - self.logs_scroll_offset}/{len(self.command_logs)})"
            scroll_text = font.render(scroll_indicator, True, (150, 150, 150))
            self.screen.blit(scroll_text, (panel_x + panel_width - 100, panel_y + 5))
    
    def _draw_status_indicators(self):
        """Dibujar indicadores de estado en la parte superior"""
        # Indicador de conexión
        connection_color = (100, 255, 100) if self.running else (255, 100, 100)
        pygame.draw.circle(self.screen, connection_color, (30, 30), 8)
        
        status_font = pygame.font.Font(None, 20)
        connection_text = status_font.render("● CONECTADO" if self.running else "● DESCONECTADO", 
                                           True, connection_color)
        self.screen.blit(connection_text, (50, 22))
        
        # Modo de renderizado
        mode_text = "Modo: 3D OpenGL" if OPENGL_AVAILABLE else "Modo: 2D Fallback"
        mode_color = (100, 255, 255) if OPENGL_AVAILABLE else (255, 255, 100)
        mode_render = status_font.render(mode_text, True, mode_color)
        self.screen.blit(mode_render, (50, 50))
    
    def _draw_sound_waves(self, center_x, center_y):
        """Dibujar ondas de sonido cuando está hablando"""
        current_time = time.time()
        
        for i in range(3):
            radius = 120 + i * 20 + int(self.speech_level * 30)
            alpha = int(255 * (1 - i * 0.3) * self.speech_level)
            wave_offset = (current_time * 5 + i) % (2 * math.pi)
            wave_radius = radius + math.sin(wave_offset) * 10
            
            # Crear superficie para transparencia
            wave_surface = pygame.Surface((wave_radius * 2, wave_radius * 2))
            wave_surface.set_alpha(alpha)
            wave_surface.fill((0, 0, 0))
            wave_surface.set_colorkey((0, 0, 0))
            
            pygame.draw.circle(wave_surface, (100, 255, 100), 
                             (wave_radius, wave_radius), wave_radius, 3)
            
            self.screen.blit(wave_surface, 
                           (center_x - wave_radius, center_y - wave_radius))
    
    def _draw_listening_circle(self, center_x, center_y):
        """Dibujar círculo pulsante cuando está escuchando"""
        current_time = time.time()
        pulse = math.sin(current_time * 4) * 0.3 + 0.7
        radius = int(130 * pulse)
        
        # Círculo exterior pulsante
        circle_surface = pygame.Surface((radius * 2, radius * 2))
        circle_surface.set_alpha(int(100 * pulse))
        circle_surface.fill((0, 0, 0))
        circle_surface.set_colorkey((0, 0, 0))
        
        pygame.draw.circle(circle_surface, (100, 150, 255), 
                         (radius, radius), radius, 4)
        
        self.screen.blit(circle_surface, 
                       (center_x - radius, center_y - radius))
        
        # Puntos indicadores alrededor
        for i in range(8):
            angle = (current_time * 2 + i * math.pi / 4) % (2 * math.pi)
            dot_x = center_x + math.cos(angle) * (radius + 15)
            dot_y = center_y + math.sin(angle) * (radius + 15)
            dot_alpha = int(255 * (math.sin(current_time * 3 + i) * 0.5 + 0.5))
            
            dot_surface = pygame.Surface((8, 8))
            dot_surface.set_alpha(dot_alpha)
            dot_surface.fill((0, 0, 0))
            dot_surface.set_colorkey((0, 0, 0))
            
            pygame.draw.circle(dot_surface, (100, 150, 255), (4, 4), 4)
            self.screen.blit(dot_surface, (int(dot_x - 4), int(dot_y - 4)))
    
    def _setup_dynamic_lighting(self):
        """Configurar iluminación dinámica para 3D"""
        current_time = time.time()
        
        # Luz principal que se mueve sutilmente
        light_x = math.sin(current_time * 0.5) * 0.5
        light_y = 1.0 + math.cos(current_time * 0.3) * 0.3
        light_z = 1.0
        
        glLightfv(GL_LIGHT0, GL_POSITION, [light_x, light_y, light_z, 0.0])
        
        # Ajustar intensidad según el estado
        if self.is_speaking:
            ambient = [0.3, 0.3, 0.3, 1.0]
            diffuse = [1.0, 0.9, 0.8, 1.0]
        elif self.is_listening:
            ambient = [0.2, 0.2, 0.4, 1.0]
            diffuse = [0.8, 0.8, 1.0, 1.0]
        else:
            ambient = [0.2, 0.2, 0.2, 1.0]
            diffuse = [0.8, 0.8, 0.8, 1.0]
        
        glLightfv(GL_LIGHT0, GL_AMBIENT, ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, diffuse)
    
    def _draw_3d_sound_effects(self):
        """Dibujar efectos de sonido en 3D"""
        current_time = time.time()
        
        # Ondas de sonido alrededor de la cabeza
        for i in range(4):
            glPushMatrix()
            
            # Posición de la onda
            angle = (current_time * 2 + i * math.pi / 2) % (2 * math.pi)
            radius = 1.5 + i * 0.3
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius
            
            glTranslatef(x, 0, z)
            
            # Color y transparencia
            alpha = 1.0 - (i * 0.2)
            intensity = self.speech_level * alpha
            glColor4f(0.2, 1.0, 0.2, intensity)
            
            # Dibujar onda como toro pequeño
            glScalef(0.1, 0.1, 0.1)
            self.draw_sphere_opengl(1.0, 8, 8)
            
            glPopMatrix()
        
        # Partículas de energía
        for i in range(6):
            glPushMatrix()
            
            particle_time = current_time * 3 + i
            x = math.sin(particle_time) * 2.0
            y = math.cos(particle_time * 1.3) * 1.5
            z = math.sin(particle_time * 0.7) * 2.0
            
            glTranslatef(x, y, z)
            glColor4f(1.0, 0.8, 0.2, self.speech_level * 0.8)
            glScalef(0.05, 0.05, 0.05)
            self.draw_sphere_opengl(1.0, 6, 6)
            
            glPopMatrix()
    
    def _draw_3d_listening_effects(self):
        """Dibujar efectos de escucha en 3D"""
        current_time = time.time()
        
        # Anillo pulsante alrededor del avatar
        pulse = math.sin(current_time * 4) * 0.3 + 0.7
        
        for i in range(12):
            glPushMatrix()
            
            angle = (i * math.pi * 2 / 12) + current_time * 0.5
            radius = 2.0 * pulse
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius
            y = math.sin(current_time * 2 + i) * 0.3
            
            glTranslatef(x, y, z)
            glColor4f(0.2, 0.5, 1.0, pulse * 0.6)
            glScalef(0.08, 0.08, 0.08)
            self.draw_sphere_opengl(1.0, 8, 8)
            
            glPopMatrix()
        
        # Ondas concéntricas en el suelo
        for ring in range(3):
            glPushMatrix()
            glTranslatef(0, -1.5, 0)
            glRotatef(90, 1, 0, 0)
            
            ring_radius = 1.0 + ring * 0.5 + (current_time * 2) % 2.0
            alpha = 1.0 - ((current_time * 2) % 2.0) / 2.0
            
            glColor4f(0.3, 0.6, 1.0, alpha * 0.4)
            
            # Dibujar anillo usando líneas
            glBegin(GL_LINE_LOOP)
            for i in range(32):
                angle = i * 2 * math.pi / 32
                x = math.cos(angle) * ring_radius
                y = math.sin(angle) * ring_radius
                glVertex3f(x, y, 0)
            glEnd()
            
            glPopMatrix()
    
    def _draw_3d_particles(self):
        """Dibujar partículas ambientales en 3D"""
        current_time = time.time()
        
        # Partículas flotantes ambientales
        for i in range(8):
            glPushMatrix()
            
            # Movimiento orbital lento
            orbit_time = current_time * 0.2 + i * math.pi / 4
            radius = 3.0 + math.sin(current_time + i) * 0.5
            x = math.cos(orbit_time) * radius
            y = math.sin(current_time * 0.3 + i) * 2.0
            z = math.sin(orbit_time) * radius
            
            glTranslatef(x, y, z)
            
            # Color suave y transparencia
            alpha = (math.sin(current_time * 2 + i) * 0.3 + 0.7) * 0.3
            glColor4f(0.8, 0.9, 1.0, alpha)
            
            glScalef(0.03, 0.03, 0.03)
            self.draw_sphere_opengl(1.0, 6, 6)
            
            glPopMatrix()
     
    def update_animation(self, dt):
        """Actualizar animaciones del avatar"""
        current_time = time.time()
        
        # Animación de parpadeo
        if current_time - self.last_blink > self.blink_interval:
            self.last_blink = current_time
            self.blink_timer = self.blink_duration
        
        if self.blink_timer > 0:
            self.blink_timer -= dt
        
        # Movimiento sutil de cabeza
        self.head_rotation = math.sin(current_time * 0.5) * 0.1
        
        # Animación de habla
        if self.is_speaking:
            self.speech_level = 0.5 + 0.3 * math.sin(current_time * 10)
        else:
            self.speech_level *= 0.9  # Decaimiento gradual
    
    def render_3d(self):
        """Renderizar avatar en 3D mejorado usando OpenGL"""
        # Configurar fondo degradado
        glClearColor(0.1, 0.1, 0.2, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Configurar iluminación dinámica
        self._setup_dynamic_lighting()
        
        # Posicionar cámara con movimiento suave
        glTranslatef(0.0, 0.0, -4.5)
        glRotatef(self.head_rotation * 15, 0, 1, 0)
        glRotatef(math.sin(time.time() * 0.3) * 2, 1, 0, 0)  # Movimiento sutil vertical
        
        # Dibujar cabeza principal con mejor sombreado
        glPushMatrix()
        glColor3f(0.95, 0.85, 0.75)  # Color piel más realista
        self.draw_sphere_opengl(1.0, 30, 30)  # Mayor resolución
        glPopMatrix()
        
        # Dibujar cuello
        glPushMatrix()
        glTranslatef(0, -1.2, 0)
        glColor3f(0.9, 0.8, 0.7)
        glScalef(0.6, 0.4, 0.6)
        self.draw_sphere_opengl(1.0, 20, 20)
        glPopMatrix()
        
        # Dibujar base de ojos (blancos)
        eye_scale = 1.0 if self.blink_timer <= 0 else 0.1
        
        # Ojo izquierdo - blanco
        glPushMatrix()
        glTranslatef(-0.35, 0.25, 0.85)
        glScalef(1.2, eye_scale, 0.8)
        glColor3f(1.0, 1.0, 1.0)  # Blanco
        self.draw_sphere_opengl(0.18, 15, 15)
        glPopMatrix()
        
        # Ojo derecho - blanco
        glPushMatrix()
        glTranslatef(0.35, 0.25, 0.85)
        glScalef(1.2, eye_scale, 0.8)
        glColor3f(1.0, 1.0, 1.0)  # Blanco
        self.draw_sphere_opengl(0.18, 15, 15)
        glPopMatrix()
        
        if self.blink_timer <= 0:
            # Pupilas
            # Pupila izquierda
            glPushMatrix()
            glTranslatef(-0.35, 0.25, 0.95)
            glColor3f(0.1, 0.1, 0.1)  # Negro
            self.draw_sphere_opengl(0.12, 12, 12)
            glPopMatrix()
            
            # Pupila derecha
            glPushMatrix()
            glTranslatef(0.35, 0.25, 0.95)
            glColor3f(0.1, 0.1, 0.1)  # Negro
            self.draw_sphere_opengl(0.12, 12, 12)
            glPopMatrix()
            
            # Brillos en los ojos
            glPushMatrix()
            glTranslatef(-0.32, 0.28, 1.0)
            glColor3f(1.0, 1.0, 1.0)
            self.draw_sphere_opengl(0.04, 8, 8)
            glPopMatrix()
            
            glPushMatrix()
            glTranslatef(0.38, 0.28, 1.0)
            glColor3f(1.0, 1.0, 1.0)
            self.draw_sphere_opengl(0.04, 8, 8)
            glPopMatrix()
        
        # Dibujar cejas
        if self.is_listening:
            # Cejas levantadas
            glPushMatrix()
            glTranslatef(-0.35, 0.45, 0.9)
            glRotatef(15, 0, 0, 1)
            glColor3f(0.4, 0.3, 0.2)  # Marrón
            glScalef(0.3, 0.05, 0.1)
            self.draw_sphere_opengl(1.0, 10, 10)
            glPopMatrix()
            
            glPushMatrix()
            glTranslatef(0.35, 0.45, 0.9)
            glRotatef(-15, 0, 0, 1)
            glColor3f(0.4, 0.3, 0.2)
            glScalef(0.3, 0.05, 0.1)
            self.draw_sphere_opengl(1.0, 10, 10)
            glPopMatrix()
        
        # Dibujar nariz
        glPushMatrix()
        glTranslatef(0, 0.05, 0.95)
        glColor3f(0.9, 0.8, 0.7)
        glScalef(0.15, 0.2, 0.3)
        self.draw_sphere_opengl(1.0, 12, 12)
        glPopMatrix()
        
        # Dibujar boca mejorada
        glPushMatrix()
        glTranslatef(0, -0.25, 0.9)
        
        # Calcular escalado de manera más controlada
        base_scale_x = 0.8  # Escala base para ancho
        base_scale_y = 0.3  # Escala base para alto
        
        if self.is_speaking:
            # Escalado suave y controlado cuando habla
            mouth_scale_x = base_scale_x + (self.speech_level * 0.3)
            mouth_scale_y = base_scale_y + (self.speech_level * 0.4)
            
            glScalef(mouth_scale_x, mouth_scale_y, 0.6)
            glColor3f(0.2, 0.1, 0.1)  # Interior oscuro de la boca
            self.draw_sphere_opengl(0.25, 15, 12)
            
            # Dientes con posición fija
            glPushMatrix()
            glLoadIdentity()  # Resetear transformaciones
            glTranslatef(0, -0.15, 0.9)  # Reposicionar dientes
            glColor3f(1.0, 1.0, 0.95)  # Blanco marfil
            glScalef(0.6, 0.2, 0.3)  # Escala fija para dientes
            self.draw_sphere_opengl(1.0, 10, 8)
            glPopMatrix()
        else:
            # Boca cerrada con escala fija
            glScalef(base_scale_x, base_scale_y, 0.8)
            glColor3f(0.8, 0.3, 0.3)  # Labios cerrados
            self.draw_sphere_opengl(0.2, 12, 10)
        
        glPopMatrix()
        
        # Efectos especiales según el estado
        if self.is_speaking:
            self._draw_3d_sound_effects()
        elif self.is_listening:
            self._draw_3d_listening_effects()
        
        # Partículas ambientales
        self._draw_3d_particles()
    
    def render_2d(self):
        """Renderizar avatar en 2D mejorado con interfaz completa"""
        # Fondo degradado
        self._draw_gradient_background()
        
        center_x = self.width // 2
        center_y = self.height // 2 - 50
        
        # Dibujar sombra de la cabeza
        shadow_offset = 5
        pygame.draw.circle(self.screen, (0, 0, 0, 50), 
                         (center_x + shadow_offset, center_y + shadow_offset), 105)
        
        # Dibujar cabeza con borde
        head_radius = 100
        pygame.draw.circle(self.screen, (200, 200, 200), (center_x, center_y), head_radius + 3)
        self.draw_circle_2d(self.screen, (center_x, center_y), head_radius, self.face_color)
        
        # Dibujar mejillas con rubor si está hablando
        if self.is_speaking:
            cheek_color = (255, 180, 180)
            pygame.draw.circle(self.screen, cheek_color, (center_x - 60, center_y + 10), 15)
            pygame.draw.circle(self.screen, cheek_color, (center_x + 60, center_y + 10), 15)
        
        # Dibujar ojos mejorados
        eye_y = center_y - 20
        eye_height = 25 if self.blink_timer <= 0 else 3
        
        # Ojo izquierdo con brillo
        left_eye_rect = (center_x - 45, eye_y - eye_height//2, 25, eye_height)
        pygame.draw.ellipse(self.screen, (255, 255, 255), left_eye_rect)
        if self.blink_timer <= 0:
            pupil_rect = (center_x - 40, eye_y - 8, 15, 16)
            pygame.draw.ellipse(self.screen, self.eye_color, pupil_rect)
            # Brillo en el ojo
            pygame.draw.circle(self.screen, (255, 255, 255), (center_x - 35, eye_y - 3), 3)
        
        # Ojo derecho con brillo
        right_eye_rect = (center_x + 20, eye_y - eye_height//2, 25, eye_height)
        pygame.draw.ellipse(self.screen, (255, 255, 255), right_eye_rect)
        if self.blink_timer <= 0:
            pupil_rect = (center_x + 25, eye_y - 8, 15, 16)
            pygame.draw.ellipse(self.screen, self.eye_color, pupil_rect)
            # Brillo en el ojo
            pygame.draw.circle(self.screen, (255, 255, 255), (center_x + 35, eye_y - 3), 3)
        
        # Dibujar cejas
        if self.is_listening:
            # Cejas levantadas cuando escucha
            pygame.draw.arc(self.screen, (100, 70, 50), 
                          (center_x - 50, eye_y - 35, 30, 20), 0, 3.14, 3)
            pygame.draw.arc(self.screen, (100, 70, 50), 
                          (center_x + 20, eye_y - 35, 30, 20), 0, 3.14, 3)
        
        # Dibujar boca mejorada
        mouth_width = int(40 + self.speech_level * 30)
        mouth_height = int(15 + self.speech_level * 20)
        mouth_rect = (center_x - mouth_width//2, center_y + 35, mouth_width, mouth_height)
        
        if self.is_speaking:
            # Boca abierta con dientes
            pygame.draw.ellipse(self.screen, (50, 20, 20), mouth_rect)
            teeth_rect = (center_x - mouth_width//3, center_y + 37, mouth_width//1.5, 8)
            pygame.draw.ellipse(self.screen, (255, 255, 255), teeth_rect)
        else:
            # Sonrisa cerrada
            pygame.draw.arc(self.screen, self.mouth_color, mouth_rect, 0, 3.14, 3)
        
        # Panel de información lateral
        self._draw_info_panel()
        
        # Panel de logs (si está abierto)
        if self.logs_panel_open:
            self._draw_logs_panel()
        
        # Indicadores de estado
        self._draw_status_indicators()
        
        # Ondas de sonido si está hablando
        if self.is_speaking:
            self._draw_sound_waves(center_x, center_y)
        
        # Círculo de escucha si está escuchando
        if self.is_listening:
            self._draw_listening_circle(center_x, center_y)
    
    def render(self):
        """Renderizar el avatar"""
        if OPENGL_AVAILABLE:
            self.render_3d()
        else:
            self.render_2d()
    
    def set_speaking(self, speaking: bool, level: float = 0.5):
        """Establecer estado de habla"""
        self.is_speaking = speaking
        if speaking:
            self.speech_level = min(level, 1.0)
        else:
            self.speech_level = 0.0
    
    def set_listening(self, listening: bool):
        """Establecer estado de escucha"""
        self.is_listening = listening
    
    def set_emotion(self, emotion: str):
        """Cambiar emoción del avatar"""
        self.emotion = emotion
        # Aquí se pueden ajustar colores o expresiones según la emoción
    
    def start_speaking(self, audio_level=0.5):
        """Iniciar animación de habla"""
        self.set_speaking(True, audio_level)
    
    def stop_speaking(self):
        """Detener animación de habla"""
        self.set_speaking(False)
    
    def blink(self):
        """Forzar parpadeo"""
        self.blink_timer = self.blink_duration
    
    def start(self):
        """Iniciar el avatar"""
        self.running = True
        self.run()
    
    def run(self):
        """Bucle principal del avatar"""
        while self.running:
            dt = self.clock.tick(60) / 1000.0  # Delta time en segundos
            
            # Manejar eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.blink()
                    elif event.key == pygame.K_s:
                        self.start_speaking(0.8)
                    elif event.key == pygame.K_q:
                        self.stop_speaking()
                    elif event.key == pygame.K_l:
                        self.set_listening(not self.is_listening)
                    elif self.input_active:
                        self._handle_text_input(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mouse_click(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self._handle_mouse_release(event)
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_mouse_motion(event)
            
            # Actualizar animaciones
            self.update_animation(dt)
            
            # Actualizar visualizador de música
            self.update_music_visualizer()
            
            # Renderizar
            self.render()
            pygame.display.flip()
    
    def update_audio_level(self, level: float):
        """Actualizar nivel de audio para animación de habla"""
        if self.is_speaking:
            self.speech_level = min(level, 1.0)
    
    def _handle_text_input(self, event):
        """Manejar entrada de texto para el campo de YouTube"""
        if event.key == pygame.K_RETURN:
            if self.youtube_search_text.strip() and self.app_instance:
                # Buscar en YouTube
                self.app_instance.buscar_youtube(self.youtube_search_text)
            self.input_active = False
        elif event.key == pygame.K_ESCAPE:
            self.input_active = False
        elif event.key == pygame.K_BACKSPACE:
            self.youtube_search_text = self.youtube_search_text[:-1]
        else:
            if len(self.youtube_search_text) < 30:  # Límite de caracteres
                self.youtube_search_text += event.unicode
    
    def _handle_mouse_click(self, event):
        """Manejar clicks del mouse"""
        if event.button == 1:  # Click izquierdo
            # Verificar click en slider
            if self.slider_rect and self.slider_rect.collidepoint(event.pos):
                self.slider_dragging = True
                self._update_slider_value(event.pos[0])
            
            # Verificar click en campo de entrada
            elif self.input_rect and self.input_rect.collidepoint(event.pos):
                self.input_active = True
            else:
                self.input_active = False
            
            # Verificar click en botón de logs
            if self.logs_toggle_rect and self.logs_toggle_rect.collidepoint(event.pos):
                self.logs_panel_open = not self.logs_panel_open
            
            # Verificar clicks en botones
            for button_key, button_rect in self.button_rects.items():
                if button_rect.collidepoint(event.pos):
                    self._handle_button_click(button_key)
    
    def _handle_mouse_release(self, event):
        """Manejar liberación del mouse"""
        if event.button == 1:  # Click izquierdo
            self.slider_dragging = False
    
    def _handle_mouse_motion(self, event):
        """Manejar movimiento del mouse"""
        if self.slider_dragging and self.slider_rect:
            self._update_slider_value(event.pos[0])
    
    def _update_slider_value(self, mouse_x):
        """Actualizar valor del slider basado en posición del mouse"""
        if self.slider_rect:
            relative_x = mouse_x - self.slider_rect.x
            relative_x = max(0, min(relative_x, self.slider_rect.width - 20))
            self.slider_value = (relative_x / (self.slider_rect.width - 20)) * 10000
            
            # Actualizar umbral de energía en la aplicación
            if self.app_instance:
                self.app_instance.energy_threshold = int(self.slider_value)
    
    def _handle_button_click(self, button_key):
        """Manejar clicks en botones"""
        if not self.app_instance:
            return
        
        if button_key == "listen":
            # Iniciar escucha
            self.app_instance.iniciar_escucha_continua()
        elif button_key == "stop":
            # Detener escucha
            self.app_instance.detener_escucha()
        elif button_key == "youtube":
            # Buscar en YouTube con texto actual
            if self.youtube_search_text.strip():
                self.app_instance.buscar_youtube(self.youtube_search_text)
    
    def add_log(self, log_type, message):
        """Añadir un log al panel de logs"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = {
            'timestamp': timestamp,
            'type': log_type,  # 'command', 'response', 'error', 'info'
            'message': message
        }
        self.command_logs.append(log_entry)
        
        # Mantener solo los últimos logs
        if len(self.command_logs) > self.max_logs:
            self.command_logs.pop(0)
    
    def update_music_visualizer(self, audio_data=None):
        """Actualizar el visualizador de música"""
        import random
        import math
        import time
        
        if self.music_playing:
            # Generar animación más realista cuando hay música
            current_time = time.time()
            for i in range(len(self.music_bars)):
                # Crear patrones de frecuencia más realistas
                base_freq = math.sin(current_time * 2 + i * 0.5) * 0.3 + 0.5
                random_variation = random.random() * 0.4
                target = (base_freq + random_variation) * self.music_volume
                target = max(0.1, min(1.0, target))  # Mantener entre 0.1 y 1.0
                
                # Suavizar la transición
                self.music_bars[i] = self.music_bars[i] * 0.6 + target * 0.4
        else:
            # Decaimiento gradual cuando no hay música
            for i in range(len(self.music_bars)):
                self.music_bars[i] *= 0.9
                if self.music_bars[i] < 0.01:
                    self.music_bars[i] = 0.0
    
    def set_music_playing(self, playing, volume=0.5):
        """Establecer el estado de reproducción de música"""
        self.music_playing = playing
        self.music_volume = volume if playing else 0.0
    
    def stop(self):
        """Detener el avatar"""
        self.running = False
        pygame.quit()

# Función para integrar con el asistente principal
def create_avatar_window(width=1200, height=800, app_instance=None):
    """Crear y mostrar ventana del avatar 3D mejorado"""
    try:
        avatar = Avatar3D(width, height, app_instance)
        return avatar
    except Exception as e:
        print(f"Error al crear avatar 3D: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Función principal para pruebas"""
    print("Iniciando Avatar 3D - Alkaris")
    print("Controles:")
    print("  ESPACIO - Parpadear")
    print("  S - Hablar")
    print("  Q - Silencio")
    print("  L - Alternar escucha")
    print("  ESC - Salir")
    
    avatar = create_avatar_window()
    if avatar:
        print("Avatar 3D iniciado exitosamente.")
        if OPENGL_AVAILABLE:
            print("Usando renderizado OpenGL 3D")
        else:
            print("Usando renderizado 2D de respaldo")
        
        try:
            avatar.start()
        except KeyboardInterrupt:
            print("\nInterrumpido por el usuario")
        except Exception as e:
            print(f"Error durante la ejecución: {e}")
            import traceback
            traceback.print_exc()
        finally:
            avatar.stop()
            print("Avatar detenido")
    else:
        print("No se pudo iniciar el avatar 3D")

if __name__ == "__main__":
    main()