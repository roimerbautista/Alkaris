import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import requests
from spotipy.exceptions import SpotifyException

class SpotifyController:
    def __init__(self, client_id, client_secret, audio_manager):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sp = None
        self.volumen_original = None
        self.audio_manager = audio_manager

    def autenticar_spotify(self, premium_check_callback, devices_callback):
        print("Autenticando con Spotify...")
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri="http://localhost:8888/callback",
                scope="user-read-playback-state user-modify-playback-state user-read-currently-playing user-library-read user-library-modify playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-follow-read user-follow-modify user-read-private user-read-email user-top-read user-read-recently-played user-modify-playback-state",
                cache_path=".cache"
            ), requests_timeout=30, retries=3)
            if premium_check_callback():
                self.audio_manager.responder_con_audio("¡Bienvenido! Tu cuenta es Premium.")
            else:
                self.audio_manager.responder_con_audio("¡Bienvenido! Tu cuenta es gratuita.")
            devices_callback()
        except spotipy.SpotifyException as e:
            self.audio_manager.responder_con_audio("Ocurrió un error al autenticar con Spotify.")
            print(f"Error al autenticar con Spotify: {e}")

    def reautenticar_spotify(self, premium_check_callback, responder_con_audio_callback):
        print("Reautenticando con Spotify...")
        try:
            cache_path = ".cache"
            if os.path.exists(cache_path):
                os.remove(cache_path)
                print(f"Archivo de caché {cache_path} eliminado correctamente.")

            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri="http://localhost:8888/callback",
                scope="user-read-playback-state user-modify-playback-state user-read-currently-playing user-library-read user-library-modify playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-follow-read user-follow-modify user-read-private user-read-email user-top-read user-read-recently-played user-modify-playback-state",
                cache_path=cache_path
            ), requests_timeout=3600, retries=3)

            if premium_check_callback():
                responder_con_audio_callback("Tu cuenta ha sido validada como Premium.")
            else:
                responder_con_audio_callback("Tu cuenta ha sido validada como gratuita.")
        except Exception as e:
            print(f"Error al reautenticar con Spotify: {e}")
            responder_con_audio_callback("Ocurrió un error al reautenticar tu cuenta de Spotify.")


    def precalentar_spotify(self):
        try:
            self.sp.current_user()
            print("Conexión con Spotify precalentada y activa.")
        except (spotipy.SpotifyException, requests.exceptions.RequestException) as e:
            print(f"Error al precalentar la conexión con Spotify: {e}")

    def ajustar_volumen_para_escuchar(self):
        try:
            playback_info = self.sp.current_playback()
            if playback_info and playback_info['device']:
                volumen_actual = playback_info['device']['volume_percent']
                self.volumen_original = volumen_actual
                nuevo_volumen = 5
                self.sp.volume(nuevo_volumen)
                print(f"Volumen ajustado a {nuevo_volumen} para escuchar comando.")
            else:
                print("No hay dispositivos activos o Spotify no está reproduciendo.")
        except Exception as e:
            print(f"Error al ajustar el volumen para escuchar: {e}")

    def restaurar_volumen_original(self):
        try:
            if self.volumen_original is not None:
                self.sp.volume(self.volumen_original)
                print(f"Volumen restaurado a {self.volumen_original}.")
            else:
                print("No se había ajustado el volumen anteriormente.")
        except Exception as e:
            print(f"Error al restaurar el volumen original: {e}")

    def verificar_estado_reproduccion(self, playing=False):
        try:
            current_playback = self.sp.current_playback()
            if current_playback is not None:
                if playing:
                    return current_playback['is_playing']
                else:
                    return not current_playback['is_playing']
            else:
                return False
        except Exception as e:
            print(f"Error al verificar el estado de reproducción: {e}")
            return False

    def obtener_device_id_activo(self):
        try:
            dispositivos = self.sp.devices()
            for dispositivo in dispositivos['devices']:
                if dispositivo['is_active']:
                    return dispositivo['id']
            return None
        except spotipy.SpotifyException as e:
            print(f"Error al obtener los dispositivos activos: {e}")
            return None

    def obtener_dispositivos(self): # Nueva función para obtener la lista de dispositivos
        try:
            return self.sp.devices()
        except spotipy.SpotifyException as e:
            print(f"Error al obtener dispositivos: {e}")
            return {'devices': []} # Return empty list in case of error


    def elegir_dispositivo(self, responder_con_audio_callback):
        dispositivos = self.sp.devices()
        print("Dispositivos disponibles:")
        for i, dispositivo in enumerate(dispositivos['devices']):
            print(f"{i + 1}. {dispositivo['name']} - {'Activo' if dispositivo['is_active'] else 'No Activo'}")
        print("Por favor, elige el dispositivo donde deseas reproducir.")
        responder_con_audio_callback("Por favor, elige el dispositivo donde deseas reproducir.")
        try:
            dispositivo_elegido = int(input("Ingresa el número correspondiente al dispositivo: "))
            if 1 <= dispositivo_elegido <= len(dispositivos['devices']):
                device_id = dispositivos['devices'][dispositivo_elegido - 1]['id']
                self.sp.transfer_playback(device_id=device_id, force_play=True)
                responder_con_audio_callback("Reproducción iniciada en el dispositivo elegido.")
            else:
                print("Número de dispositivo inválido.")
                responder_con_audio_callback("Número de dispositivo inválido.")
        except ValueError:
            print("Por favor, ingresa un número válido.")
            responder_con_audio_callback("Por favor, ingresa un número válido.")

    def elegir_y_forzar_dispositivo(self, responder_con_audio_callback):
        dispositivos = self.sp.devices()
        print("Dispositivos disponibles:")
        for i, dispositivo in enumerate(dispositivos['devices']):
            print(f"{i + 1}. {dispositivo['name']} - {'Activo' if dispositivo['is_active'] else 'No Activo'}")
        print("Por favor, elige el dispositivo donde deseas forzar la reproducción.")
        responder_con_audio_callback("Por favor, elige el dispositivo donde deseas forzar la reproducción.")
        try:
            dispositivo_elegido = int(input("Ingresa el número correspondiente al dispositivo: "))
            if 1 <= dispositivo_elegido <= len(dispositivos['devices']):
                device_id = dispositivos['devices'][dispositivo_elegido - 1]['id']
                self.sp.transfer_playback(device_id=device_id, force_play=True)
                responder_con_audio_callback("Reproducción forzada en el dispositivo elegido.")
            else:
                print("Número de dispositivo inválido.")
                responder_con_audio_callback("Número de dispositivo inválido.")
        except ValueError:
            print("Por favor, ingresa un número válido.")
            responder_con_audio_callback("Por favor, ingresa un número válido.")

    

    def mostrar_dispositivos_disponibles(self):
        try:
            dispositivos = self.sp.devices()
            print("Dispositivos disponibles:")
            for dispositivo in dispositivos['devices']:
                print(f"ID: {dispositivo['id']}, Nombre: {dispositivo['name']}, Tipo: {dispositivo['type']}, Activo: {dispositivo['is_active']}")
        except spotipy.SpotifyException as e:
            print(f"Error al obtener los dispositivos disponibles: {e}")

    def verificar_cuenta_premium(self):
        try:
            cuenta = self.sp.me()
            return cuenta.get("product") == "premium"
        except spotipy.SpotifyException as e:
            print(f"Error al verificar la cuenta premium: {e}")
            return False

    def pausar_spotify_si_es_necesario(self, responder_con_audio_callback):
        if self.verificar_estado_reproduccion(playing=True):
            self.pause_playback()
            responder_con_audio_callback("Reproducción de Spotify pausada.")
            return True
        return False

    def pause_playback(self):
        self.sp.pause_playback()

    def next_track(self):
        self.sp.next_track()

    def previous_track(self):
        self.sp.previous_track()

    def start_playback(self, device_id=None):
        self.sp.start_playback(device_id=device_id)

    def agregar_cancion_a_favoritos(self, responder_con_audio_callback):
        try:
            track = self.sp.current_playback()
            if track and track['item']:
                track_id = track['item']['id']
                self.sp.current_user_saved_tracks_add(tracks=[track_id])
                responder_con_audio_callback("Canción agregada a tus favoritos.")
            else:
                responder_con_audio_callback("No hay una canción reproducida actualmente.")
        except spotipy.SpotifyException as e:
            print(f"Error al agregar la canción a favoritos: {e}")
            responder_con_audio_callback("Ocurrió un error al intentar agregar la canción a favoritos.")

    def reproducir_canciones_favoritas(self, responder_con_audio_callback):
        try:
            resultados = self.sp.current_user_saved_tracks(limit=50)
            tracks = resultados['items']
            if not tracks:
                responder_con_audio_callback("No tienes canciones guardadas en tus favoritos.")
                return

            track_uris = [track['track']['uri'] for track in tracks if 'track' in track]
            dispositivos = self.sp.devices()
            device_id = next((device['id'] for device in dispositivos['devices'] if device['is_active']), None)

            if device_id:
                self.sp.start_playback(device_id=device_id, uris=track_uris)
                responder_con_audio_callback("Reproduciendo tus canciones favoritas.")
            else:
                responder_con_audio_callback("No hay dispositivos activos disponibles para reproducir.")
        except spotipy.SpotifyException as e:
            responder_con_audio_callback(f"Ocurrió un error al intentar reproducir tus canciones favoritas: {str(e)}")

    def obtener_nombre_cancion_actual(self, responder_con_audio_callback):
        try:
            reproduccion_actual = self.sp.current_playback()
            if reproduccion_actual and reproduccion_actual.get('item'):
                nombre_cancion = reproduccion_actual['item']['name']
                nombre_artista = reproduccion_actual['item']['artists'][0]['name']
                responder_con_audio_callback(f"Estás escuchando {nombre_cancion} de {nombre_artista}.")
            else:
                responder_con_audio_callback("Actualmente no hay ninguna canción reproduciéndose.")
        except Exception as e:
            print(f"Error al obtener la canción actual: {e}")
            responder_con_audio_callback("Ocurrió un error al intentar obtener el nombre de la canción actual.")

    def mostrar_playlists_disponibles(self, limit, offset, responder_con_audio_callback):
        try:
            playlists = self.sp.current_user_playlists(limit=limit, offset=offset)
            print("Playlists disponibles:")
            for i, playlist in enumerate(playlists['items'], start=offset + 1):
                print(f"{i}. {playlist['name']}")
            responder_con_audio_callback("Estas son tus playlists disponibles.")
        except spotipy.SpotifyException as e:
            print(f"Error al obtener las playlists disponibles: {e}")

    def reproducir_primera_cancion_playlist(self, playlist_uri, responder_con_audio_callback):
        try:
            tracks = self.sp.playlist_tracks(playlist_uri)
            if tracks['items']:
                track_uri = tracks['items'][0]['track']['uri']
                dispositivos = self.sp.devices()
                if dispositivos['devices']:
                    device_id = dispositivos['devices'][0]['id']
                    self.sp.start_playback(device_id=device_id, uris=[track_uri])
                else:
                    responder_con_audio_callback("No se encontraron dispositivos disponibles para reproducir la playlist.")
            else:
                responder_con_audio_callback("La playlist está vacía.")
        except spotipy.SpotifyException as e:
            print(f"Error al reproducir la primera canción de la playlist: {e}")
            responder_con_audio_callback("Ocurrió un error al reproducir la primera canción de la playlist.")

    def reproducir_playlist_por_numero(self, numero_playlist, responder_con_audio_callback):
        try:
            playlists = self.sp.current_user_playlists()
            if 1 <= numero_playlist <= len(playlists['items']):
                playlist_uri = playlists['items'][numero_playlist - 1]['uri']
                self.reproducir_primera_cancion_playlist(playlist_uri, responder_con_audio_callback)
                playlist_nombre = playlists['items'][numero_playlist - 1]['name']
                responder_con_audio_callback(f"Reproduciendo la playlist {playlist_nombre}.")
            else:
                responder_con_audio_callback("Número de playlist inválido.")
        except spotipy.SpotifyException as e:
            print(f"Error al reproducir la playlist: {e}")
            responder_con_audio_callback("Ocurrió un error al reproducir la playlist. Por favor, inténtalo nuevamente.")

    def subir_volumen(self, responder_con_audio_callback):
        try:
            volumen_actual = self.sp.current_playback()['device']['volume_percent']
            nuevo_volumen = min(volumen_actual + 5, 100)
            self.sp.volume(nuevo_volumen)
            responder_con_audio_callback(f"Volumen subido a {nuevo_volumen} por ciento.")
        except Exception as e:
            print(f"Error al subir el volumen: {e}")
            responder_con_audio_callback("Ocurrió un error al subir el volumen.")

    def bajar_volumen(self, responder_con_audio_callback):
        try:
            volumen_actual = self.sp.current_playback()['device']['volume_percent']
            nuevo_volumen = max(volumen_actual - 5, 0)
            self.sp.volume(nuevo_volumen)
            responder_con_audio_callback(f"Volumen bajado a {nuevo_volumen} por ciento.")
        except Exception as e:
            print(f"Error al bajar el volumen: {e}")
            responder_con_audio_callback("Ocurrió un error al bajar el volumen.")

    def ajustar_volumen(self, volumen, responder_con_audio_callback):
        try:
            nuevo_volumen = max(min(volumen, 100), 0)
            self.sp.volume(nuevo_volumen)
            responder_con_audio_callback(f"Volumen ajustado a {nuevo_volumen} por ciento.")
        except Exception as e:
            print(f"Error al ajustar el volumen: {e}")
            responder_con_audio_callback("Ocurrió un error al ajustar el volumen.")

    def buscar_y_reproducir_cancion(self, cancion, responder_con_audio_callback=None):
        # Asegurarse de que tenemos una función de callback válida
        if responder_con_audio_callback is None:
            responder_con_audio_callback = self.audio_manager.responder_con_audio
            
        if not cancion.strip():
            responder_con_audio_callback("La consulta de búsqueda está vacía.")
            return
        dispositivos = self.sp.devices()
        if len(dispositivos['devices']) == 1:
            device_id = dispositivos['devices'][0]['id']
            try:
                results = self.sp.search(q=cancion, type="track", limit=1)
                if results["tracks"]["items"]:
                    track_uri = results["tracks"]["items"][0]["uri"]
                    self.sp.start_playback(device_id=device_id, uris=[track_uri])
                    nombre_cancion = results["tracks"]["items"][0]["name"]
                    responder_con_audio_callback(f"Reproduciendo {nombre_cancion}")
                else:
                    responder_con_audio_callback("No se encontraron resultados para tu búsqueda.")
            except spotipy.SpotifyException as e:
                responder_con_audio_callback("Ocurrió un error al buscar la canción.")
                print(f"Error al buscar la canción {cancion}: {e}")
        elif len(dispositivos['devices']) > 1:
            device_id = self.obtener_device_id_activo()
            if not device_id:
                responder_con_audio_callback("No se encontró un dispositivo activo.")
                return
            try:
                results = self.sp.search(q=cancion, type="track", limit=1)
                if results["tracks"]["items"]:
                    track_uri = results["tracks"]["items"][0]["uri"]
                    self.sp.start_playback(device_id=device_id, uris=[track_uri])
                    nombre_cancion = results["tracks"]["items"][0]["name"]
                    responder_con_audio_callback(f"Reproduciendo {nombre_cancion}")
                else:
                    responder_con_audio_callback("No se encontraron resultados para tu búsqueda.")
            except spotipy.SpotifyException as e:
                responder_con_audio_callback("Ocurrió un error al buscar la canción.")
                print(f"Error al buscar la canción {cancion}: {e}")
        else:
            responder_con_audio_callback("No se encontraron dispositivos disponibles para reproducir.")

    # Los métodos intermedios se mantienen iguales...

    def eliminar_de_favoritos(self, nombre_cancion=None, responder_con_audio_callback=None):
        # Asegurarse de que tenemos una función de callback válida
        if responder_con_audio_callback is None:
            responder_con_audio_callback = self.audio_manager.responder_con_audio
            
        try:
            # If no song name provided, remove currently playing track from favorites
            if not nombre_cancion:
                cancion_actual = self.sp.current_playback()
                if cancion_actual and cancion_actual.get('item'):
                    id_cancion = cancion_actual['item']['id']
                    nombre_cancion_favorita = cancion_actual['item']['name']
                    self.sp.current_user_saved_tracks_delete([id_cancion])
                    
                    responder_con_audio_callback(f"Canción {nombre_cancion_favorita} eliminada de favoritos.")
                else:
                    responder_con_audio_callback("No hay ninguna canción reproduciéndose actualmente.")
            else:
                # Search for the song and remove the first result from favorites
                resultados = self.sp.search(q=nombre_cancion, type="track", limit=1)
                if resultados['tracks']['items']:
                    id_cancion = resultados['tracks']['items'][0]['id']
                    nombre_cancion_favorita = resultados['tracks']['items'][0]['name']
                    self.sp.current_user_saved_tracks_delete([id_cancion])
                    
                    responder_con_audio_callback(f"Canción {nombre_cancion_favorita} eliminada de favoritos.")
                else:
                    print(f"No results found for song: {nombre_cancion}")
                    responder_con_audio_callback("No se encontraron resultados para tu búsqueda.")
        except Exception as e:
            print(f"Error al eliminar de favoritos: {e}")
            responder_con_audio_callback("Ocurrió un error al eliminar la canción de favoritos.")

    def activar_desactivar_aleatorio(self, estado=True, responder_con_audio_callback=None):
        # Asegurarse de que tenemos una función de callback válida
        if responder_con_audio_callback is None:
            responder_con_audio_callback = self.audio_manager.responder_con_audio
            
        try:
            self.sp.shuffle(estado)
            if estado:
                responder_con_audio_callback("Modo aleatorio activado.")
            else:
                responder_con_audio_callback("Modo aleatorio desactivado.")
        except Exception as e:
            print(f"Error al configurar modo aleatorio: {e}")
            responder_con_audio_callback("Ocurrió un error al configurar el modo aleatorio.")

    def modo_repeticion(self, modo='off', responder_con_audio_callback=None):
        # Asegurarse de que tenemos una función de callback válida
        if responder_con_audio_callback is None:
            responder_con_audio_callback = self.audio_manager.responder_con_audio
            
        try:
            # Valid modes: 'track', 'context', 'off'
            self.sp.repeat(modo)
            if modo == 'track':
                responder_con_audio_callback("Modo de repetición: repetir canción actual.")
            elif modo == 'context':
                responder_con_audio_callback("Modo de repetición: repetir lista o álbum.")
            else:
                responder_con_audio_callback("Modo de repetición desactivado.")
        except Exception as e:
            print(f"Error al configurar modo de repetición: {e}")
            responder_con_audio_callback("Ocurrió un error al configurar el modo de repetición.")

    def reproducir_album(self, album_nombre=None):
        try:
            if not album_nombre and hasattr(self, 'last_command'):
                # Try to extract album name from last command
                comando = self.last_command
                if "reproducir álbum" in comando or "reproducir album" in comando:
                    album_nombre = comando.replace("reproducir álbum", "", 1).replace("reproducir album", "", 1).strip()
            
            if not album_nombre:
                self.audio_manager.responder_con_audio("Por favor, especifica qué álbum quieres reproducir.")
                return
                
            # Search for the album
            results = self.sp.search(q=f"album:{album_nombre}", type="album", limit=1)
            
            if not results['albums']['items']:
                self.audio_manager.responder_con_audio(f"No encontré ningún álbum con el nombre {album_nombre}.")
                return
                
            album_id = results['albums']['items'][0]['id']
            album_uri = f"spotify:album:{album_id}"
            
            # Get active device
            device_id = self.obtener_device_id_activo()
            if not device_id:
                self.audio_manager.responder_con_audio("No se encontró un dispositivo activo para reproducir.")
                return
                
            # Play the album
            self.sp.start_playback(device_id=device_id, context_uri=album_uri)
            album_name = results['albums']['items'][0]['name']
            artist_name = results['albums']['items'][0]['artists'][0]['name']
            self.audio_manager.responder_con_audio(f"Reproduciendo el álbum {album_name} de {artist_name}.")
            
        except Exception as e:
            print(f"Error al reproducir álbum: {e}")
            self.audio_manager.responder_con_audio("Ocurrió un error al intentar reproducir el álbum.")

    def cambiar_aleatorio(self, responder_con_audio_callback=None):
        # Asegurarse de que tenemos una función de callback válida
        if responder_con_audio_callback is None:
            responder_con_audio_callback = self.audio_manager.responder_con_audio
            
        try:
            # Get current playback to check shuffle state
            reproduccion_actual = self.sp.current_playback()
            if reproduccion_actual:
                aleatorio_actual = reproduccion_actual.get('shuffle_state', False)
                # Toggle to opposite state
                self.activar_desactivar_aleatorio(not aleatorio_actual, responder_con_audio_callback)
            else:
                # Default to enabling shuffle if no playback info
                self.activar_desactivar_aleatorio(True, responder_con_audio_callback)
        except Exception as e:
            print(f"Error toggling shuffle: {e}")
            responder_con_audio_callback("Ocurrió un error al cambiar el modo aleatorio.")

    def cambiar_repeticion(self, responder_con_audio_callback=None):
        # Asegurarse de que tenemos una función de callback válida
        if responder_con_audio_callback is None:
            responder_con_audio_callback = self.audio_manager.responder_con_audio
            
        try:
            # Get current playback to check repeat state
            reproduccion_actual = self.sp.current_playback()
            if reproduccion_actual:
                repeticion_actual = reproduccion_actual.get('repeat_state', 'off')
                # Cycle through repeat modes: off -> context -> track -> off
                if repeticion_actual == 'off':
                    self.modo_repeticion('context', responder_con_audio_callback)
                elif repeticion_actual == 'context':
                    self.modo_repeticion('track', responder_con_audio_callback)
                else:  # track
                    self.modo_repeticion('off', responder_con_audio_callback)
            else:
                # Default to context repeat if no playback info
                self.modo_repeticion('context', responder_con_audio_callback)
        except Exception as e:
            print(f"Error toggling repeat mode: {e}")
            responder_con_audio_callback("Ocurrió un error al cambiar el modo de repetición.")

    def obtener_recomendaciones(self, tipo_semilla='track', limite=5, responder_con_audio_callback=None):
        # Asegurarse de que tenemos una función de callback válida
        if responder_con_audio_callback is None:
            responder_con_audio_callback = self.audio_manager.responder_con_audio
            
        try:
            elementos_semilla = []
            nombre_semilla = ""

            # Si no hay reproducción actual, intentar con géneros populares como alternativa
            cancion_actual = self.sp.current_playback()
            if not cancion_actual or not cancion_actual.get('item'):
                # Plan B: Usar géneros disponibles como semilla si no hay canción actual
                try:
                    seed_genres = ["pop", "rock", "electronic"]  # Géneros populares como fallback
                    recomendaciones = self.sp.recommendations(seed_genres=seed_genres, limit=limite)
                    responder_con_audio_callback("Reproduciendo recomendaciones basadas en géneros populares.")
                    
                    if recomendaciones and recomendaciones['tracks']:
                        uris_canciones = [cancion['uri'] for cancion in recomendaciones['tracks']]
                        id_dispositivo = self.obtener_device_id_activo()
                        if id_dispositivo:
                            self.sp.start_playback(device_id=id_dispositivo, uris=uris_canciones)
                        else:
                            self.sp.start_playback(uris=uris_canciones)
                        return
                    else:
                        # Si incluso esto falla, pasar al siguiente método
                        pass
                except Exception as e:
                    print(f"Error con recomendaciones basadas en géneros: {e}")
                    # Continuar con el flujo normal

            # Proceso normal basado en tipo de semilla
            if tipo_semilla == 'track':
                if cancion_actual and cancion_actual.get('item'):
                    elementos_semilla = [cancion_actual['item']['id']]
                    nombre_semilla = cancion_actual['item']['name']
                else:
                    try:
                        mejores_canciones = self.sp.current_user_top_tracks(limit=5, time_range='short_term')
                        if mejores_canciones['items']:
                            # Intentar con varias canciones top en caso de que alguna falle
                            for i in range(min(5, len(mejores_canciones['items']))):
                                top_track = mejores_canciones['items'][i]
                                if top_track and top_track.get('id'):
                                    elementos_semilla = [top_track['id']]
                                    nombre_semilla = top_track['name']
                                    # Verificar si este ID es válido haciendo una petición de prueba
                                    try:
                                        self.sp.track(top_track['id'])
                                        break  # Si la canción existe, usar esta
                                    except:
                                        continue  # Si falla, intentar con la siguiente
                        
                        if not elementos_semilla:
                            # Como último recurso, obtener las playlists del usuario y extraer una canción
                            playlists = self.sp.current_user_playlists(limit=1)
                            if playlists['items']:
                                playlist = playlists['items'][0]
                                tracks = self.sp.playlist_tracks(playlist['id'], limit=1)
                                if tracks['items']:
                                    track = tracks['items'][0]['track']
                                    elementos_semilla = [track['id']]
                                    nombre_semilla = track['name']
                    except Exception as e:
                        print(f"Error obteniendo canciones populares del usuario: {e}")
                
                # Verificar si tenemos semillas válidas
                if not elementos_semilla:
                    responder_con_audio_callback("No se pudo identificar una canción para generar recomendaciones.")
                    return
                    
                # Verificar explícitamente que el ID de la canción sea válido
                try:
                    self.sp.track(elementos_semilla[0])
                except:
                    responder_con_audio_callback("La canción seleccionada no está disponible para generar recomendaciones.")
                    return
                    
                recomendaciones = self.sp.recommendations(seed_tracks=elementos_semilla, limit=limite)

            elif tipo_semilla == 'artist':
                if cancion_actual and cancion_actual.get('item') and cancion_actual['item'].get('artists') and len(cancion_actual['item']['artists']) > 0:
                    elementos_semilla = [cancion_actual['item']['artists'][0]['id']]
                    nombre_semilla = cancion_actual['item']['artists'][0]['name']
                else:
                    try:
                        mejores_artistas = self.sp.current_user_top_artists(limit=5, time_range='medium_term')
                        if mejores_artistas['items']:
                            # Intentar con varios artistas top en caso de que alguno falle
                            for i in range(min(5, len(mejores_artistas['items']))):
                                top_artist = mejores_artistas['items'][i]
                                if top_artist and top_artist.get('id'):
                                    elementos_semilla = [top_artist['id']]
                                    nombre_semilla = top_artist['name']
                                    # Verificar si este ID es válido
                                    try:
                                        self.sp.artist(top_artist['id'])
                                        break  # Si el artista existe, usar este
                                    except:
                                        continue  # Si falla, intentar con el siguiente
                    except Exception as e:
                        print(f"Error obteniendo artistas populares del usuario: {e}")
                
                # Verificar si tenemos semillas válidas
                if not elementos_semilla:
                    responder_con_audio_callback("No se pudo identificar un artista para generar recomendaciones.")
                    return
                    
                # Verificar explícitamente que el ID del artista sea válido
                try:
                    self.sp.artist(elementos_semilla[0])
                except:
                    responder_con_audio_callback("El artista seleccionado no está disponible para generar recomendaciones.")
                    return
                    
                recomendaciones = self.sp.recommendations(seed_artists=elementos_semilla, limit=limite)
                
            else:  # Tipo de semilla no reconocido
                # Usar géneros como fallback
                seed_genres = ["pop", "rock", "electronic"]
                recomendaciones = self.sp.recommendations(seed_genres=seed_genres, limit=limite)
                nombre_semilla = "géneros populares"

            # Procesar las recomendaciones
            if recomendaciones and recomendaciones.get('tracks') and len(recomendaciones['tracks']) > 0:
                uris_canciones = [cancion['uri'] for cancion in recomendaciones['tracks']]
                
                # Verificar que tenemos URIs válidos
                if not uris_canciones:
                    responder_con_audio_callback("No se pudieron generar recomendaciones con la información disponible.")
                    return
                    
                # Intentar reproducir
                try:
                    id_dispositivo = self.obtener_device_id_activo()
                    if id_dispositivo:
                        self.sp.start_playback(device_id=id_dispositivo, uris=uris_canciones)
                    else:
                        self.sp.start_playback(uris=uris_canciones)

                    print(f"Playing recommendations based on {tipo_semilla}: {nombre_semilla}")
                    responder_con_audio_callback(f"Reproduciendo recomendaciones basadas en {nombre_semilla}.")
                except SpotifyException as e:
                    if "NO_ACTIVE_DEVICE" in str(e):
                        responder_con_audio_callback("No hay dispositivos activos. Por favor, abre Spotify en algún dispositivo.")
                    elif "PREMIUM_REQUIRED" in str(e):
                        responder_con_audio_callback("Se requiere una cuenta Premium para esta función.")
                    else:
                        responder_con_audio_callback("Error al reproducir las recomendaciones.")
                    print(f"Error al reproducir: {e}")
            else:
                print("No recommendations found")
                responder_con_audio_callback("No se pudieron generar recomendaciones. Intenta con otro tipo de semilla.")
                
        except SpotifyException as e:
            error_msg = str(e)
            print(f"Spotify API error while getting recommendations: {error_msg}")
            
            if "404" in error_msg:
                responder_con_audio_callback("No se encontró la canción o artista para generar recomendaciones.")
            elif "401" in error_msg or "403" in error_msg:
                responder_con_audio_callback("Error de autenticación. Por favor, inicia sesión nuevamente.")
            elif "429" in error_msg:
                responder_con_audio_callback("Se han realizado demasiadas solicitudes. Intenta más tarde.")
            else:
                responder_con_audio_callback("Ocurrió un error al obtener recomendaciones de Spotify.")
                
        except Exception as e:
            print(f"Unexpected error while getting recommendations: {e}")
            responder_con_audio_callback("Ocurrió un error inesperado al obtener recomendaciones.")