"""Ennemis, projectiles, dangers et boss (Gardien, Écho)."""

import math
import random

import pygame

from settings import ENTITY_DAMAGE, SOULS_KILL


class Enemy:
    hp = 1
    w, h = 24, 40
    walk = 0.0
    chase = 0.0
    is_boss = False
    kb_resist = 1.0

    def __init__(self, x, y):
        self.spawn_x, self.spawn_y = x, y
        self.rect = pygame.Rect(x, y, self.w, self.h)
        self.vx = 0.0
        self.vy = 0.0
        self.face = -1
        self.state = "idle"
        self.t = 0.0
        self.flash = 0.0
        self.on_ground = False
        self.dead = False
        self.dying = 0.0
        self.cd = random.uniform(0.2, 1.2)

    @property
    def max_hp(self):
        return type(self).hp

    @property
    def souls_value(self):
        return SOULS_KILL[self.etype]

    @property
    def dmg(self):
        return self.dmg_value

    def respawn(self):
        self.rect.topleft = (self.spawn_x, self.spawn_y)
        self.vx = self.vy = 0.0
        self.face = -1
        self.state = "idle"
        self.t = 0.0
        self.flash = 0.0
        self.on_ground = False
        self.dead = False
        self.dying = 0.0
        self.cd = random.uniform(0.2, 1.0)

    def move_solid(self, solids, dt):
        hit_wall = False
        self.rect.x += int(round(self.vx * dt))
        for s in solids:
            if self.rect.colliderect(s):
                if self.vx > 0:
                    self.rect.right = s.left
                else:
                    self.rect.left = s.right
                self.vx = 0
                hit_wall = True
        self.rect.y += int(round(self.vy * dt))
        self.on_ground = False
        for s in solids:
            if self.rect.colliderect(s):
                if self.vy > 0:
                    self.rect.bottom = s.top
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = s.bottom
                self.vy = 0
        return hit_wall

    def fall(self, dt):
        self.vy = min(self.vy + 2200 * dt, 1300)

    def edge_ahead(self, game):
        probe = pygame.Rect(
            self.rect.centerx + self.face * (self.rect.w // 2 + 6),
            self.rect.bottom + 2, 4, 8,
        )
        return not any(probe.colliderect(s) for s in game.room.solids)

    def take_damage(self, dmg, from_dir, game):
        if self.dead or self.dying > 0:
            return False
        self.hp -= dmg
        self.flash = 0.14
        kb = 240 * self.kb_resist
        self.vx += kb * (1 if from_dir >= 0 else -1)
        game.fx_hit(self.rect.center)
        game.sfx("hit")
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.dying = 1.6 if self.is_boss else 0.5
            game.on_enemy_killed(self)
        return True

    def update(self, dt, game):
        pass

    def damage_boxes(self):
        return []


class Walker(Enemy):
    aggro_x = 300
    aggro_y = 170
    strike_range = 50
    strike_dy = 52
    windup = 0.45
    strike_time = 0.14
    cooldown = 0.9
    strike_w = 54
    strike_h = 44

    def update(self, dt, game):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.cd -= dt
        p = game.player.rect
        aggro = (
            abs(p.centerx - self.rect.centerx) < self.aggro_x
            and abs(p.centery - self.rect.centery) < self.aggro_y
            and not game.player.dead
        )
        if self.state == "idle":
            self.vx = self.face * self.walk
            self.fall(dt)
            moved = self.move_solid(game.room.solids, dt)
            if moved or self.edge_ahead(game):
                self.face *= -1
            if aggro:
                self.state = "chase"
        elif self.state == "chase":
            dx = p.centerx - self.rect.centerx
            self.face = 1 if dx > 0 else -1
            if (
                abs(dx) < self.strike_range
                and abs(p.centery - self.rect.centery) < self.strike_dy
                and self.cd <= 0
            ):
                self.state = "windup"
                self.t = 0.0
                self.vx = 0
            elif abs(dx) > self.aggro_x + 180 or game.player.dead:
                self.state = "idle"
            else:
                self.vx = self.face * self.chase
                self.fall(dt)
                self.move_solid(game.room.solids, dt)
        elif self.state == "windup":
            self.vx = 0
            self.fall(dt)
            self.move_solid(game.room.solids, dt)
            if self.t > self.windup:
                self.state = "strike"
                self.t = 0.0
                game.sfx("attack")
        elif self.state == "strike":
            self.vx = 0
            self.fall(dt)
            self.move_solid(game.room.solids, dt)
            if self.t > self.strike_time + 0.1:
                self.state = "chase"
                self.cd = self.cooldown

    def strike_box(self):
        r = pygame.Rect(0, 0, self.strike_w, self.strike_h)
        r.centery = self.rect.centery
        if self.face > 0:
            r.left = self.rect.centerx
        else:
            r.right = self.rect.centerx
        return r

    def damage_boxes(self):
        if self.state == "strike" and self.t < self.strike_time:
            return [(self.strike_box(), self.dmg)]
        return []


class Hollow(Walker):
    etype = "hollow"
    hp = 40
    w, h = 24, 40
    walk = 60.0
    chase = 150.0
    dmg_value = 15


class Heavy(Walker):
    etype = "heavy"
    hp = 90
    w, h = 44, 56
    walk = 35.0
    chase = 105.0
    aggro_x = 330
    aggro_y = 190
    strike_range = 64
    strike_dy = 66
    windup = 0.62
    strike_time = 0.16
    cooldown = 1.1
    strike_w = 66
    strike_h = 58
    kb_resist = 0.25
    dmg_value = 25


class Archer(Enemy):
    etype = "archer"
    hp = 30
    w, h = 22, 36
    dmg_value = 12

    def update(self, dt, game):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.cd -= dt
        p = game.player.rect
        dx = p.centerx - self.rect.centerx
        dy = abs(p.centery - self.rect.centery)
        in_range = 200 < abs(dx) < 460 and dy < 200 and not game.player.dead
        too_close = abs(dx) < 130 and not game.player.dead
        if self.state == "idle":
            if too_close:
                self.face = -1 if dx > 0 else 1
                self.vx = self.face * 120
            else:
                self.vx = 0
                if abs(dx) < 460:
                    self.face = 1 if dx > 0 else -1
            if in_range and self.cd <= 0:
                self.state = "windup"
                self.t = 0.0
        elif self.state == "windup":
            self.vx = 0
            if self.t > 0.6:
                self.state = "idle"
                self.cd = 1.7
                game.spawn_projectile(
                    self.rect.centerx, self.rect.centery,
                    p.centerx, p.centery, speed=420, dmg=self.dmg,
                    color=(120, 220, 160),
                )
                game.sfx("attack")
        self.fall(dt)
        self.move_solid(game.room.solids, dt)


class Flyer(Enemy):
    etype = "flyer"
    hp = 25
    w, h = 26, 22
    dmg_value = 15

    def __init__(self, x, y):
        super().__init__(x, y)
        self.t = random.uniform(0, 6.28)

    def respawn(self):
        super().respawn()
        self.t = random.uniform(0, 6.28)

    def update(self, dt, game):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        p = game.player.rect
        if self.state == "idle":
            tx = self.spawn_x + math.sin(self.t * 0.8) * 70
            ty = self.spawn_y + math.sin(self.t * 2.1) * 26
            self.vx = (tx - self.rect.centerx) * 2.4
            self.vy = (ty - self.rect.centery) * 2.4
            if (
                math.hypot(p.centerx - self.rect.centerx, p.centery - self.rect.centery) < 250
                and not game.player.dead
            ):
                self.state = "swoop"
                self.t = 0.0
                ang = math.atan2(
                    p.centery - self.rect.centery, p.centerx - self.rect.centerx
                )
                self.vx = math.cos(ang) * 420
                self.vy = math.sin(ang) * 420
        elif self.state == "swoop":
            self.vy += 300 * dt
            if self.t > 0.75:
                self.state = "return"
                self.t = 0.0
        elif self.state == "return":
            self.vx = (self.spawn_x - self.rect.centerx) * 1.8
            self.vy = (self.spawn_y - self.rect.centery) * 1.8
            if (
                math.hypot(self.spawn_x - self.rect.centerx, self.spawn_y - self.rect.centery)
                < 30
            ):
                self.state = "idle"
        self.rect.x += int(round(self.vx * dt))
        self.rect.y += int(round(self.vy * dt))
        for s in game.room.solids:
            if self.rect.colliderect(s):
                if self.state == "swoop":
                    self.state = "return"
                    self.t = 0.0
                self.rect.clamp_ip(s.inflate(-2, -2))
                self.vx = self.vy = 0

    def damage_boxes(self):
        if self.state == "swoop":
            return [(self.rect.copy(), self.dmg)]
        return []


class Proj:
    def __init__(self, x, y, vx, vy, dmg, color, ttl=3.0, grav=0.0, r=6):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.dmg = dmg
        self.color = color
        self.ttl = ttl
        self.grav = grav
        self.r = r
        self.dead = False

    def rect(self):
        return pygame.Rect(int(self.x) - self.r, int(self.y) - self.r, self.r * 2, self.r * 2)

    def update(self, dt, game):
        self.vy += self.grav * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.ttl -= dt
        if self.ttl <= 0:
            self.dead = True
            return
        if self.rect().collidelist(game.room.solids) != -1:
            self.dead = True
            game.fx_puff(self.x, self.y, self.color)


class Shockwave(Proj):
    def __init__(self, x, y, vx, dmg):
        super().__init__(x, y, vx, 0, dmg, (255, 140, 60), ttl=1.0, r=13)

    def update(self, dt, game):
        self.x += self.vx * dt
        self.ttl -= dt
        if self.ttl <= 0:
            self.dead = True


class Hazard:
    def __init__(self, cx, y0, y1, delay, dmg, width=64):
        self.rect = pygame.Rect(cx - width // 2, y0, width, y1 - y0)
        self.delay = delay
        self.t = 0.0
        self.dmg = dmg
        self.hit_done = False
        self.active = 0.5
        self.dead = False

    def update(self, dt, game):
        self.t += dt
        if self.delay <= self.t < self.delay + self.active and not self.hit_done:
            if self.rect.colliderect(game.player.rect):
                if game.player.take_damage(self.dmg, 0, game):
                    self.hit_done = True
        if self.t > self.delay + self.active:
            self.dead = True


class Gardien(Enemy):
    hp = 650
    w, h = 64, 88
    is_boss = True
    dmg_value = 28

    def __init__(self, x, y):
        super().__init__(x, y)
        self.etype = "gardien"
        self.name = "Le Gardien de Cendre"

    @property
    def phase2(self):
        return self.hp < self.max_hp * 0.5

    def activate(self):
        self.state = "intro"
        self.t = 0.0
        self.on_ground = False

    def update(self, dt, game):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        if self.dead or self.state == "sleep":
            return
        p = game.player.rect
        mult = 1.18 if self.phase2 else 1.0
        dx = p.centerx - self.rect.centerx
        adx = abs(dx)
        if self.state == "intro":
            if self.t > 1.0:
                self.state = "idle"
                self.t = 0.0
        elif self.state == "idle":
            self.vx = 0
            self.face = 1 if dx > 0 else -1
            if self.t > (0.45 if self.phase2 else 0.6):
                if adx < 130:
                    self.state = "swing"
                    self.t = 0.0
                elif adx < 560:
                    self.state = "charge_tel"
                    self.t = 0.0
                else:
                    self.state = "leap"
                    self.t = 0.0
                    self.vy = -820
                    self.vx = max(-470, min(470, dx / 0.52))
        elif self.state == "swing":
            if self.t > 0.38 / mult:
                self.state = "swing4"
                self.t = 0.0
                game.sfx("attack")
                game.cam.shake = 4
        elif self.state == "swing4":
            if self.t > 0.32:
                self.state = "idle"
                self.t = 0.0
        elif self.state == "charge_tel":
            self.vx = 0
            self.fall(dt)
            self.move_solid(game.room.solids, dt)
            if self.t > 0.5 / mult:
                self.state = "charge"
                self.t = 0.0
                self.vx = 700 * (1 if dx > 0 else -1)
        elif self.state == "charge":
            self.fall(dt)
            wall_hit = self.move_solid(game.room.solids, dt)
            if wall_hit and self.on_ground:
                self.state = "stun"
                self.t = 0.0
                game.cam.shake = 11
                game.sfx("hit")
            elif self.t > 1.1:
                self.state = "idle"
                self.t = 0.0
                self.vx = 0
            return
        elif self.state == "stun":
            self.vx = 0
            self.fall(dt)
            self.move_solid(game.room.solids, dt)
            if self.t > 1.3:
                self.state = "idle"
                self.t = 0.0
        elif self.state == "leap":
            self.vy = min(self.vy + 1900 * dt, 1300)
            self.move_solid(game.room.solids, dt)
            if self.on_ground and self.t > 0.15:
                self.state = "idle"
                self.t = 0.0
                game.cam.shake = 10
                game.sfx("hit")
                floor_y = self.rect.bottom
                for sgn in (-1, 1):
                    game.projectiles.append(
                        Shockwave(
                            self.rect.centerx + sgn * 44, floor_y - 16, sgn * 330,
                            ENTITY_DAMAGE["gardien_slam"],
                        )
                    )
                    game.fx_slam(self.rect.centerx + sgn * 40, floor_y)
            return
        self.face = 1 if dx > 0 else -1
        self.fall(dt)
        self.move_solid(game.room.solids, dt)

    def _swing_box(self):
        r = pygame.Rect(0, 0, 96, 82)
        r.centery = self.rect.centery
        if self.face > 0:
            r.left = self.rect.centerx
        else:
            r.right = self.rect.centerx
        return r

    def damage_boxes(self):
        out = []
        if self.state == "swing" and self.t > 0.2:
            out.append((self._swing_box(), ENTITY_DAMAGE["gardien_swing"]))
        if self.state == "swing4" and self.t < 0.14:
            out.append((self._swing_box(), ENTITY_DAMAGE["gardien_swing"]))
        if self.state == "charge":
            out.append((self.rect.copy(), ENTITY_DAMAGE["gardien_charge"]))
        return out


class Echo(Enemy):
    hp = 950
    w, h = 56, 72
    is_boss = True
    dmg_value = 16

    def __init__(self, x, y):
        super().__init__(x, y)
        self.etype = "echo"
        self.name = "L'Écho des Abysses"
        self.anchors = [(380, 300), (760, 230), (1150, 330), (1560, 250), (1960, 320)]
        self.visible = True

    @property
    def phase2(self):
        return self.hp < self.max_hp * 0.55

    def activate(self):
        self.state = "appear"
        self.t = 0.0

    def update(self, dt, game):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        if self.dead or self.state == "sleep":
            return
        speed_k = 0.75 if self.phase2 else 1.0
        if self.state == "appear":
            self.visible = True
            if self.t > 0.45 * speed_k:
                self.state = "cast"
                self.t = 0.0
                self.pick_pattern(game)
        elif self.state == "cast":
            if self.t > 1.15 * speed_k:
                self.state = "vanish"
                self.t = 0.0
        elif self.state == "vanish":
            self.visible = False
            if self.t > 0.4:
                anchor = random.choice(self.anchors)
                self.rect.center = anchor
                self.state = "appear"
                self.t = 0.0
                game.fx_teleport(*anchor)

    def pick_pattern(self, game):
        p = game.player.rect
        roll = random.random()
        cx, cy = self.rect.center
        if self.phase2 and roll < 0.35:
            for i in range(12):
                ang = i * math.pi / 6
                game.projectiles.append(
                    Proj(cx, cy, math.cos(ang) * 260, math.sin(ang) * 260,
                         ENTITY_DAMAGE["echo_burst"], (170, 90, 220), ttl=3.2, r=7)
                )
            game.sfx("attack")
        elif roll < 0.55:
            base = math.atan2(p.centery - cy, p.centerx - cx)
            for off in (-0.42, -0.21, 0.0, 0.21, 0.42):
                game.projectiles.append(
                    Proj(cx, cy, math.cos(base + off) * 320, math.sin(base + off) * 320,
                         ENTITY_DAMAGE["echo_bolt"], (170, 90, 220), ttl=4.0, r=7)
                )
            game.sfx("attack")
        else:
            for _ in range(4):
                hz_x = p.centerx + random.choice((-220, -80, 80, 220))
                game.hazards.append(
                    Hazard(hz_x, 60, game.floor_y(), 0.85, ENTITY_DAMAGE["echo_ash"])
                )
            game.sfx("fire")

    def damage_boxes(self):
        if self.visible and self.state == "cast":
            return [(self.rect.copy(), ENTITY_DAMAGE["echo_bolt"])]
        return []


ENEMY_TYPES = {
    "hollow": Hollow,
    "heavy": Heavy,
    "archer": Archer,
    "flyer": Flyer,
}

BOSS_TYPES = {
    "gardien": Gardien,
    "echo": Echo,
}
