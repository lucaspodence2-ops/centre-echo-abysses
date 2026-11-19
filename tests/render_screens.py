"""Rend des captures d'écran pour vérifier visuellement les niveaux."""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, SRC)

import pygame

from main import Game, InputState
from render import draw_room_scene

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shots")


def make_input(**flags):
    inp = InputState()
    for k, v in flags.items():
        setattr(inp, k, v)
    return inp


def main():
    pygame.init()
    screen = pygame.Surface((1280, 720))
    game = Game(screen, enable_audio=False)
    game.new_game()
    game.menu_idx = 0
    game.banner_t = 0.0
    os.makedirs(OUT, exist_ok=True)

    shots = [
        ("crypt", "crypt", {}),
        ("hall", "hall", {}),
        ("sanctuary", "sanctuary", {}),
        ("tower", "tower", {}),
        ("cave", "cave", {}),
        ("abyss", "abyss", {}),
    ]
    for shot, rid, flags in shots:
        game.grant_ability("double_jump")
        game.grant_ability("dash")
        game.player.hp = game.player.max_hp
        game.enter_room(rid, "left")
        if rid == "sanctuary":
            game.player.rect.centerx = 700
        if rid == "abyss":
            game.player.rect.centerx = 1300
        for _ in range(40):
            game.step(1 / 60, make_input(**flags))
        game.banner_t = 0.0
        draw_room_scene(screen, game)
        pygame.image.save(screen, os.path.join(OUT, f"{shot}.png"))
        print("écrit", shot)
    pygame.quit()


if __name__ == "__main__":
    main()
