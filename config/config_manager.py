import json
import os

class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file

    def load_config(self):
        if not os.path.exists(self.config_file):
            return {}  # Retorna config por defecto si no existe el archivo
        try:
            with open(self.config_file, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            print("Archivo de configuración no encontrado. Usando configuración por defecto.")
            return {}
        except Exception as e:
            print(f"Error al cargar la configuración: {e}")
            return {}

    def save_config(self, config_data):
        try:
            with open(self.config_file, "w") as file:
                json.dump(config_data, file)
        except Exception as e:
            print(f"Error al guardar la configuración: {e}")