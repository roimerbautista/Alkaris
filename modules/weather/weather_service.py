import requests
import re

class WeatherService:
    def __init__(self, weathermap_api_key):
        self.weathermap_api_key = weathermap_api_key

    def extraer_ciudad_aspecto(self, comando_pronunciado):
        pattern = re.compile(r"(clima|tiempo|condiciones)\s+(para|en|de)?\s*([a-zA-Z\s]+)?\s*(sobre\s+)?([a-z\s]+)?", re.IGNORECASE)
        match = pattern.search(comando_pronunciado)

        if not match:
            return None, None

        ciudad = match.group(3).strip() if match.group(3) else None
        aspecto = match.group(5).strip() if match.group(5) else "resumen"
        return ciudad, aspecto

    def obtener_clima_de(self, ciudad, aspecto, responder_con_audio_callback):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={ciudad}&appid={self.weathermap_api_key}&units=metric&lang=es"
        try:
            respuesta = requests.get(url)
            datos = respuesta.json()
            if respuesta.status_code == 200:
                mensaje_clima = self._construir_mensaje_clima(datos, aspecto, ciudad)
                return mensaje_clima
            else:
                return "No se pudo obtener el clima para esa ciudad."
        except Exception as e:
            return f"Ocurrió un error al obtener el clima: {e}"

    def _construir_mensaje_clima(self, datos, aspecto, ciudad):
        aspectos = {
            "temperatura": f"La temperatura es de {datos['main']['temp']}°C.",
            "viento": f"La velocidad del viento es de {datos['wind']['speed']} m/s.",
            "humedad": f"La humedad es del {datos['main']['humidity']}%.",
            "presión": f"La presión atmosférica es de {datos['main']['pressure']} hPa.",
            "nubes": f"Nubosidad del {datos['clouds']['all']}%.",
            "descripción": datos['weather'][0]['description'],
            "resumen": (f"Clima en {ciudad}: {datos['weather'][0]['description']}, "
                        f"Temperatura: {datos['main']['temp']}°C, "
                        f"Presión: {datos['main']['pressure']} hPa, "
                        f"Humedad: {datos['main']['humidity']}%, "
                        f"Viento: {datos['wind']['speed']} m/s, "
                        f"Nubosidad: {datos['clouds']['all']}%.")
        }
        return aspectos.get(aspecto, "Aspecto del clima no reconocido o no disponible.")