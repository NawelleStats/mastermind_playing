"""Synthèse vocale (TTS) pour Reachy Mini.

Approche : pyttsx3 synthétise le texte dans un fichier temporaire. macOS
produit un conteneur AIFF/AIFC malgré l'extension demandée, il est donc
converti en WAV PCM avant que `mini.media.play_sound(path)` le joue sur le
haut-parleur du robot
(API confirmée par la documentation officielle du SDK). C'est plus simple
et plus robuste que de pousser des échantillons bruts via
`push_audio_sample`, et ça fonctionne hors ligne (pyttsx3 utilise les
moteurs TTS du système, pas d'appel API externe).
"""

import tempfile
import time
import wave
import shutil
import struct
import json
import urllib.error
import urllib.request

from config import TTS_VOLUME
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
        self._engine.setProperty("volume", TTS_VOLUME)
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
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
            source_path = tmp.name
        wav_path = f"{source_path}.wav"

        self._engine.save_to_file(text, source_path)
        self._engine.runAndWait()
        _ensure_wav(source_path, wav_path)

        try:
            print(f"[audio] lecture Reachy : {text}")
            print(f"[audio] fichier WAV : {wav_path} ({_wav_duration_seconds(wav_path):.1f}s)")
            _play_sound_with_status(self._mini, wav_path)
            if block:
                time.sleep(_wav_duration_seconds(wav_path))
        finally:
            Path(source_path).unlink(missing_ok=True)
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


def _play_sound_with_status(mini, wav_path: str) -> None:
    """Upload puis joue le WAV en remontant les erreurs du daemon."""
    audio = getattr(mini.media, "audio", None)
    daemon_url = getattr(audio, "daemon_url", None)
    upload_sound = getattr(audio, "upload_sound", None)
    if not daemon_url or upload_sound is None:
        mini.media.play_sound(wav_path)
        return

    remote_path = upload_sound(wav_path)
    request = urllib.request.Request(
        f"{daemon_url}/api/media/play_sound",
        data=json.dumps({"file": remote_path}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
            print(f"[audio] daemon : HTTP {response.status} {response_body}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Le daemon a refusé la lecture audio (HTTP {error.code}) : {detail}"
        ) from error



def _ensure_wav(source_path: str, wav_path: str) -> None:
    """Produit un WAV PCM, y compris quand macOS écrit un fichier AIFF."""
    source = Path(source_path).read_bytes()
    if source[:4] == b"RIFF" and source[8:12] == b"WAVE":
        shutil.copyfile(source_path, wav_path)
        return
    if source[:12] not in (
        b"FORM" + source[4:8] + b"AIFF",
        b"FORM" + source[4:8] + b"AIFC",
    ):
        raise ValueError("pyttsx3 n'a pas produit un fichier audio AIFF ou WAV valide")

    is_aifc = source[8:12] == b"AIFC"
    channels = sample_width = sample_rate = None
    audio_data = None
    offset = 12
    while offset + 8 <= len(source):
        chunk_id = source[offset:offset + 4]
        chunk_size = struct.unpack(">I", source[offset + 4:offset + 8])[0]
        chunk = source[offset + 8:offset + 8 + chunk_size]
        if chunk_id == b"COMM":
            channels, _, sample_width = struct.unpack(">H I H", chunk[:8])
            sample_rate = round(_decode_extended_float(chunk[8:18]))
            if is_aifc and chunk[18:22] not in (b"NONE", b"raw ", b"twos"):
                raise ValueError("Le fichier AIFF utilise un codec non PCM")
        elif chunk_id == b"SSND":
            data_offset = struct.unpack(">I", chunk[:4])[0]
            audio_data = chunk[8 + data_offset:]
        offset += 8 + chunk_size + (chunk_size % 2)

    if not all((channels, sample_width, sample_rate)) or audio_data is None:
        raise ValueError("Fichier AIFF incomplet produit par pyttsx3")

    byte_width = sample_width // 8
    if sample_width % 8:
        raise ValueError(f"Profondeur audio AIFF non supportée : {sample_width} bits")
    little_endian = b"".join(
        audio_data[index:index + byte_width][::-1]
        for index in range(0, len(audio_data), byte_width)
    )
    with wave.open(wav_path, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(byte_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(little_endian)


def _decode_extended_float(value: bytes) -> float:
    """Décode le float IEEE 80 bits utilisé par le format AIFF."""
    exponent, mantissa = struct.unpack(">H Q", value)
    if exponent == 0 and mantissa == 0:
        return 0.0
    sign = -1 if exponent & 0x8000 else 1
    exponent = exponent & 0x7FFF
    return sign * (mantissa / 2**63) * 2 ** (exponent - 16383)
