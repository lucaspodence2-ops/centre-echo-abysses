# Cendre — L'Écho des Abysses

Un souls-like metroidvania minimal, en Python/pygame, fidèle aux deux genres :

- **Souls-like** : les morts coûtent vos âmes (tache de sang à récupérer), endurance,
  roulade avec frames d'invincibilité, feux de cendre (checkpoints) qui raniment les
  ennemis, montée en puissance payée en âmes, boss avec phases enragées.
- **Metroidvania** : monde interconnecté de 6 salles, deux capacités qui ouvrent de
  nouveaux passages — **Ailes de Cendre** (double saut, laissées par le Gardien de
  Cendre) et **Passe d'Ombre** (roulade longue distance, dans la Grotte Murmurante) —
  plus un raccourci à sens unique pour reboucler.

Aucun asset externe : graphismes et sons dessinés/synthétisés par le code.

## Lancer

```bash
pip install -r requirements.txt
python cendre.py
```

## Objectif

1. Quittez la **Crypte des Origines**, traversez la **Salle des Étroits**.
2. Battez **Le Gardien de Cendre** dans le **Sanctuaire Déchu** → Ailes de Cendre.
3. Empruntez la porte du plafond de la Salle des Étroits → **Balgard de la Tour** →
   **Grotte Murmurante**.
4. Prenez la **Passe d'Ombre** sur son socle, franchissez le gouffre (saut + L),
   tombez dans le trou du fond.
5. Terrassez **L'Écho des Abysses**.

## Commandes

| Action | Touche |
|---|---|
| Se déplacer | Q / D, A / D ou flèches |
| Saut / double saut | Espace, Z / W ou haut |
| Attaque | J ou X |
| Roulade / Passe d'Ombre | L ou C |
| Fiole de cendre (soin) | K ou V |
| Interagir (feux de cendre) | E |
| Pause | Échap |

La roulade (L) donne des frames d'invincibilité : c'est votre meilleur outil contre
les coups de charge du Gardien.

## Architecture

```
src/
  main.py      États du jeu, règles, métroidvania (feux, âmes, portes)
  render.py    Rendu procédural (tuiles, boss, particules) + boucle
  player.py    Joueur : physique, combat, endurance, roulade, fioles
  enemies.py   Ennemis, projectiles, dangers, boss (Gardien, Écho)
  rooms.py     Grilles des 6 salles (générées) et connexions
  world.py     Salles : collisions, sorties, thèmes, caméra
  ui.py        HUD, menus, messages
  audio.py     Sons synthétisés (numpy)
  settings.py  Constantes
  savedata.py  Sauvegarde JSON locale
tests/
  selftest.py  Auto-tests headless (python tests/selftest.py)
  render_screens.py  Captures des zones (shots/)
```

## Tests

```bash
python tests/selftest.py
```

Vérifie, sans fenêtre : transitions entre salles, combat âmes/endurance, fioles,
feux de cendre + sauvegarde, mort / tache de sang / récupération, verrou métroidvania,
les deux boss et la victoire.

## Licence

MIT.
