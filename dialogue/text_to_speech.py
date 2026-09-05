"""Synthèse vocale (TTS) pour Reachy Mini.

Approche : pyttsx3 synthétise le texte dans un fichier WAV temporaire,
puis `mini.media.play_sound(path)` le joue sur le haut-parleur du robot
(API confirmée par la documentation officielle du SDK). C'est plus simple
et plus robuste que de pousser des échantillons bruts via
`push_audio_sample`, et ça fonctionne hors ligne (pyttsx3 utilise les
moteurs TTS du système, pas d'appel API externe).
"""

import tempfile
import time
import wave
from pathlib import Path
from typing import Optional

try:
    import pyttsx3
except ImportError:  # permet de développer/tester sans pyttsx3 installé
    pyttsx3 = None


class Speaker:
    """Convertit du texte en parole et le joue sur le haut-parleur du robot.

    Un seul `Speaker` doit être instancié par session (pyttsx3 conserve un
    état interne). `mini` doit être une connexion déjà ouverte, partagée
    avec le reste de l'application (voir `robotics.RobotSession`).
    """

    def __init__(self, mini, rate: int = 175, voice_lang_hint: Optional[str] = "fr"):
        if pyttsx3 is None:
            raise RuntimeError(
                "le package 'pyttsx3' n'est pas installé. "
                "pip install pyttsx3 pour activer la synthèse vocale."
            )
        self._mini = mini
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", rate)
        if voice_lang_hint:
            self._select_voice(voice_lang_hint)

        self._mini.media.start_playing()

    def _select_voice(self, lang_hint: str) -> None:
        """Sélectionne une voix correspondant à la langue si disponible
        (le nom des voix système varie selon l'OS, d'où une recherche
        approximative plutôt qu'un identifiant exact)."""
        for voice in self._engine.getProperty("voices"):
            haystack = f"{voice.name} {' '.join(voice.languages)}".lower()
            if lang_hint.lower() in haystack:
                self._engine.setProperty("voice", voice.id)
                return

    def say(self, text: str, block: bool = True) -> None:
        """Synthétise `text` et le joue sur le haut-parleur du robot."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name

        self._engine.save_to_file(text, wav_path)
        self._engine.runAndWait()

        self._mini.media.play_sound(wav_path)
        if block:
            time.sleep(_wav_duration_seconds(wav_path))

        Path(wav_path).unlink(missing_ok=True)

    def close(self) -> None:
        self._mini.media.stop_playing()


def _wav_duration_seconds(path: str) -> float:
    """Durée d'un fichier WAV, pour savoir combien de temps attendre après
    avoir lancé `play_sound` (non bloquant côté SDK)."""
    with wave.open(path, "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        return frames / float(rate)
