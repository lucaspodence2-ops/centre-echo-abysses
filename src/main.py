"""Cendre — L'Écho des Abysses
Souls-like metroidvania minimal en pygame. `python -m src.main` pour jouer.
"""

import math
import random

import pygame

from enemies import BOSS_TYPES, ENEMY_TYPES
from player import Player
from rooms import build_rooms
import audio
import savedata
from settings import (
    COLORS,
    ENTITY_DAMAGE,
    HP_PER_VIGOR,
    LEVEL_BASE_COST,
    LEVEL_GROWTH,
    PLAYER,
    STAM_PER_ENDURANCE,
    TILE,
    WS_HEIGHT,
    WS_WIDTH,
)
from world import Camera, Room, find_exit


class InputState:
    __slots__ = (
        "left", "right", "jump", "jump_pressed", "attack", "attack_pressed",
        "roll", "roll_pressed", "flask", "flask_pressed", "interact",
        "interact_pressed", "up_pressed", "down_pressed", "confirm_pressed",
        "pause_pressed", "escape",
    )

    def __init__(self):
        for name in self.__slots__:
            setattr(self, name, False)


def build_input(keys, prev):
    inp = InputState()
    left = keys[pygame.K_q] or keys[pygame.K_a] or keys[pygame.K_LEFT]
    right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
    jump = (
        keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_z]
        or keys[pygame.K_UP]
    )
    attack = keys[pygame.K_j] or keys[pygame.K_x]
    roll = keys[pygame.K_l] or keys[pygame.K_c]
    flask = keys[pygame.K_k] or keys[pygame.K_v]
    interact = keys[pygame.K_e] or keys[pygame.K_RETURN]
    inp.left, inp.right, inp.jump = left, right, jump
    inp.attack, inp.roll, inp.flask, inp.interact = attack, roll, flask, interact
    pc = prev is not None
    inp.jump_pressed = jump and not (pc and prev.jump)
    inp.attack_pressed = attack and not (pc and prev.attack)
    inp.roll_pressed = roll and not (pc and prev.roll)
    inp.flask_pressed = flask and not (pc and prev.flask)
    inp.interact_pressed = interact and not (pc and prev.interact)
    inp.up_pressed = keys[pygame.K_UP] and not (pc and getattr(prev, "up_key", False))
    inp.down_pressed = keys[pygame.K_DOWN] and not (pc and getattr(prev, "down_key", False))
    inp.confirm_pressed = interact and not (pc and prev.interact)
    inp.escape = keys[pygame.K_ESCAPE]
    return inp


def _mk_proj(x, y, vx, vy, dmg, color, ttl=3.0, r=6):
    from enemies import Proj
    return Proj(x, y, vx, vy, dmg, color, ttl=ttl, r=r)


def level_cost(n):
    return int(LEVEL_BASE_COST * (LEVEL_GROWTH ** n))


class Game:
    def __init__(self, screen, enable_audio=True):
        self.screen = screen
        pygame.font.init()
        self.font = pygame.font.SysFont("Georgia,DejaVuSerif,dejavuserif", 30)
        self.big = pygame.font.SysFont("Georgia,DejaVuSerif,dejavuserif", 64, bold=True)
        self.small = pygame.font.SysFont("Georgia,DejaVuSerif,dejavuserif", 20)
        self.audio_on = enable_audio
        if enable_audio:
            audio.init()
        self.room_defs = build_rooms()
        self.rooms = {rid: Room(rid, d) for rid, d in self.room_defs.items()}
        self.toasts = []
        self.particles = []
        self.ambient = []
        self.blood = None
        self.state = "title"
        self.menu_idx = 0
        self.menu_options = None
        self.menu_options_kind = None
        self.death_t = 0.0
        self.victory_t = 0.0
        self.flash_t = 0.0
        self.banner_t = 0.0
        self.playtime = 0.0
        self.title_t = 0.0
        self.player = None
        self.cam = None
        self.grant_queue = None
        self.active_fog = None
        self.saved = None
        self.deaths = 0
        self.tutos = set()
        self.near_fire = False
        self.return_state = "title"

    def sfx(self, name):
        if not self.audio_on:
            return
        try:
            audio.play(name)
        except pygame.error:
            pass

    def toast(self, text, color=COLORS["text"], ttl=3.0):
        self.toasts.append([text, ttl, color])
        if len(self.toasts) > 3:
            self.toasts.pop(0)

    def new_game(self):
        savedata.delete_save()
        self.player = Player(100, 0)
        self.player.rect.bottom = 18 * TILE
        self.vigor = 0
        self.endurance = 0
        self.bosses_dead = set()
        self.blood = None
        self.deaths = 0
        self.playtime = 0.0
        self.respawn_point = ("crypt", (8 * TILE, 17 * TILE))
        self.tutos = set()
        self.death_t = 0.0
        self.victory_t = 0.0
        self.enter_room("crypt", "left")
        self._atk_hit = set()
        self.banner_t = 3.5
        self.toast("Les cendres se souviennent de toi...", COLORS["gold"], 4.5)
        self.state = "play"

    def load_game_at(self, data):
        self.player = Player(100, 0)
        self.player.souls = data["souls"]
        self.vigor = data["vigor"]
        self.endurance = data["endurance"]
        self.player.max_hp = PLAYER["base_hp"] + self.vigor * HP_PER_VIGOR
        self.player.hp = self.player.max_hp
        self.player.max_stamina = PLAYER["base_stamina"] + self.endurance * STAM_PER_ENDURANCE
        self.player.stamina = self.player.max_stamina
        self.player.abilities = set(data["abilities"])
        self.player.refresh_ability()
        self.bosses_dead = set(data["bosses_dead"])
        self.deaths = data["deaths"]
        self.playtime = data["playtime"]
        self.blood = None
        rid = data["bonfire"] or "crypt"
        room = self.rooms.get(rid) or self.rooms["crypt"]
        pos = room.bonfires[0] if room.bonfires else (8 * TILE, 17 * TILE)
        self.respawn_point = (room.rid, pos)
        self.enter_room(room.rid, "left")
        self.player.rect.centerx = pos[0] + TILE // 2
        self.player.rect.bottom = pos[1] + TILE
        self._settle()
        self.banner_t = 3.0
        self.toast("La cendre reprend votre trace...", COLORS["gold"], 3.5)
        self.state = "play"

    def save_game(self):
        data = {
            "vigor": self.vigor,
            "endurance": self.endurance,
            "souls": self.player.souls,
            "abilities": sorted(self.player.abilities),
            "bosses_dead": sorted(self.bosses_dead),
            "bonfire": self.respawn_point[0],
            "last_room": self.current_rid,
            "deaths": self.deaths,
            "playtime": self.playtime,
        }
        savedata.write_save(data)

    def enter_room(self, rid, side, along=None):
        room = self.rooms[rid]
        self.room = room
        self.current_rid = rid
        self.enemies = []
        for et, x, y in room.spawns:
            self.enemies.append(ENEMY_TYPES[et](x, y + TILE - ENEMY_TYPES[et].h))
        self.projectiles = []
        self.hazards = []
        self._atk_hit = set()
        self.boss = None
        self.active_fog = None
        if room.boss and rid not in self.bosses_dead:
            btype = BOSS_TYPES[room.boss]
            if rid == "sanctuary":
                bx, by = 36 * TILE, 18 * TILE - btype.h
            else:
                bx, by = 41 * TILE, 9 * TILE
            self.boss = btype(bx, by)
            self.boss.state = "sleep"
        r = self.player.rect
        if side == "left":
            r.x = 10
            if along is not None:
                r.centery = along
        elif side == "right":
            r.right = room.width - 10
            if along is not None:
                r.centery = along
        elif side == "top":
            ex = find_exit(room, "top")
            cx = room.width // 2
            if ex:
                cx = (ex.span[0] + ex.span[1] + 1) // 2 * TILE
            r.centerx = cx
            r.y = 6
            self.player.vy = 0
        elif side == "bottom":
            ex = find_exit(room, "bottom")
            cx = room.width // 2
            if ex:
                cx = (ex.span[0] + ex.span[1] + 1) // 2 * TILE + 3 * TILE
            r.centerx = cx
            r.bottom = 18 * TILE
            self.player.vy = 0
        r.x = max(4, min(room.width - r.w - 4, r.x))
        r.y = max(4, min(room.height - r.h - 4, r.y))
        self._settle()
        if self.cam is None:
            self.cam = Camera(room)
        else:
            self.cam.set_room(room)
            self.cam.snap(r)
        self.ambient = []
        self.banner_t = 2.2

    def floor_y(self):
        return 18 * TILE + 8

    def _settle(self):
        room = self.room
        r = self.player.rect
        if r.collidelist(room.solids) == -1:
            return
        x0, y0 = r.x, r.y
        for dx in (9, 18, 36, 72, 120, 200, 300):
            if x0 + dx <= room.width - r.w - 4:
                r.x = x0 + dx
                if r.collidelist(room.solids) == -1:
                    return
            r.x = x0 - dx
            if r.collidelist(room.solids) == -1 and r.x > 2:
                return
        r.x = x0
        for dy in (9, 18, 36, 60, 90, 130, 180):
            r.y = y0 + dy
            if r.collidelist(room.solids) == -1:
                return
            r.y = y0 - dy
            if r.collidelist(room.solids) == -1 and r.y > 2:
                return
        r.x, r.y = x0, y0

    def on_player_death(self):
        self.deaths += 1
        if self.player.souls > 0:
            self.blood = {
                "rid": self.current_rid,
                "x": self.player.rect.centerx,
                "y": min(self.player.rect.centery, 18 * TILE - 8),
                "amount": self.player.souls,
            }
            self.player.souls = 0
        self.sfx("die")
        self.death_t = 2.8

    def respawn(self):
        rid, pos = self.respawn_point
        self.player.heal_full()
        self.player.vx = self.player.vy = 0
        self.enter_room(rid, "left")
        self.player.rect.centerx = pos[0] + TILE // 2
        self.player.rect.bottom = pos[1] + TILE
        self._settle()
        self.banner_t = 1.5
        self.toast("Ranimé au feu de cendre.", COLORS["gold"])

    def grant_ability(self, ability):
        if ability in self.player.abilities:
            return
        self.player.abilities.add(ability)
        self.player.refresh_ability()
        self.flash_t = 0.8
        self.sfx("pickup")
        if ability == "double_jump":
            self.toast(
                "AILES DE CENDRE — sautez de nouveau en l'air (Espace)",
                COLORS["gold"], 5.5,
            )
        elif ability == "dash":
            self.toast(
                "PASSE D'OMBRE — la roulade traverse l'obscurité (L)",
                COLORS["gold"], 5.5,
            )
        self.save_game()

    def on_enemy_killed(self, enemy):
        self.player.souls += enemy.souls_value
        self.fx_death(enemy.rect.center)
        if enemy.is_boss:
            self.bosses_dead.add(self.current_rid)
            reward = self.room_defs[self.current_rid].get("reward")
            if reward:
                self.grant_queue = reward
                self.toast("La volonté du Gardien se brise...", COLORS["gold"], 4.0)
            if self.current_rid == "abyss":
                self.victory_t = 2.4

    def spawn_projectile(self, x, y, tx, ty, speed=420, dmg=10, color=(120, 220, 160)):
        ang = math.atan2(ty - y, tx - x)
        self.projectiles.append(
            _mk_proj(x, y, math.cos(ang) * speed, math.sin(ang) * speed, dmg, color)
        )

    def update_particles(self, dt):
        for part in self.particles:
            part["x"] += part["vx"] * dt
            part["y"] += part["vy"] * dt
            part["vy"] += part.get("grav", 0) * dt
            part["ttl"] -= dt
        self.particles = [p for p in self.particles if p["ttl"] > 0]

    def particle_burst(self, x, y, color, n=8, speed=120, ttl=0.5, grav=0.0, size=3):
        for _ in range(n):
            self.particles.append({
                "x": x + random.uniform(-6, 6),
                "y": y + random.uniform(-6, 6),
                "vx": random.uniform(-speed, speed),
                "vy": random.uniform(-speed, speed),
                "ttl": ttl * random.uniform(0.6, 1.2),
                "color": color,
                "grav": grav,
                "size": size,
            })

    def update_ambient(self, dt):
        theme = self.room.theme["particle"]
        if len(self.ambient) < 56:
            self.ambient.append({
                "x": self.cam.x + random.uniform(-100, WS_WIDTH + 100),
                "y": self.cam.y + random.uniform(-100, WS_HEIGHT + 100),
                "size": random.uniform(1.5, 3.5),
                "phase": random.uniform(0, 6.28),
            })
        for a in self.ambient:
            if theme == "ember":
                a["y"] -= (14 + 8 * math.sin(a["phase"])) * dt
                a["x"] += math.sin(a["phase"] * 1.7) * 22 * dt
            else:
                a["y"] += (10 + 6 * math.sin(a["phase"])) * dt
                a["x"] += math.cos(a["phase"] * 1.3) * 16 * dt
            a["phase"] += dt
            if a["y"] < self.cam.y - 120 or a["y"] > self.cam.y + WS_HEIGHT + 120:
                a["y"] = self.cam.y + random.uniform(0, WS_HEIGHT)
                a["x"] = self.cam.x + random.uniform(-60, WS_WIDTH + 60)
            if a["x"] < self.cam.x - 120 or a["x"] > self.cam.x + WS_WIDTH + 120:
                a["x"] = self.cam.x + random.uniform(0, WS_WIDTH)
                a["y"] = self.cam.y + random.uniform(0, WS_HEIGHT)

    def fx_swipe(self, player):
        pass

    def fx_hit(self, center):
        self.particle_burst(center[0], center[1], (255, 200, 120), 10, 160, 0.4, 300)
        self.cam.shake = max(self.cam.shake, 4)

    def fx_hurt(self, center):
        self.particle_burst(center[0], center[1], (200, 40, 40), 14, 190, 0.5, 350)

    def fx_death(self, center):
        self.particle_burst(center[0], center[1], (220, 190, 120), 26, 190, 0.9, -30, 4)

    def fx_land(self, center):
        self.particle_burst(center[0], center[1] + 14, (110, 110, 110), 5, 60, 0.3, 120, 2)

    def fx_double_jump(self, pos):
        self.particle_burst(pos[0], pos[1], (255, 170, 90), 16, 130, 0.5, -60)

    def fx_drink(self, center):
        self.particle_burst(center[0], center[1], (255, 140, 60), 12, 90, 0.6, -140)

    def fx_puff(self, x, y, color):
        self.particle_burst(x, y, color, 6, 90, 0.35, 0, 2)

    def fx_slam(self, x, y):
        self.particle_burst(x, y, (255, 150, 60), 18, 160, 0.5, -200, 4)

    def fx_teleport(self, x, y):
        self.particle_burst(x, y, (170, 90, 220), 18, 130, 0.6, 0, 1)

    def update_bonfire_fx(self):
        for px, py in self.room.bonfires:
            sx, sy = px + TILE // 2, py + TILE - 6
            if abs(sx - (self.cam.x + WS_WIDTH / 2)) > WS_WIDTH:
                continue
            if random.random() < 0.5:
                self.particles.append({
                    "x": sx + random.uniform(-7, 7),
                    "y": sy,
                    "vx": random.uniform(-14, 14),
                    "vy": random.uniform(-70, -30),
                    "ttl": random.uniform(0.5, 1.1),
                    "color": random.choice([(255, 150, 50), (255, 200, 80), (200, 80, 30)]),
                    "grav": -40,
                    "size": random.uniform(2, 4),
                })

    def window_solids(self):
        solids = list(self.room.solids)
        self.active_fog = None
        if self.boss and not self.boss.dead and self.boss.dying <= 0 and self.boss.state != "sleep":
            if self.current_rid == "sanctuary":
                fog = pygame.Rect(0, 64, 96, 18 * TILE - 64)
            else:
                ex = find_exit(self.room, "top")
                span = ex.span if ex else (24, 27)
                fog = pygame.Rect(span[0] * TILE, 0, (span[1] - span[0] + 1) * TILE, 5 * TILE)
            if not fog.colliderect(self.player.rect):
                solids.append(fog)
                self.active_fog = fog
        return solids

    def check_transitions(self, inp):
        room = self.room
        r = self.player.rect
        for ex in room.exits:
            a, b = ex.span
            lo, hi = a * TILE - 8, b * TILE + TILE + 8
            need_block = ex.need and ex.need not in self.player.abilities
            crossed = False
            if ex.side == "left" and r.right < 8:
                crossed = True
                if need_block:
                    r.left = 10
                else:
                    self.do_transition(ex, "right")
                    return
            elif ex.side == "right" and r.left > room.width - 8:
                crossed = True
                if need_block:
                    r.right = room.width - 10
                else:
                    self.do_transition(ex, "left")
                    return
            elif ex.side == "top" and r.top < -6 and lo <= r.centerx <= hi:
                crossed = True
                if need_block:
                    r.top = 4
                    self.player.vy = 60
                else:
                    self.do_transition(ex, "bottom")
                    return
            elif ex.side == "bottom" and r.top > room.height - 4 and lo <= r.centerx <= hi + TILE:
                crossed = True
                if need_block:
                    r.bottom = room.height - 2 * TILE
                    self.player.vy = -240
                else:
                    self.do_transition(ex, "top")
                    return
            if crossed and need_block:
                self.block_toast(ex.need)

    def block_toast(self, need):
        if self._block_cd <= 0:
            if need == "double_jump":
                self.toast(
                    "La corniche est hors de portée... (il faut sauter plus loin)",
                    COLORS["faded"], 2.5,
                )
            else:
                self.toast("Un seuil vous retient. (capacité requise)", COLORS["faded"], 2.5)
            self._block_cd = 2.0

    def do_transition(self, ex, enter_side):
        target_defs = self.room_defs[ex.to_room]
        _ = target_defs
        along = self.player.rect.centery
        self.enter_room(ex.to_room, enter_side, along)
        self.sfx("fire")

    def hazard_update(self, dt):
        for hz in self.hazards:
            hz.update(dt, self)
        self.hazards = [h for h in self.hazards if not h.dead]

    def tutorial(self):
        if self.current_rid != "crypt":
            return
        x = self.player.rect.centerx
        if x > 60 and "move" not in self.tutos:
            self.tutos.add("move")
            self.toast("Q / D — se déplacer     Espace — sauter", COLORS["faded"], 6.0)
        if x > 500 and "atk" not in self.tutos:
            self.tutos.add("atk")
            self.toast("J — attaquer     L — roulade (esquive !)", COLORS["faded"], 6.0)
        if x > 900 and "fire" not in self.tutos:
            self.tutos.add("fire")
            self.toast("E — se reposer au feu de cendre", COLORS["faded"], 6.0)

    def step_title(self, dt, inp):
        saved = self.saved or savedata.load_save()
        opts = ["Nouvelle partie"]
        if saved:
            opts.append("Continuer")
        opts += ["Contrôles", "Quitter"]
        self.menu_options = opts
        self.menu_idx = min(max(0, self.menu_idx), len(opts) - 1)
        if inp.down_pressed:
            self.menu_idx = (self.menu_idx + 1) % len(self.menu_options)
        if inp.up_pressed:
            self.menu_idx = (self.menu_idx - 1) % len(self.menu_options)
        if inp.confirm_pressed:
            choice = self.menu_options[self.menu_idx]
            if choice == "Nouvelle partie":
                self.new_game()
            elif choice == "Continuer":
                data = savedata.load_save()
                if data:
                    self.load_game_at(data)
                else:
                    self.new_game()
            elif choice == "Contrôles":
                self.state = "help"
            elif choice == "Quitter":
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def title_options(self):
        if self.menu_options is None:
            self.step_title(0, InputState())
        return self.menu_options

    def bonfire_options(self):
        cost = level_cost(self.vigor + self.endurance)
        return [
            "Se reposer (soigne, ranime les ennemis, sauvegarde)",
            f"Renforcer la vigueur : +{HP_PER_VIGOR} PV   ({cost} âmes)",
            f"Forger l'endurance : +{STAM_PER_ENDURANCE}   ({cost} âmes)",
            "Reprendre la marche",
        ]

    def do_bonfire_choice(self, idx):
        if idx == 0:
            self.player.heal_full()
            self.player.flasks = self.player.flask_max
            self.respawn_point = (self.current_rid, self.fire_menu_pos)
            for e in self.enemies:
                if not e.is_boss:
                    e.respawn()
            if self.boss and not self.boss.dead:
                btype = BOSS_TYPES[self.room.boss]
                if self.current_rid == "sanctuary":
                    bx, by = 36 * TILE, 18 * TILE - btype.h
                else:
                    bx, by = 41 * TILE, 9 * TILE
                self.boss = btype(bx, by)
                self.boss.state = "sleep"
            for proj in self.projectiles:
                proj.dead = True
            self.hazards = []
            self.save_game()
            self.sfx("fire")
            self.toast("Repos accepté. La cendre se souvient.", COLORS["gold"], 3.5)
        elif idx in (1, 2):
            spent = level_cost(self.vigor + self.endurance)
            if self.player.souls >= spent:
                self.player.souls -= spent
                if idx == 1:
                    self.vigor += 1
                    self.player.max_hp += HP_PER_VIGOR
                    self.player.hp += HP_PER_VIGOR
                else:
                    self.endurance += 1
                    self.player.max_stamina += STAM_PER_ENDURANCE
                    self.player.stamina += STAM_PER_ENDURANCE
                self.save_game()
                self.sfx("pickup")
                self.toast("Votre essence s'épaissit d'âmes.", COLORS["gold"])
            else:
                self.toast("Pas assez d'âmes...", COLORS["faded"])
        if idx == 3 or idx == 0:
            self.state = "play"
        else:
            self.state = "play"

    def _fog_rect(self):
        if not (self.boss and not self.boss.dead and self.boss.dying <= 0
                and self.boss.state != "sleep"):
            return None
        if self.current_rid == "sanctuary":
            return pygame.Rect(0, 64, 96, 18 * TILE - 64)
        ex = find_exit(self.room, "top")
        span = ex.span if ex else (24, 27)
        return pygame.Rect(span[0] * TILE, 0, (span[1] - span[0] + 1) * TILE, 5 * TILE)

    def step_play(self, dt, inp):
        fog = self._fog_rect()
        if fog is not None and not fog.colliderect(self.player.rect):
            self.room.solids.append(fog)
            self.active_fog = fog
        else:
            self.active_fog = None
        try:
            self._step_play_body(dt, inp)
        finally:
            if self.active_fog is not None:
                try:
                    self.room.solids.remove(self.active_fog)
                except ValueError:
                    pass
            self.active_fog = None

    def _step_play_body(self, dt, inp):
        self.playtime += dt
        self.update_ambient(dt)

        prev_atk = self.player.atk_phase
        self.player.update(dt, inp, self)
        if prev_atk == "windup" and self.player.atk_phase == "active":
            self._atk_hit = set()

        for e in self.enemies:
            if e.dead:
                e.dying = max(0.0, e.dying - dt)
            else:
                e.update(dt, self)
        self.enemies = [e for e in self.enemies if not (e.dead and e.dying <= 0)]

        if self.boss:
            if self.boss.dead:
                self.boss.dying = max(0.0, self.boss.dying - dt)
            else:
                if self.boss.state == "sleep":
                    trigger = self.room_defs[self.current_rid]["trigger_x"]
                    if self.player.rect.centerx > trigger and not self.player.dead:
                        self.boss.activate()
                        self.sfx("roar")
                        self.toast(self.boss.name, COLORS["white"], 3.2)
                self.boss.update(dt, self)

        if self.grant_queue and self.boss is not None and self.boss.dead and self.boss.dying <= 0:
            self.grant_ability(self.grant_queue)
            self.grant_queue = None

        if self.victory_t > 0:
            self.victory_t -= dt
            if self.victory_t <= 0:
                self.state = "victory"
                self.sfx("victory")
                self.save_game()
                return

        self.check_transitions(inp)

        hb = self.player.attack_hitbox()
        if hb:
            for e in self.enemies:
                if not e.dead and hb.colliderect(e.rect) and id(e) not in self._atk_hit:
                    self._atk_hit.add(id(e))
                    e.take_damage(PLAYER["attack_damage"], self.player.facing, self)
            if self.boss and not self.boss.dead and hb.colliderect(self.boss.rect) \
                    and id(self.boss) not in self._atk_hit:
                self._atk_hit.add(id(self.boss))
                self.boss.take_damage(PLAYER["attack_damage"], self.player.facing, self)
        for e in self.enemies:
            if e.dead:
                continue
            for box, dmg in e.damage_boxes():
                if box.colliderect(self.player.rect):
                    dx = self.player.rect.centerx - e.rect.centerx
                    self.player.take_damage(dmg, 1 if dx >= 0 else -1, self)
        if self.boss and not self.boss.dead:
            for box, dmg in self.boss.damage_boxes():
                if box.colliderect(self.player.rect):
                    dx = self.player.rect.centerx - self.boss.rect.centerx
                    self.player.take_damage(dmg, 1 if dx >= 0 else -1, self)

        for proj in self.projectiles:
            if proj.dead:
                continue
            proj.update(dt, self)
            if not proj.dead and proj.rect().colliderect(self.player.rect):
                if self.player.take_damage(proj.dmg, 1 if proj.vx >= 0 else -1, self):
                    proj.dead = True
                    self.fx_puff(proj.x, proj.y, proj.color)
        self.projectiles = [p for p in self.projectiles if not p.dead]

        self.hazard_update(dt)

        for spike in self.room.spikes:
            if spike.colliderect(self.player.rect) and not self.player.dead:
                if self.player.take_damage(ENTITY_DAMAGE["spike"], 0, self):
                    self.player.vy = -460
                break

        if self.blood and self.blood.get("rid") == self.current_rid:
            if math.hypot(
                self.player.rect.centerx - self.blood["x"],
                self.player.rect.centery - self.blood["y"],
            ) < 48:
                amt = self.blood["amount"]
                self.player.souls += amt
                self.blood = None
                self.toast(f"{amt} âmes récupérées.", COLORS["soul"], 3.0)
                self.sfx("pickup")

        if (
            self.room.item
            and self.room.item not in self.player.abilities
            and self.room.item_pos
        ):
            ix, iy = self.room.item_pos
            if math.hypot(self.player.rect.centerx - ix, self.player.rect.centery - iy) < 46:
                self.grant_ability(self.room.item)

        self.update_bonfire_fx()

        self.near_fire = False
        for px, py in self.room.bonfires:
            fx = px + TILE // 2
            if (
                abs(self.player.rect.centerx - fx) < 52
                and abs(self.player.rect.bottom - (py + TILE)) < 60
            ):
                self.near_fire = True
                self.fire_menu_pos = (fx, py)
        if self.near_fire and inp.interact_pressed and not self.player.dead:
            self.state = "bonfire"
            self.menu_idx = 0

        self.cam.follow(self.player.rect, dt)
        self.tutorial()

    def step_pause(self, dt, inp):
        if inp.escape or inp.confirm_pressed:
            self.state = "play"

    def step(self, dt, inp):
        self.title_t += dt
        for t in self.toasts:
            t[1] -= dt
        self.toasts = [t for t in self.toasts if t[1] > 0]
        self.flash_t = max(0.0, self.flash_t - dt)
        self.banner_t = max(0.0, self.banner_t - dt)
        self._block_cd = max(0.0, getattr(self, "_block_cd", 0.0) - dt)
        self.update_particles(dt)

        if self.state == "title":
            self.step_title(dt, inp)
            return
        if self.state == "help":
            return
        if self.state == "pause":
            self.step_pause(dt, inp)
            return
        if self.state == "victory":
            return
        if self.player is None:
            return
        if self.death_t > 0:
            self.death_t -= dt
            self.player.anim_t += dt
            if self.death_t <= 0:
                self.respawn()
            return
        if self.state == "bonfire":
            if inp.down_pressed:
                self.menu_idx = (self.menu_idx + 1) % 4
            elif inp.up_pressed:
                self.menu_idx = (self.menu_idx - 1) % 4
            elif inp.confirm_pressed:
                self.do_bonfire_choice(self.menu_idx)
            return
        self.step_play(dt, inp)
