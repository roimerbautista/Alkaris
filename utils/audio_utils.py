import numpy as np

def normalizar_audio(audio, sr):
    """
    Normaliza el audio para que el pico más alto sea -1.0 dBFS.
    """
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio_normalizado = audio / peak * 0.99
    else:
        audio_normalizado = audio
    return audio_normalizado