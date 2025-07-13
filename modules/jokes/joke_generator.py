import requests

class JokeGenerator:
    def get_joke(self):
        try:
            url = "https://v2.jokeapi.dev/joke/Any?lang=es"
            response = requests.get(url)
            data = response.json()

            if data["type"] == "single":
                texto_del_chiste = data["joke"]
            else:
                texto_del_chiste = f"{data['setup']}\n{data['delivery']}"
            return texto_del_chiste
        except Exception as e:
            print(f"Error al obtener chiste: {e}")
            return "Lo siento, no pude pensar en un chiste ahora mismo."