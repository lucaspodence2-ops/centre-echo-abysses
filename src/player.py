"""Joueur : physique, combat, endurance, roulade, fioles."""

import pygame

from settings import (
    FLASK_CHARGES,
    FLASK_DRINK_TIME,
    FLASK_HEAL,
    PLAYER,
)

PW, PH = 26, 44


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PW, PH)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.max_jumps = 1
        self.jumps_used = 0
        self.dead = False
        self.state = "idle"
        self.anim_t = 0.0
        self.dj_fx = 0.0
        self.abilities = set()
        self.max_hp = PLAYER["base_hp"]
        self.hp = self.max_hp
        self.max_stamina = PLAYER["base_stamina"]
        self.stamina = self.max_stamina
        self.souls = 0
        self.flasks = FLASK_CHARGES
        self.flask_max = FLASK_CHARGES
        self.roll_t = 0.0
        self.roll_dir = 1
        self.roll_speed = PLAYER["roll_speed"]
        self.iframes = 0.0
        self.hurt_t = 0.0
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.stam_delay = 0.0
        self.atk_phase = None
        self.atk_t = 0.0
        self.flask_t = 0.0

    @property
    def can_dash(self):
        return "dash" in self.abilities

    def spend_stamina(self, v):
        if self.stamina < v:
            return False
        self.stamina -= v
        self.stam_delay = PLAYER["stamina_regen_delay"]
        return True

    def move_and_collide(self, solids, dt):
        self.rect.x += int(round(self.vx * dt))
        for s in solids:
            if self.rect.colliderect(s):
                if self.vx > 0:
                    self.rect.right = s.left
                elif self.vx < 0:
                    self.rect.left = s.right
                self.vx = 0
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

    def update(self, dt, inp, game):
        self.anim_t += dt
        self.iframes = max(0.0, self.iframes - dt)
        self.hurt_t = max(0.0, self.hurt_t - dt)
        self.dj_fx = max(0.0, self.dj_fx - dt)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        if self.dead:
            if not self.on_ground:
                self.vy = min(self.vy + 2400 * dt, 1300)
                self.move_and_collide(game.room.solids, dt)
            return

        rolling = self.roll_t > 0
        attacking = self.atk_phase is not None
        drinking = self.flask_t > 0

        if self.on_ground:
            self.coyote = PLAYER["coyote_time"]
            self.jumps_used = 0
        else:
            self.coyote = max(0.0, self.coyote - dt)

        if inp.jump_pressed and not rolling and not drinking:
            self.jump_buffer = PLAYER["jump_buffer"]
        if inp.attack_pressed and not rolling and not drinking and not attacking:
            self.start_attack(game)
        if inp.roll_pressed and not drinking and (
            not rolling and (not attacking or self.atk_phase == "recover")
        ):
            self.try_roll(inp, game)
        if (
            inp.flask_pressed
            and self.flasks > 0
            and self.hp < self.max_hp
            and not drinking
            and not rolling
        ):
            self.flask_t = FLASK_DRINK_TIME

        if rolling:
            self.roll_t -= dt
            if self.roll_t <= 0:
                self.vx = 0
                self.state = "idle" if self.on_ground else "air"
            else:
                self.vx = self.roll_dir * self.roll_speed
                self.state = "roll"
        elif drinking:
            self.flask_t -= dt
            self.vx *= 0.7
            self.state = "drink"
            if self.flask_t <= 0:
                self.flasks -= 1
                self.hp = min(self.max_hp, self.hp + FLASK_HEAL)
                game.fx_drink(self.rect.center)
        elif attacking:
            self.vx *= 0.8
            self.atk_t -= dt
            if self.atk_phase == "windup" and self.atk_t <= 0:
                self.atk_phase = "active"
                self.atk_t = 0.10
                game.fx_swipe(self)
                game.sfx("attack")
            elif self.atk_phase == "active" and self.atk_t <= 0:
                self.atk_phase = "recover"
                self.atk_t = 0.16
            elif self.atk_phase == "recover" and self.atk_t <= 0:
                self.atk_phase = None
            if self.on_ground:
                self.state = "attack"
            else:
                self.state = "air"
        else:
            move = (1 if inp.right else 0) - (1 if inp.left else 0)
            self.vx = move * PLAYER["speed"]
            if move != 0:
                self.facing = move
            self.state = "idle" if self.on_ground else ("run" if move else "idle")
            if not self.on_ground:
                self.state = "air"

        if self.jump_buffer > 0 and not rolling and not drinking:
            if self.coyote > 0:
                self.vy = PLAYER["jump_vel"]
                self.jumps_used = 1
                self.coyote = 0.0
                self.jump_buffer = 0.0
                self.on_ground = False
                game.sfx("jump")
            elif self.jumps_used < self.max_jumps:
                self.vy = PLAYER["air_jump_vel"]
                self.jumps_used = self.max_jumps
                self.jump_buffer = 0.0
                self.dj_fx = 0.25
                game.fx_double_jump(self.rect.midbottom)
                game.sfx("jump")
        if not inp.jump and self.vy < -260:
            self.vy *= 0.82

        was_air = not self.on_ground
        self.vy = min(self.vy + 2200 * dt, 1300)
        self.move_and_collide(game.room.solids, dt)
        if self.on_ground and was_air:
            self.jumps_used = 0
            game.fx_land(self.rect.center)
        if self.rect.top > game.room.height + 60:
            self.take_damage(9999, 0, game, pit=True)

        self.stam_delay -= dt
        if self.stam_delay <= 0:
            self.stamina = min(
                self.max_stamina, self.stamina + PLAYER["stamina_regen"] * dt
            )

    def try_roll(self, inp, game):
        if not self.spend_stamina(PLAYER["roll_stamina"]):
            return
        self.roll_speed = PLAYER["dash_speed"] if self.can_dash else PLAYER["roll_speed"]
        self.roll_t = PLAYER["roll_time"]
        if inp.left:
            self.roll_dir = -1
        elif inp.right:
            self.roll_dir = 1
        else:
            self.roll_dir = self.facing
        self.facing = self.roll_dir
        self.iframes = max(self.iframes, PLAYER["roll_iframes"])
        self.atk_phase = None
        self.atk_t = 0.0
        game.sfx("roll")

    def start_attack(self, game):
        if not self.spend_stamina(PLAYER["attack_stamina"]):
            return
        self.atk_phase = "windup"
        self.atk_t = 0.08
        lunge = 190 if self.on_ground else 70
        self.vx = self.facing * lunge

    def attack_hitbox(self):
        if self.atk_phase != "active":
            return None
        r = pygame.Rect(0, 0, 76, 52)
        r.centery = self.rect.centery
        if self.facing > 0:
            r.left = self.rect.centerx
        else:
            r.right = self.rect.centerx
        return r

    def take_damage(self, dmg, from_dir, game, pit=False):
        if self.dead or (self.iframes > 0 and not pit):
            return False
        self.hp -= dmg
        self.iframes = PLAYER["iframes_hurt"]
        self.hurt_t = 0.3
        self.atk_phase = None
        self.atk_t = 0.0
        self.roll_t = 0.0
        if not pit:
            self.vx = 260 * (1 if from_dir >= 0 else -1)
            self.vy = -220
        game.fx_hurt(self.rect.center)
        game.sfx("hurt")
        game.cam.shake = 8
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            game.on_player_death()
        return True

    def heal_full(self):
        self.hp = self.max_hp
        self.stamina = self.max_stamina
        self.flasks = self.flask_max
        self.dead = False

    def refresh_ability(self):
        self.max_jumps = 2 if "double_jump" in self.abilities else 1
