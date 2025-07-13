# Avatar 3D - Alkaris

## Descripción

Este módulo implementa un avatar 3D usando OpenGL y ModernGL para proporcionar una representación visual del asistente de voz Alkaris. El avatar incluye animaciones faciales, movimientos de cabeza y respuestas visuales a las interacciones de voz.

## Características

### Renderizado 3D
- **Motor de renderizado**: OpenGL con ModernGL
- **Geometría**: Modelos 3D basados en esferas para cabeza, ojos y boca
- **Shaders**: Vertex y fragment shaders personalizados para iluminación realista
- **Iluminación**: Sistema de iluminación Phong con componentes ambient, diffuse y specular

### Animaciones
- **Habla**: Animación de la boca basada en el nivel de audio
- **Parpadeo**: Parpadeo automático y manual de los ojos
- **Movimiento de cabeza**: Rotación sutil y movimientos naturales
- **Emociones**: Diferentes expresiones faciales (feliz, sorprendido, pensativo, neutral)

### Integración con el Asistente
- **Eventos de voz**: Responde a cuando el asistente habla, escucha o está en silencio
- **Sincronización de audio**: Las animaciones se sincronizan con el audio del asistente
- **Control gestual**: Integración con el sistema de control gestual existente

## Estructura de Archivos

```
modules/avatar/
├── __init__.py                 # Inicialización del módulo
├── avatar_3d.py               # Clase principal del avatar 3D
├── avatar_integration.py      # Sistema de integración con el asistente
└── README_AVATAR.md          # Esta documentación
```

## Dependencias

Para usar el avatar 3D, necesitas instalar las siguientes dependencias:

```bash
pip install moderngl PyOpenGL PyOpenGL_accelerate pygame numpy Pillow
```

### Dependencias Detalladas
- **moderngl**: Motor de renderizado OpenGL moderno
- **PyOpenGL**: Bindings de OpenGL para Python
- **PyOpenGL_accelerate**: Aceleración para PyOpenGL
- **pygame**: Manejo de ventanas y eventos
- **numpy**: Operaciones matemáticas y matrices
- **Pillow**: Procesamiento de imágenes (para texturas futuras)

## Uso

### Uso Básico

```python
from modules.avatar.avatar_3d import create_avatar_window

# Crear y mostrar el avatar
avatar = create_avatar_window()
if avatar:
    # El avatar se ejecuta en su propio hilo
    # Usar avatar.stop() para detenerlo
    pass
```

### Integración con el Asistente

```python
from modules.avatar.avatar_integration import (
    start_3d_avatar, stop_3d_avatar, 
    on_assistant_speaking, on_assistant_silent,
    on_assistant_listening, on_assistant_not_listening,
    update_speech_level, set_avatar_emotion, make_avatar_blink
)

# Iniciar el avatar
start_3d_avatar()

# Notificar eventos
on_assistant_speaking()  # Cuando el asistente habla
on_assistant_silent()    # Cuando el asistente termina de hablar
on_assistant_listening() # Cuando el asistente escucha

# Controlar emociones
set_avatar_emotion("happy")     # Expresión feliz
set_avatar_emotion("surprised") # Expresión sorprendida
set_avatar_emotion("thinking")  # Expresión pensativa
set_avatar_emotion("neutral")   # Expresión neutral

# Controlar animaciones
make_avatar_blink()             # Hacer parpadear
update_speech_level(0.8)        # Actualizar nivel de habla (0.0-1.0)

# Detener el avatar
stop_3d_avatar()
```

## Configuración

### Configuración en app_core.py

El avatar se puede habilitar/deshabilitar en la configuración:

```json
{
    "avatar_3d_enabled": true,
    "asistente_nombre": "Alkaris",
    ...
}
```

### Personalización Visual

Puedes personalizar la apariencia del avatar modificando los parámetros en `avatar_3d.py`:

```python
# Colores
self.program['object_color'].value = (0.9, 0.8, 0.7)  # Color piel
self.program['object_color'].value = (0.1, 0.1, 0.1)  # Color ojos
self.program['object_color'].value = (0.8, 0.2, 0.2)  # Color boca

# Tamaños
head_vertices, head_indices = self.create_sphere(1.0, 30, 30)    # Cabeza
eye_vertices, eye_indices = self.create_sphere(0.15, 15, 15)     # Ojos
mouth_vertices, mouth_indices = self.create_sphere(0.2, 15, 10)  # Boca
```

## Controles de Teclado (Modo de Prueba)

Cuando ejecutas el avatar en modo de prueba:

- **ESPACIO**: Hacer parpadear
- **S**: Iniciar animación de habla
- **Q**: Detener animación de habla
- **ESC**: Salir

## Pruebas

Puedes probar el avatar usando el archivo de prueba:

```bash
python test_avatar.py
```

Esto ejecutará:
1. Verificación de dependencias
2. Prueba básica del avatar
3. Prueba del sistema de integración

## Arquitectura Técnica

### Clase Avatar3D

- **Inicialización**: Configura OpenGL, crea contexto ModernGL, carga shaders
- **Geometría**: Genera mallas 3D para cabeza, ojos y boca
- **Renderizado**: Bucle de renderizado con matrices de transformación
- **Animación**: Sistema de animación basado en tiempo y eventos

### Clase AvatarManager

- **Gestión de hilos**: Ejecuta el avatar en un hilo separado
- **Eventos**: Maneja eventos del asistente de voz
- **Estado**: Mantiene el estado de animaciones y emociones
- **Integración**: Proporciona API simple para el asistente principal

### Sistema de Shaders

- **Vertex Shader**: Transforma vértices y calcula posiciones
- **Fragment Shader**: Implementa modelo de iluminación Phong
- **Uniforms**: Matrices de transformación, posición de luz, colores

## Solución de Problemas

### Error: "No module named 'moderngl'"
```bash
pip install moderngl
```

### Error: "OpenGL context creation failed"
- Verifica que tu sistema soporte OpenGL 3.3+
- Actualiza los drivers de tu tarjeta gráfica
- En sistemas virtuales, asegúrate de que la aceleración 3D esté habilitada

### Error: "Avatar window not responding"
- Verifica que no haya conflictos con otras aplicaciones OpenGL
- Cierra otras aplicaciones que usen aceleración gráfica
- Reinicia la aplicación

### Rendimiento Lento
- Reduce la resolución de las esferas en `create_sphere()`
- Disminuye la frecuencia de actualización (FPS)
- Verifica que estés usando aceleración por hardware

## Desarrollo Futuro

### Características Planeadas
- **Texturas**: Aplicar texturas realistas a la piel
- **Modelos complejos**: Importar modelos 3D más detallados
- **Animaciones avanzadas**: Movimientos labiales más precisos
- **Personalización**: Editor visual de apariencia
- **Efectos**: Partículas y efectos visuales

### Optimizaciones
- **LOD**: Nivel de detalle basado en distancia
- **Culling**: Eliminación de geometría no visible
- **Batching**: Agrupación de llamadas de renderizado
- **Caching**: Cache de geometría y texturas

## Contribuir

Para contribuir al desarrollo del avatar:

1. Familiarízate con OpenGL y ModernGL
2. Revisa el código existente
3. Implementa mejoras o nuevas características
4. Prueba exhaustivamente
5. Documenta los cambios

## Licencia

Este módulo es parte del proyecto Alkaris y sigue la misma licencia del proyecto principal.