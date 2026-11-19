"""Auto-test headless : exerce les systèmes principaux sans fenêtre."""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, SRC)

import pygame  # noqa: E402

from main import Game, InputState, level_cost  # noqa: E402
from rooms import build_rooms  # noqa: E402
import savedata  # noqa: E402
from settings import TILE as TILE_C  # noqa: E402

DT = 1 / 60
FAILS = []


def check(name, cond, extra=""):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        FAILS.append(name)


def make_input(**flags):
    inp = InputState()
    for k, v in flags.items():
        setattr(inp, k, v)
    return inp


def test_rooms():
    rooms = build_rooms()
    check(
        "6 salles définies",
        set(rooms) == {"crypt", "hall", "sanctuary", "tower", "cave", "abyss"},
    )
    for rid, d in rooms.items():
        rows = d["map"]
        check(f"{rid}: hauteur 22", len(rows) == 22)
        w = len(rows[0])
        check(f"{rid}: largeur constante", all(len(r) == w for r in rows))
    check(
        "boss gardien présent",
        any(d.get("boss") == "gardien" for d in rooms.values()),
    )
    check("boss écho présent", any(d.get("boss") == "echo" for d in rooms.values()))


def test_spawns_on_ground():
    for rid, d in build_rooms().items():
        rows = d["map"]
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch in "1234":
                    if ch == "3":
                        continue
                    below = rows[y + 1][x] if y + 1 < 22 else "#"
                    check(f"{rid} ennemi {ch} ({x},{y}) sur sol", below == "#")


def make_game():
    surf = pygame.Surface((1280, 720))
    game = Game(surf, enable_audio=False)
    game.new_game()
    return game


def run_frames(game, n, inp=None):
    if inp is None:
        inp = make_input()
    for _ in range(n):
        game.step(DT, inp)


def test_movement_and_transition():
    game = make_game()
    check("spawn crypte", game.current_rid == "crypt")
    inp = make_input(right=True)
    for _ in range(900):
        game.step(DT, inp)
        if game.current_rid == "hall":
            break
    check(
        "transition crypte -> salle en marchant",
        game.current_rid == "hall",
        f"x={game.player.rect.x} room={game.current_rid}",
    )


def test_attack_kills_enemy():
    game = make_game()
    player, enemy = game.player, game.enemies[0]
    enemy.rect.centerx = player.rect.centerx
    enemy.rect.centery = player.rect.centery
    souls0 = player.souls
    enemy.take_damage(999, 1, game)
    game.step(DT, make_input())
    check("ennemi tué -> âmes", player.souls - souls0 == 50, f"{player.souls} vs {souls0}")
    check("ennemi mort", enemy.dead)


def test_roll_and_stamina():
    game = make_game()
    p = game.player
    p.stamina = 100
    inp = make_input(roll_pressed=True, right=True)
    p.try_roll(inp, game)
    check("roulade active", p.roll_t > 0, f"roll_t={p.roll_t}")
    check("endurance dépensée", p.stamina < 100, f"st={p.stamina}")
    check("i-frames", p.iframes > 0, f"ifr={p.iframes}")
    run_frames(game, 60)
    check("endurance régénérée", p.stamina > 90, f"st={p.stamina}")


def test_flask_and_damage():
    game = make_game()
    p = game.player
    p.hp = 40
    inp = make_input(flask_pressed=True)
    game.step(DT, inp)
    run_frames(game, 50)
    check("fiole soigne", p.hp > 40, f"hp={p.hp}")
    check("fiole consommée", p.flasks == 2, f"fl={p.flasks}")
    dmg0 = p.hp
    p.iframes = 0
    p.take_damage(15, 1, game)
    check("dégâts reçus", p.hp == dmg0 - 15, f"hp={p.hp}")


def test_bonfire_rest_and_save():
    game = make_game()
    p = game.player
    p.hp = 33
    p.flasks = 0
    p.souls = 500
    game.fire_menu_pos = (8 * TILE_C + 16, 17 * TILE_C)
    game.fire_room = "crypt"
    game.do_bonfire_choice(0)
    check("repos soigne", p.hp == p.max_hp, f"hp={p.hp}")
    check("fioles rechargées", p.flasks == 3, f"fl={p.flasks}")
    saved = savedata.load_save()
    check("sauvegarde écrite", saved is not None)
    check("feu de cendre mémorisé", saved["bonfire"] == "crypt", str(saved))
    check("âmes sauvegardées", saved["souls"] == 500)
    return game


def test_level_up():
    game = make_game()
    game.player.souls = level_cost(0)
    game.fire_menu_pos = (8 * TILE_C + 16, 17 * TILE_C)
    game.fire_room = "crypt"
    hp0 = game.player.max_hp
    game.do_bonfire_choice(1)
    check("vigueur améliore les PV", game.player.max_hp == hp0 + 25,
          f"{game.player.max_hp} vs {hp0}")
    check("coût déduit", game.player.souls == 0)


def test_death_and_bloodstain():
    game = make_game()
    p = game.player
    p.souls = 333
    p.take_damage(9999, 0, game)
    check("mort déclenchée", p.dead and game.death_t > 0)
    check("tache de sang posée", game.blood is not None and game.blood["amount"] == 333)
    check("âmes perdues", p.souls == 0)
    p.rect.centerx = game.blood["x"]
    inp = make_input()
    for _ in range(220):
        game.step(DT, inp)
        if game.death_t <= 0 and not game.player.dead:
            break
    check("résurrection au feu", not p.dead and p.hp == p.max_hp)
    check("retour en jeu", game.state == "play")
    game.player.rect.center = (game.blood["x"], game.blood["y"])
    run_frames(game, 10)
    check("âmes récupérées", game.player.souls == 333 and game.blood is None,
          f"souls={game.player.souls}")


def test_gate_blocks_without_double_jump():
    game = make_game()
    game.enter_room("hall", "left", 300)
    p = game.player
    p.abilities = set()
    p.refresh_ability()
    p.rect.center = (71 * TILE_C, 2 * TILE_C + 20)
    run_frames(game, 90)
    check("porte du haut bloquée sans Ailes", game.current_rid == "hall",
          f"room={game.current_rid}")


def test_double_jump_progression():
    game = make_game()
    game.grant_ability("double_jump")
    game.enter_room("hall", "left", 300)
    p = game.player
    p.rect.center = (71 * TILE_C, 2 * TILE_C + 10)
    for i in range(220):
        inp = make_input(jump=(i % 40 < 8), jump_pressed=(i % 40 == 0))
        game.step(DT, inp)
        if game.current_rid == "tower":
            break
    check("Ailes de Cendre ouvrent la tour", game.current_rid == "tower",
          f"room={game.current_rid}")


def test_dash_pickup():
    game = make_game()
    game.enter_room("cave", "left")
    room = game.room
    ix, iy = room.item_pos
    game.player.rect.center = (ix, iy)
    run_frames(game, 4)
    check("Passe d'Ombre obtenue", "dash" in game.player.abilities)


def test_gardien_boss_and_reward():
    game = make_game()
    game.enter_room("sanctuary", "left", 300)
    check("gardien endormi", game.boss is not None and game.boss.state == "sleep")
    game.player.rect.centerx = 700
    inp = make_input()
    for _ in range(30):
        game.step(DT, inp)
    check("gardien réveillé", game.boss.state != "sleep")
    game.boss.take_damage(9999, 1, game)
    check("gardien mourant", game.boss.dead)
    for _ in range(140):
        game.step(DT, inp)
    check("Ailes de Cendre après le Gardien", "double_jump" in game.player.abilities)
    run_frames(game, 30)
    check("brume dissipée", game.active_fog is None)
    reloaded = savedata.load_save()
    check("boss vaincu sauvegardé", reloaded and reloaded["bosses_dead"] == ["sanctuary"])


def test_echo_boss_victory():
    game = make_game()
    game.enter_room("abyss", "top")
    game.player.rect.centerx = 1300
    inp = make_input()
    for _ in range(30):
        game.step(DT, inp)
    check("écho réveillé", game.boss is not None and game.boss.state != "sleep")
    game.boss.take_damage(99999, 1, game)
    for i in range(300):
        game.step(DT, inp)
        if game.state == "victory":
            break
    check("victoire après l'Écho", game.state == "victory", game.state)


def test_save_load_roundtrip():
    game = make_game()
    game.player.souls = 777
    game.vigor = 2
    game.endurance = 1
    game.player.abilities = {"double_jump", "dash"}
    game.player.refresh_ability()
    game.bosses_dead = {"sanctuary"}
    game.deaths = 4
    game.respawn_point = ("cave", (6 * TILE_C, 17 * TILE_C))
    game.current_rid = "cave"
    game.fire_menu_pos = (6 * TILE_C + 16, 17 * TILE_C)
    game.fire_room = "cave"
    game.do_bonfire_choice(0)
    data = savedata.load_save()
    check(
        "cycle: données complètes",
        data["souls"] == 777
        and data["vigor"] == 2
        and data["endurance"] == 1
        and sorted(data["abilities"]) == ["dash", "double_jump"]
        and data["bosses_dead"] == ["sanctuary"]
        and data["deaths"] == 4,
        str(data),
    )
    game2 = Game(pygame.Surface((1280, 720)), enable_audio=False)
    game2.load_game_at(data)
    check("cycle: chargé au feu", game2.current_rid == "cave", game2.current_rid)
    check("cycle: capacités actives", game2.player.max_jumps == 2)


def test_camera_and_render():
    game = make_game()
    run_frames(game, 60, make_input(right=True))
    from render import draw_death_overlay, draw_room_scene

    draw_room_scene(game.screen, game)
    game.death_t = 1.0
    draw_death_overlay(game.screen, game)
    check("rendu sans exception", True)


def cleanup():
    savedata.delete_save()


def main():
    pygame.init()
    try:
        test_rooms()
        test_spawns_on_ground()
        test_movement_and_transition()
        test_attack_kills_enemy()
        test_roll_and_stamina()
        test_flask_and_damage()
        test_bonfire_rest_and_save()
        test_level_up()
        test_death_and_bloodstain()
        test_gate_blocks_without_double_jump()
        test_double_jump_progression()
        test_dash_pickup()
        test_gardien_boss_and_reward()
        test_echo_boss_victory()
        test_save_load_roundtrip()
        test_camera_and_render()
    finally:
        pygame.quit()
        cleanup()
    if FAILS:
        print(f"\n{len(FAILS)} test(s) échoué(s) : {FAILS}")
        sys.exit(1)
    print("\nTous les tests passent.")


if __name__ == "__main__":
    main()
