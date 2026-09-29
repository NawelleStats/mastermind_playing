# WIP: la logique du jeu doit être reconstruite (next step: ajout d'une couche de ML)

# Mastermind avec Reachy Mini

Jeu de Mastermind jouable avec le robot Reachy Mini, dans les deux rôles :

- **Reachy Mini codemaker** : tu places un secret à l'aveugle, sa caméra le
  perçoit, et il t'annonce le score (pions noirs/blancs) à chaque essai.
- **Reachy Mini codebreaker** : tu places un secret, Reachy Mini propose ses
  essais (algorithme minimax type Knuth) et tu lui donnes ton feedback avec
  des pions noir/blanc que sa caméra lit.

## Architecture

```
mastermind_reachy/
├── main.py                # point d'entrée : lance une partie
├── .env.exemple           # en local .env avec les variables d'environnement
├── config.py              # gestion des variables de l'application
├── calibrate.py           # génère board_calibration.json
├── board_calibration.json # généré par calibrate.py (absent au départ)
│
├── core/                  # logique de jeu pure, sans dépendance robot
│   ├── rules.py             # calcul du feedback (pions noirs/blancs)
│   ├── board.py              # état du plateau, historique des essais
│   ├── codemaker.py           # génération/validation du secret
│   └── solver.py               # stratégie de résolution (minimax type Knuth)
│
├── perception/             # ce que "voit" Reachy Mini
│   ├── camera.py              # wrapper caméra (SDK Reachy Mini + webcam de test)
│   ├── color_detector.py       # classification HSV : couleurs de jeu + noir/blanc
│   ├── peg_localizer.py         # lecture d'une grille de trous calibrée
│   ├── calibration.py            # outil interactif de calibration
│   └── live_view.py               # affichage live + flux "nouvelle ligne détectée"
│
├── orchestrator/            # machine à états du jeu
│   └── game_fsm.py             # CodebreakerOrchestrator / CodemakerOrchestrator
│
├── robotics/                # connexion Reachy, gestes et pointage
├── dialogue/                # annonces vocales et reconnaissance vocale optionnelle
│
└── tests/
```

`core/` et `perception/` sont indépendants l'un de l'autre : toute la
logique de jeu est testable sans caméra ni robot.

## Installation

```bash
uv sync
source .venv/bin/activate

cp .env.example .env
```

`uv sync` crée et gère l'environnement virtuel `.venv` ainsi que les
dépendances du projet. Pour exécuter une commande sans activer
l'environnement :

```bash
uv run python calibrate.py --webcam
```

Après le premier `uv sync`, utilise `uv run --no-sync` pour lancer
instantanément le script sans que `uv` revérifie l'environnement à chaque
fois :

```bash
uv run --no-sync python calibrate.py
```

Les valeurs par défaut sont dans `.env` : dimensions du plateau, couleurs,
nombre d'essais et paramètres de connexion Reachy. La longueur du code est
toujours égale au nombre de colonnes.
Utilise `.env.example` comme modèle; les options passées sur la ligne de
commande de `calibrate.py` restent prioritaires.

> Utilise `opencv-python` (pas `opencv-python-headless`) : les fenêtres de
> calibration et de vision live ont besoin d'un affichage.

## 1. Calibrer le plateau

Nécessaire une fois par installation physique (position caméra/plateau).
À refaire si l'un des deux bouge.

**Sans robot (test sur la webcam de l'ordinateur) :**
```bash
uv run python calibrate.py --webcam
```

**Avec Reachy Mini branché :**
```bash
uv run python calibrate.py
```

Si la découverte mDNS ne fonctionne pas, indiquez directement l'adresse du
daemon :
```bash
export REACHY_MINI_HOST=192.168.1.95
export REACHY_MINI_PORT=8000
uv run python calibrate.py
uv run python main.py codebreaker
```

Options utiles :
```bash
uv run python calibrate.py --rows 12 --columns 5 \
  --colors rouge,bleu,vert,jaune,orange,violet,noir,blanc
```

`--rows` et `--columns` décrivent la grille physique. Le code secret contient
un pion par colonne : une grille de 5 × 12 utilise donc un code de 5 pions.
Les couleurs indiquées sont également celles utilisées par le jeu après la
calibration.

Déroulé :
1. Une fenêtre live dédiée au **code secret** s'ouvre d'abord pour annoter la
  ligne 0, puis une seconde fenêtre permet d'annoter les lignes restantes de
  la grille. `r` supprime uniquement le dernier point et `q`/Entrée valide
  l'étape en cours.
2. Une seconde fenêtre demande de cliquer un pion de chaque couleur, pour
   calibrer les teintes réelles sous ton éclairage.
3. Le résultat est sauvegardé dans `board_calibration.json`.

Pour vérifier la calibration à tout moment (fenêtre live avec overlay des
couleurs détectées, `q` pour quitter) :
```python
from perception import BoardLayout, run_display
run_display(BoardLayout.load("board_calibration.json"))
```

## 2. Jouer

```bash
uv run python main.py codemaker      # Reachy Mini tient le secret
uv run python main.py codebreaker    # Reachy Mini devine ton secret
```

Pour afficher ce que voit la caméra pendant la partie :

```bash
uv run --no-sync python main.py codebreaker --show-camera
```

La fenêtre `VISION ROBOT` affiche la grille observée; `Q` ferme l'affichage.

- **Codemaker** : place ta combinaison secrète sur la ligne 0 sans la
  regarder toi-même si tu veux jouer honnêtement, puis place tes essais sur
  les lignes suivantes. Reachy Mini annonce le score après chaque essai
  stable (quelques secondes après que tu as fini de poser les pions).
- **Codebreaker** : place ton secret, Reachy Mini annonce son essai à voix
  haute et accompagne l'annonce de gestes, puis place ton feedback en
  pions noir/blanc sur la ligne correspondante.

## État actuel du projet

| Module | État |
|---|---|
| `core/` | ✅ fonctionnel et testé |
| `perception/` | ✅ fonctionnel (calibration manuelle requise) |
| `orchestrator/` | ✅ fonctionnel |
| `robotics/` | ✅ connexion partagée, gestes et pointage |
| `dialogue/` | ✅ annonces vocales via le haut-parleur du robot |

`main.py` partage une unique `RobotSession` entre la caméra, les gestes et
le dialogue. La dépendance `pyttsx3` est nécessaire pour les annonces
vocales hors ligne.

## Tests

```bash
uv run pytest tests/
```

`core/` est testable indépendamment du matériel. `perception/` peut être
testé sur des images synthétiques (voir les exemples dans les tests) sans
caméra réelle.
