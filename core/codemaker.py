"""Génération et validation du code secret.

Utile si Reachy Mini tient parfois le rôle de codemaker (secret généré par
le programme), ou pour valider qu'un secret proposé par un humain respecte
bien les règles (longueur, couleurs autorisées, doublons ou non).
"""

import random
from typing import List, Sequence


def generate_secret(
    colors: Sequence[str], code_length: int, allow_repeats: bool = True
) -> List[str]:
    """Génère un code secret aléatoire.

    allow_repeats=True (mode Mastermind classique) autorise une même couleur
    plusieurs fois. Mettre False pour une variante sans répétition.
    """
    if not allow_repeats and code_length > len(colors):
        raise ValueError(
            "code_length > nombre de couleurs disponibles sans répétition"
        )
    if allow_repeats:
        return [random.choice(colors) for _ in range(code_length)]
    return random.sample(list(colors), code_length)


def validate_guess(
    guess: Sequence[str], colors: Sequence[str], code_length: int
) -> None:
    """Vérifie qu'un essai (ou un secret) est valide, lève ValueError sinon."""
    if len(guess) != code_length:
        raise ValueError(f"longueur attendue {code_length}, reçue {len(guess)}")
    invalid = set(guess) - set(colors)
    if invalid:
        raise ValueError(f"couleurs invalides : {invalid}")
