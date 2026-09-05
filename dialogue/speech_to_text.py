"""Reconnaissance vocale (STT) pour Reachy Mini.

Optionnel dans le flux de jeu actuel : les deux modes (codemaker et
codebreaker) lisent les essais/le secret via la caméra, pas la voix. Ce
module est fourni pour une extension future (ex: annoncer son essai à
voix haute plutôt que de placer des pions), ou pour des confirmations
vocales simples ("c'est prêt", "oui"/"non").
"""

import numpy as np

try:
    import whisper
except ImportError:  # dépendance lourde et optionnelle
    whisper = None


class Listener:
    """Enregistre l'audio du micro de Reachy Mini et le transcrit.

    `mini` doit être une connexion déjà ouverte, partagée avec le reste de
    l'application (voir `robotics.RobotSession`).
    """

    def __init__(self, mini, whisper_model: str = "base"):
        self._mini = mini
        self._model = None
        self._whisper_model_name = whisper_model
        self._mini.media.start_recording()

    def _ensure_model_loaded(self):
        if whisper is None:
            raise RuntimeError(
                "le package 'openai-whisper' n'est pas installé. "
                "pip install openai-whisper pour activer la transcription. "
                "Sans lui, utilisez record_seconds() et traitez l'audio vous-même."
            )
        if self._model is None:
            self._model = whisper.load_model(self._whisper_model_name)

    def record_seconds(self, duration: float) -> np.ndarray:
        """Enregistre `duration` secondes d'audio brut (float32, mono/stéréo
        selon le matériel, échantillonné à la fréquence native du robot).
        """
        samples = self._mini.media.get_audio_sample()
        target_len = int(duration * self._mini.media.get_input_audio_samplerate())
        # get_audio_sample() renvoie généralement un buffer court : on
        # accumule jusqu'à atteindre la durée demandée.
        buffer = [samples]
        total = len(samples)
        while total < target_len:
            chunk = self._mini.media.get_audio_sample()
            buffer.append(chunk)
            total += len(chunk)
        return np.concatenate(buffer, axis=0)[:target_len]

    def listen_and_transcribe(self, duration: float, language: str = "fr") -> str:
        """Enregistre puis transcrit en texte. Nécessite `openai-whisper`."""
        self._ensure_model_loaded()
        audio = self.record_seconds(duration)

        # whisper attend un signal mono float32 à 16kHz : le SDK Reachy Mini
        # échantillonne déjà à 16kHz (voir doc officielle), on ne convertit
        # que le nombre de canaux si besoin.
        if audio.ndim == 2 and audio.shape[1] > 1:
            audio = audio.mean(axis=1)
        audio = audio.astype(np.float32)

        result = self._model.transcribe(audio, language=language)
        return result["text"].strip()

    def close(self) -> None:
        self._mini.media.stop_recording()
