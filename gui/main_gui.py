import tkinter as tk

class MainGUI:
    def __init__(self, app_instance):
        self.root = tk.Tk()
        self.app_instance = app_instance # Referencia a la instancia principal de SpotifyVoiceControl
        self.root.title("Control de Voz para Spotify")

        # Inicializar variables que serán elementos de la GUI
        self.energy_threshold_slider = None
        self.label_nombre_asistente = None
        self.entry_cancion = None
        self.canvas = None
        self.estado_circulo = None

    def init_ui(self):
        """Inicializa los elementos de la interfaz de usuario."""
        ancho_ventana = 150
        alto_ventana = 280
        pos_x = 0
        pos_y = 0
        self.root.geometry(f'{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}')
        self.root.attributes('-topmost', True)

        self.label_nombre_asistente = tk.Label(self.root, text=f"Asistente: {self.app_instance.asistente_nombre}", font=("Arial", 14))
        self.label_nombre_asistente.pack()
        self.app_instance.label_nombre_asistente = self.label_nombre_asistente # Asignar a la instancia principal

        self.energy_threshold_slider = tk.Scale(self.root, from_=100, to=10000, orient='horizontal', label='suprimir ruido')
        self.energy_threshold_slider.set(self.app_instance.energy_threshold)
        self.energy_threshold_slider.pack()
        self.energy_threshold_slider.bind("<ButtonRelease-1>", self.app_instance.on_threshold_change)
        self.app_instance.energy_threshold_slider = self.energy_threshold_slider # Asignar a la instancia principal

        self.entry_cancion = tk.Entry(self.root, width=40)
        self.entry_cancion.pack(pady=10)
        self.app_instance.entry_cancion = self.entry_cancion # Asignar a la instancia principal

        self.btn_buscar_youtube = tk.Button(self.root, text="Buscar en YouTube (VLC)", command=self.app_instance.buscar_youtube_y_reproducir_desde_ui)
        self.btn_buscar_youtube.pack()

        self.canvas = tk.Canvas(self.root, width=100, height=100, bg='white')
        self.canvas.pack(side='bottom')
        self.estado_circulo = self.canvas.create_oval(20, 20, 80, 80, fill="red")
        self.app_instance.canvas = self.canvas # Asignar a la instancia principal
        self.app_instance.estado_circulo = self.estado_circulo # Asignar a la instancia principal

        btn_reset = tk.Button(self.root, text="Reiniciar Configuración", command=self.app_instance.reiniciar_configuracion)
        btn_reset.pack()

        self.root.protocol("WM_DELETE_WINDOW", self.app_instance.on_closing)
        self.app_instance.iniciar_en_hilo()