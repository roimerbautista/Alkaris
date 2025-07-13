from core.app_core import SpotifyVoiceControl
import time

if __name__ == "__main__":
    app = SpotifyVoiceControl()
    
    # Mantener la aplicación corriendo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCerrando aplicación...")
        app.on_closing()