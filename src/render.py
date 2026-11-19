"""Rendu de la scène et boucle principale."""

import math
import sys

import pygame

import ui
from main import Game, build_input
from settings import COLORS, PLAYER, TILE, WS_HEIGHT, WS_WIDTH


def draw_backdrop(surf, room, cam):
    theme = room.theme
    for y in range(WS_HEIGHT):
        k = y / WS_HEIGHT
        c = tuple(
            int(theme["sky_top"][i] + (theme["sky_bot"][i] - theme["sky_top"][i]) * k)
            for i in range(3)
        )
        pygame.draw.line(surf, c, (0, y), (WS_WIDTH, y))
    for pillar in room.pillars:
        d = pygame.Rect(
            int(pillar.x - cam.x * 0.35),
            int(pillar.y - cam.y * 0.25),
            pillar.w,
            pillar.h,
        )
        shade = pygame.Surface((d.w, d.h), pygame.SRCALPHA)
        shade.fill((*theme["silhouette"], 170))
        surf.blit(shade, d.topleft)


def _lighten(color, f=0.22):
    return tuple(min(255, int(c + (255 - c) * f)) for c in color)


def draw_tiles(surf, room, cam):
    theme = room.theme
    edge = _lighten(theme["tile_a"], 0.30)
    for r in room.solids:
        d = cam.apply(r)
        if d.right < -10 or d.left > WS_WIDTH + 10 or d.bottom < -10 or d.top > WS_HEIGHT + 10:
            continue
        pygame.draw.rect(surf, theme["tile_a"], d)
        pygame.draw.rect(surf, edge, (d.x, d.y, d.w, min(5, d.h // 3)))
        pygame.draw.rect(surf, theme["tile_b"], (d.x, d.bottom - max(2, d.h // 6), d.w, max(2, d.h // 6)))
        pygame.draw.rect(surf, (10, 10, 12), d, 1)
        if d.w > 70:
            for gx in range(d.x + 64, d.right, 64):
                pygame.draw.line(surf, theme["tile_b"], (gx, d.y + 3), (gx, d.bottom - 3))


def draw_exits(surf, room, cam):
    for ex in room.exits:
        a, b = ex.span
        locked = ex.need is not None
        if ex.side in ("left", "right"):
            r = pygame.Rect(
                -8 if ex.side == "left" else room.width - 24,
                a * TILE, 32, (b - a + 1) * TILE,
            )
        elif ex.side == "top":
            r = pygame.Rect(a * TILE, -8, (b - a + 1) * TILE, 40)
        else:
            r = pygame.Rect(a * TILE, room.height - 24, (b - a + 1) * TILE, 32)
        d = cam.apply(r)
        shade = pygame.Surface((max(1, d.w), max(1, d.h)), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 130))
        surf.blit(shade, d.topleft)
        if locked:
            pygame.draw.rect(surf, (150, 120, 60), d, 3)


def draw_spikes(surf, room, cam):
    for spike in room.spikes:
        d = cam.apply(spike)
        if d.right < -10 or d.left > WS_WIDTH + 10:
            continue
        pts = [(d.x, d.bottom), (d.x + d.w / 2, d.y - 4), (d.right, d.bottom)]
        pygame.draw.polygon(surf, (150, 150, 160), pts)
        pygame.draw.polygon(surf, (60, 60, 70), pts, 2)


def draw_bonfire(surf, room, cam, t, near):
    for px, py in room.bonfires:
        cx, cy = px + TILE // 2, py + TILE
        sx, sy = cam.to_screen(cx, cy)
        glow = pygame.Surface((110, 110), pygame.SRCALPHA)
        for rad, alpha in ((52, 34), (34, 70), (20, 110)):
            pygame.draw.circle(glow, (255, 140, 40, alpha), (55, 62), rad)
        surf.blit(glow, (sx - 55, sy - 62))
        pygame.draw.rect(surf, (70, 70, 80), (sx - 14, sy - 12, 28, 12))
        pygame.draw.line(surf, (160, 150, 130), (sx + 16, sy - 74), (sx - 6, sy - 4), 5)
        pygame.draw.line(surf, (100, 100, 110), (sx + 16, sy - 74), (sx - 4, sy - 6), 2)
        flick = math.sin(t * 9) * 3
        pygame.draw.polygon(surf, (235, 120, 40), [
            (sx - 12, sy - 10), (sx, sy - 34 - flick), (sx + 12, sy - 10),
        ])
        pygame.draw.polygon(surf, (250, 220, 120), [
            (sx - 6, sy - 10), (sx, sy - 24 - flick), (sx + 6, sy - 10),
        ])
        if near:
            return


def draw_item(surf, game, cam):
    room = game.room
    if not room.item or room.item in game.player.abilities or not room.item_pos:
        return
    ix, iy = room.item_pos
    sx, sy = cam.to_screen(ix, iy + math.sin(game.title_t * 3) * 5)
    glow = pygame.Surface((80, 80), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 210, 120, 60), (40, 40), 36)
    pygame.draw.circle(glow, (255, 230, 160, 110), (40, 40), 20)
    surf.blit(glow, (sx - 40, sy - 40))
    pygame.draw.circle(surf, (255, 235, 180), (sx, sy), 7)


def draw_blood(surf, game, cam):
    b = game.blood
    if not b or b.get("rid") != game.current_rid:
        return
    sx, sy = cam.to_screen(b["x"], b["y"])
    pulse = pygame.Surface((40, 40), pygame.SRCALPHA)
    pygame.draw.circle(pulse, (160, 30, 30, 80), (20, 20), 18)
    surf.blit(pulse, (sx - 20, sy - 20))
    pygame.draw.circle(surf, (100, 22, 26), (sx, sy), 15)
    pygame.draw.circle(surf, (160, 44, 44), (sx, sy), 8)


def draw_fog(surf, game, t):
    fog = getattr(game, "active_fog", None)
    if not fog:
        return
    d = game.cam.apply(fog)
    s = pygame.Surface((d.w, d.h), pygame.SRCALPHA)
    for yy in range(0, d.h, 8):
        alpha = 80 + int(35 * math.sin(t * 3 + yy * 0.12))
        pygame.draw.line(s, (140, 60, 190, alpha), (0, yy), (d.w, yy), 4)
    pygame.draw.rect(s, (180, 110, 240, 220), s.get_rect(), 3)
    surf.blit(s, d.topleft)


def draw_enemies(surf, game, cam):
    for e in game.enemies:
        if e.dead and e.dying <= 0:
            continue
        d = cam.apply(e.rect)
        if d.right < -30 or d.left > WS_WIDTH + 30:
            continue
        color, eye = {
            "hollow": ((72, 70, 82), (255, 214, 92)),
            "heavy": ((94, 66, 56), (255, 96, 64)),
            "archer": ((62, 84, 70), (140, 255, 190)),
            "flyer": ((74, 64, 88), (200, 140, 255)),
        }[e.etype]
        if e.state == "windup":
            eye = (255, 90, 60)
        body = d.inflate(-4, 0)
        pygame.draw.rect(surf, color, body, border_radius=6)
        pygame.draw.rect(surf, (14, 14, 18), body, 1, border_radius=6)
        pygame.draw.circle(surf, eye, (d.centerx + e.face * 4, d.y + 10), 3)
        if e.etype == "hollow":
            pygame.draw.rect(surf, (30, 30, 36), (d.x + 2, d.y - 3, d.w - 4, 7), border_radius=3)
        if e.etype == "flyer":
            flap = math.sin(game.title_t * 22) * 6
            pygame.draw.polygon(surf, (70, 60, 90),
                                ((d.centerx, d.centery),
                                 (d.centerx - 20, d.centery - 14 + flap * e.face),
                                 (d.centerx - 8, d.centery + 2)))
            pygame.draw.polygon(surf, (70, 60, 90),
                                ((d.centerx, d.centery),
                                 (d.centerx + 20, d.centery - 14 - flap * e.face),
                                 (d.centerx + 8, d.centery + 2)))
        if e.flash > 0:
            fl = pygame.Surface(d.size, pygame.SRCALPHA)
            fl.fill((255, 255, 255, min(200, int(e.flash * 1300))))
            surf.blit(fl, d.topleft)


def draw_boss(surf, game, cam):
    boss = game.boss
    if not boss:
        return
    if boss.dead and boss.dying <= 0:
        return
    d = cam.apply(boss.rect)
    if boss.etype == "gardien":
        pygame.draw.rect(surf, (70, 62, 68), d, border_radius=10)
        pygame.draw.rect(surf, (18, 16, 18), d, 3, border_radius=10)
        inner = d.inflate(-28, -18)
        pygame.draw.rect(surf, (96, 84, 90), inner, border_radius=8)
        for hx in (d.x + 10, d.right - 18):
            pygame.draw.polygon(surf, (26, 24, 26),
                                [(hx, d.y + 14), (hx + 7, d.y - 16), (hx + 11, d.y + 14)])
        ex = d.centerx + boss.face * 10
        pygame.draw.line(surf, (255, 150, 40), (ex - 8, d.y + 26), (ex + 8, d.y + 26), 3)
        if boss.state in ("charge_tel", "charge"):
            pygame.draw.rect(surf, (205, 60, 40), d.inflate(12, 12), 3, border_radius=10)
        if boss.state == "stun":
            pygame.draw.circle(surf, (240, 220, 120), (d.centerx, d.y - 18), 5)
        if boss.state == "swing" and boss.t > 0.2:
            sb = boss._swing_box()
            sd = cam.apply(sb)
            pygame.draw.arc(surf, (230, 230, 250), sd, 0, math.pi, 4)
    else:
        if not boss.visible:
            pass
        else:
            s = pygame.Surface(d.size, pygame.SRCALPHA)
            pygame.draw.ellipse(s, (120, 60, 170, 175), s.get_rect())
            pygame.draw.ellipse(s, (190, 120, 240, 60), s.get_rect().inflate(-10, -14))
            surf.blit(s, d.topleft)
            pygame.draw.circle(surf, (255, 200, 255), (d.centerx - 10, d.y + 26), 4)
            pygame.draw.circle(surf, (255, 200, 255), (d.centerx + 10, d.y + 26), 4)
    if boss.flash > 0:
        fl = pygame.Surface(d.size, pygame.SRCALPHA)
        fl.fill((255, 255, 255, min(190, int(boss.flash * 1300))))
        surf.blit(fl, d.topleft)


def draw_projectiles(surf, game, cam):
    for proj in game.projectiles:
        sx, sy = cam.to_screen(proj.x, proj.y)
        glow = pygame.Surface((proj.r * 5, proj.r * 5), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*proj.color, 70), (proj.r * 2 + proj.r // 2,) * 2, proj.r * 2)
        surf.blit(glow, (sx - proj.r * 2 - proj.r // 2, sy - proj.r * 2 - proj.r // 2))
        pygame.draw.circle(surf, proj.color, (sx, sy), proj.r)


def draw_hazards(surf, game, cam, t):
    for hz in game.hazards:
        d = cam.apply(hz.rect)
        s = pygame.Surface((d.w, d.h), pygame.SRCALPHA)
        if hz.t < hz.delay:
            k = 0.35 + 0.5 * abs(math.sin(t * 9))
            s.fill((200, 60, 40, int(70 * k)))
            pygame.draw.rect(s, (220, 90, 60, 170), s.get_rect(), 2)
        else:
            s.fill((255, 120, 40, 150))
            pygame.draw.rect(s, (255, 220, 120, 210), s.get_rect().inflate(-8, 0))
        surf.blit(s, d.topleft)


def draw_particles(surf, game, cam):
    for part in game.particles:
        sx, sy = cam.to_screen(part["x"], part["y"])
        r = max(1, int(part["size"] * min(1.0, part["ttl"] * 2)))
        if -6 <= sx <= WS_WIDTH + 6 and -6 <= sy <= WS_HEIGHT + 6:
            pygame.draw.circle(surf, part["color"], (sx, sy), r)


def draw_ambient(surf, game, cam):
    color = {"ember": (255, 150, 60), "ash": (205, 205, 215), "dust": (160, 160, 175)}[
        game.room.theme["particle"]
    ]
    for a in game.ambient:
        sx, sy = cam.to_screen(a["x"], a["y"])
        if -10 <= sx <= WS_WIDTH + 10 and -10 <= sy <= WS_HEIGHT + 10:
            pygame.draw.circle(surf, color, (sx, sy), int(a["size"]))


def draw_player(surf, game, cam):
    p = game.player
    d = cam.apply(p.rect)
    if p.dead:
        s = pygame.Surface((d.w, d.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (60, 60, 72, 190), s.get_rect(), border_radius=8)
        surf.blit(s, d.topleft)
        return
    blink = p.iframes > 0 and int(p.anim_t * 30) % 2 == 0
    if p.hurt_t > 0 and int(p.anim_t * 30) % 2 == 0:
        body_color = (205, 70, 70)
    elif blink:
        body_color = (215, 185, 185)
    else:
        body_color = (150, 152, 162)
    if p.state == "roll":
        spin = (1.0 - p.roll_t / PLAYER["roll_time"]) * 360
        s = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.rect(s, (*body_color, 225), (4, 4, 32, 32), border_radius=10)
        rot = pygame.transform.rotate(s, int(spin) * p.roll_dir)
        surf.blit(rot, rot.get_rect(center=d.center).topleft)
    else:
        cape = [
            (d.centerx - p.facing * 6, d.y + 10),
            (d.centerx - p.facing * (18 + 3 * math.sin(p.anim_t * 8)), d.y + 24),
            (d.centerx - p.facing * 8, d.bottom - 4),
        ]
        pygame.draw.polygon(surf, (125, 32, 32), cape)
        body = d.inflate(-6, -2)
        body.bottom = d.bottom
        pygame.draw.rect(surf, body_color, body, border_radius=6)
        helm = pygame.Rect(d.x + 4, d.y, d.w - 8, 16)
        pygame.draw.rect(surf, (118, 122, 132), helm, border_radius=6)
        pygame.draw.line(
            surf,
            (255, 175, 60) if p.hurt_t <= 0 else (220, 60, 60),
            (helm.centerx - 4, helm.y + 8),
            (helm.centerx + 4, helm.y + 8),
            2,
        )
        if p.state == "drink":
            pygame.draw.circle(surf, (255, 170, 60), (d.centerx, d.y - 6), 5)
    if p.atk_phase == "active":
        s = pygame.Surface((130, 100), pygame.SRCALPHA)
        if p.facing > 0:
            pygame.draw.arc(s, (240, 240, 255, 210), (0, 8, 126, 84), 0.35, math.pi * 0.8, 5)
            surf.blit(s, (d.centerx - 6, d.centery - 50))
        else:
            pygame.draw.arc(s, (240, 240, 255, 210), (4, 8, 126, 84), math.pi * 0.2, math.pi - 0.35, 5)
            flipped = pygame.transform.flip(s, True, False)
            surf.blit(flipped, (d.centerx - 126, d.centery - 50))
    if p.dj_fx > 0:
        wing_a = int(150 * (p.dj_fx / 0.25))
        s = pygame.Surface((92, 56), pygame.SRCALPHA)
        pygame.draw.polygon(s, (255, 200, 120, wing_a), [(6, 52), (46, 4), (86, 52)])
        surf.blit(s, (d.centerx - 46, d.bottom - 44))


def draw_room_scene(surf, game):
    room = game.room
    cam = game.cam
    draw_backdrop(surf, room, cam)
    draw_ambient(surf, game, cam)
    draw_tiles(surf, room, cam)
    draw_exits(surf, room, cam)
    draw_spikes(surf, room, cam)
    draw_bonfire(surf, room, cam, game.title_t, getattr(game, "near_fire", False))
    draw_item(surf, game, cam)
    draw_blood(surf, game, cam)
    draw_hazards(surf, game, cam, game.title_t)
    draw_boss(surf, game, cam)
    draw_enemies(surf, game, cam)
    draw_projectiles(surf, game, cam)
    draw_fog(surf, game, game.title_t)
    draw_player(surf, game, cam)
    draw_particles(surf, game, cam)
    if 0 < game.banner_t < 2.2:
        s = game.font.render(room.name, True, COLORS["white"])
        k = game.banner_t / 2.2
        surf.set_alpha(int(255 * min(1.0, k)))
        surf.blit(s, s.get_rect(center=(WS_WIDTH // 2, 78)))
        surf.set_alpha(255)
    if getattr(game, "near_fire", False) and not game.player.dead:
        hint = game.small.render("E — feu de cendre (se reposer)", True, COLORS["gold"])
        surf.blit(hint, hint.get_rect(center=(WS_WIDTH // 2, WS_HEIGHT - 40)))


def draw_death_overlay(surf, game):
    k = min(1.0, (2.8 - game.death_t) / 1.2)
    s = pygame.Surface((WS_WIDTH, WS_HEIGHT), pygame.SRCALPHA)
    s.fill((25, 0, 0, int(160 * k)))
    surf.blit(s, (0, 0))
    if k >= 1.0 or game.death_t < 2.2:
        txt = game.big.render("VOUS ÊTES MORT", True, (170, 24, 24))
        surf.blit(txt, txt.get_rect(center=(WS_WIDTH // 2, 320)))


def run():
    pygame.init()
    pygame.display.set_caption("Cendre — L'Écho des Abysses")
    screen = pygame.display.set_mode((WS_WIDTH, WS_HEIGHT))
    clock = pygame.time.Clock()
    game = Game(screen)
    prev = None
    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if game.state == "play":
                        game.state = "pause"
                        game.menu_idx = 0
                    elif game.state in ("pause", "bonfire"):
                        game.state = "play"
                    elif game.state == "help":
                        game.state = "title"
                if (
                    ev.key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE)
                    and game.state == "victory"
                ):
                    game.state = "title"
        keys = pygame.key.get_pressed()
        inp = build_input(keys, prev)
        prev = _snapshot(keys, inp)
        game.step(dt, inp)

        if game.state == "play":
            draw_room_scene(screen, game)
            ui.draw_hud(screen, game, game.font, game.small)
            ui.draw_boss_bar(screen, game, game.font)
            if game.death_t > 0:
                draw_death_overlay(screen, game)
        elif game.state == "pause":
            draw_room_scene(screen, game)
            dim = pygame.Surface((WS_WIDTH, WS_HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))
            screen.blit(dim, (0, 0))
            txt = game.font.render("Pause — Échap pour reprendre", True, COLORS["white"])
            screen.blit(txt, txt.get_rect(center=(WS_WIDTH // 2, 330)))
            ui.draw_hud(screen, game, game.font, game.small)
        elif game.state == "bonfire":
            draw_room_scene(screen, game)
            dim = pygame.Surface((WS_WIDTH, WS_HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 135))
            screen.blit(dim, (0, 0))
            ui.draw_menu(screen, game.font, game.small, "FEU DE CENDRE",
                         f"Âmes : {game.player.souls}", game.bonfire_options(),
                         game.menu_idx)
        elif game.state == "title":
            screen.fill((8, 8, 10))
            ui.draw_menu(screen, game.font, game.small, "CENDRE",
                         "L'Écho des Abysses",
                         game.menu_options or ["Nouvelle partie", "Contrôles", "Quitter"],
                         game.menu_idx)
        elif game.state == "victory":
            screen.fill((10, 8, 6))
            txt = game.big.render("L'AUBE SE LÈVE", True, COLORS["gold"])
            screen.blit(txt, txt.get_rect(center=(WS_WIDTH // 2, 250)))
            stats = game.small.render(
                f"Morts : {game.deaths}    Âmes : {game.player.souls}    "
                f"Temps : {int(game.playtime // 60)} min {int(game.playtime % 60)} s",
                True, COLORS["text"],
            )
            screen.blit(stats, stats.get_rect(center=(WS_WIDTH // 2, 370)))
            hint = game.small.render("Entrée — retour au titre", True, COLORS["faded"])
            screen.blit(hint, hint.get_rect(center=(WS_WIDTH // 2, 430)))
        elif game.state == "help":
            ui.draw_help(screen, game.font, game.small)
        if game.flash_t > 0:
            fl = pygame.Surface((WS_WIDTH, WS_HEIGHT), pygame.SRCALPHA)
            fl.fill((255, 220, 140, int(120 * game.flash_t)))
            screen.blit(fl, (0, 0))
        pygame.display.flip()
    pygame.quit()
    sys.exit(0)


def _snapshot(keys, inp):
    class Snap:
        pass
    s = Snap()
    s.jump = inp.jump
    s.attack = inp.attack
    s.roll = inp.roll
    s.flask = inp.flask
    s.interact = inp.interact
    s.up_key = keys[pygame.K_UP]
    s.down_key = keys[pygame.K_DOWN]
    return s


if __name__ == "__main__":
    run()
