"""Interface : barres, menus, toasts."""

import pygame

from settings import COLORS, CONTROLS_HINT


def bar(surf, x, y, w, h, ratio, color, back):
    pygame.draw.rect(surf, back, (x, y, w, h), border_radius=3)
    if ratio > 0:
        pygame.draw.rect(surf, color, (x, y, max(4, int(w * ratio)), h), border_radius=3)
    pygame.draw.rect(surf, (0, 0, 0), (x, y, w, h), 1)


def draw_hud(surf, game, font, small):
    p = game.player
    bar(surf, 24, 24, 320, 20, p.hp / p.max_hp, COLORS["hp"], COLORS["hp_back"])
    bar(surf, 24, 50, 260, 12, p.stamina / p.max_stamina, COLORS["stam"], COLORS["stam_back"])
    for i in range(p.flask_max):
        r = pygame.Rect(24 + i * 26, 70, 16, 20)
        if i < p.flasks:
            pygame.draw.rect(surf, (196, 120, 40), r, border_radius=6)
            pygame.draw.rect(surf, (90, 50, 15), r, 1, border_radius=6)
        else:
            pygame.draw.rect(surf, (40, 38, 36), r, 1, border_radius=6)
    souls_txt = font.render(str(p.souls), True, COLORS["soul"])
    label = small.render("ÂMES", True, COLORS["faded"])
    surf.blit(label, (24, 100))
    surf.blit(souls_txt, (24, 112))

    abilities = [a for a in ("double_jump", "dash") if a in p.abilities]
    if abilities:
        ax = 24
        small_txt = small.render(
            " + ".join(
                "Ailes de Cendre" if a == "double_jump" else "Passe d'Ombre"
                for a in abilities
            ),
            True, COLORS["gold"],
        )
        surf.blit(small_txt, (ax, 140))


def draw_boss_bar(surf, game, font):
    boss = game.boss
    if not boss or boss.dead or boss.state == "sleep":
        return
    name = font.render(boss.name, True, COLORS["text"])
    surf.blit(name, name.get_rect(center=(640, 620)))
    bar(surf, 240, 640, 800, 18, boss.hp / boss.max_hp, COLORS["boss"], COLORS["hp_back"])


def draw_toasts(surf, game, small):
    y = 90
    for text, ttl, color in game.toasts:
        alpha = min(1.0, ttl)
        surf_alpha = int(255 * alpha)
        txt = small.render(text, True, color)
        shadow = small.render(text, True, (0, 0, 0))
        pos = txt.get_rect(center=(640, y))
        surf.blit(shadow, (pos.x + 1, pos.y + 1))
        surf.set_alpha(surf_alpha)
        surf.blit(txt, pos)
        surf.set_alpha(255)
        y += 26


def draw_menu(surf, font, small, title, subtitle, options, selected, hint=True):
    surf.fill((8, 8, 10))
    for i in range(40):
        y = (i * 37) % 720
        x = (i * 211) % 1280
        pygame.draw.circle(surf, (24, 22, 20), (x, y), 1)
    t = font.render(title, True, COLORS["white"])
    surf.blit(t, t.get_rect(center=(640, 140)))
    if subtitle:
        s = small.render(subtitle, True, COLORS["faded"])
        surf.blit(s, s.get_rect(center=(640, 180)))
    y = 300
    for i, opt in enumerate(options):
        if opt is None:
            y += 24
            continue
        color = COLORS["gold"] if i == selected else COLORS["faded"]
        txt = font.render(opt, True, color)
        surf.blit(txt, txt.get_rect(center=(640, y)))
        if i == selected:
            pygame.draw.polygon(
                surf, COLORS["accent"], ((520, y - 8), (520, y + 8), (530, y))
            )
        y += 44
    if hint:
        h = small.render("Haut / Bas — choisir     Entrée — valider", True, COLORS["faded"])
        surf.blit(h, h.get_rect(center=(640, 680)))


def draw_help(surf, font, small):
    surf.fill((8, 8, 10))
    t = font.render("Marche à suivre, cendré...", True, COLORS["white"])
    surf.blit(t, t.get_rect(center=(640, 110)))
    y = 190
    for name, keys in CONTROLS_HINT:
        txt = small.render(name, True, COLORS["text"])
        k = small.render(keys, True, COLORS["gold"])
        surf.blit(txt, (300, y))
        surf.blit(k, (760, y))
        y += 46
    h = small.render("N'importe quelle touche pour revenir", True, COLORS["faded"])
    surf.blit(h, h.get_rect(center=(640, 660)))
