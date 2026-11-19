"""Sauvegarde et chargement de la progression (JSON local)."""

import json
import os

from settings import PATH_SAVE

DEFAULT_SAVE = {
    "vigor": 0,
    "endurance": 0,
    "souls": 0,
    "abilities": [],
    "bosses_dead": [],
    "bonfire": None,
    "last_room": "crypt",
    "flasks": 3,
    "deaths": 0,
    "playtime": 0.0,
}


def save_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), PATH_SAVE)


def load_save():
    path = save_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    merged = dict(DEFAULT_SAVE)
    merged.update({k: v for k, v in data.items() if k in DEFAULT_SAVE})
    return merged


def write_save(data):
    clean = {k: data.get(k, DEFAULT_SAVE[k]) for k in DEFAULT_SAVE}
    try:
        with open(save_path(), "w", encoding="utf-8") as fh:
            json.dump(clean, fh, indent=2)
        return True
    except OSError:
        return False


def delete_save():
    path = save_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
