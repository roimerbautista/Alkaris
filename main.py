from core.app_core import SpotifyVoiceControl
import time

if __name__ == "__main__":
    app = SpotifyVoiceControl()
    
    # Iniciar la escucha continua
    app.iniciar_escucha_continua()
    
    # Mantener la aplicación corriendo
    try:
        while app.escuchando:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCerrando aplicación...")
        app.detener_escucha()
        app.on_closing()
    
    print("Aplicación cerrada correctamente.")