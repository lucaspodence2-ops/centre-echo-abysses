"""Monde : salles en tilemap, sorties, thèmes et caméra."""

import random

import pygame

from settings import TILE

SOLID = "#"
AIR = "."
SPIKE = "^"

ENEMY_CHARS = {"1": "hollow", "2": "archer", "3": "flyer", "4": "heavy"}

THEMES = {
    "crypt": {
        "sky_top": (16, 18, 26),
        "sky_bot": (30, 28, 36),
        "silhouette": (22, 22, 32),
        "tile_a": (52, 54, 66),
        "tile_b": (38, 40, 50),
        "particle": "dust",
        "fog": (40, 44, 60),
    },
    "hall": {
        "sky_top": (28, 22, 16),
        "sky_bot": (46, 34, 22),
        "silhouette": (36, 28, 20),
        "tile_a": (78, 62, 46),
        "tile_b": (56, 44, 32),
        "particle": "ember",
        "fog": (60, 44, 28),
    },
    "sanctuary": {
        "sky_top": (34, 12, 16),
        "sky_bot": (54, 20, 24),
        "silhouette": (44, 16, 20),
        "tile_a": (92, 52, 52),
        "tile_b": (64, 36, 38),
        "particle": "ember",
        "fog": (90, 30, 40),
    },
    "tower": {
        "sky_top": (18, 16, 32),
        "sky_bot": (38, 32, 58),
        "silhouette": (26, 24, 44),
        "tile_a": (76, 72, 100),
        "tile_b": (52, 50, 74),
        "particle": "ash",
        "fog": (60, 56, 96),
    },
    "cave": {
        "sky_top": (10, 20, 24),
        "sky_bot": (18, 36, 40),
        "silhouette": (14, 28, 32),
        "tile_a": (48, 82, 82),
        "tile_b": (34, 60, 60),
        "particle": "dust",
        "fog": (28, 60, 64),
    },
    "abyss": {
        "sky_top": (16, 6, 10),
        "sky_bot": (34, 8, 14),
        "silhouette": (26, 8, 12),
        "tile_a": (86, 44, 52),
        "tile_b": (58, 30, 36),
        "particle": "ash",
        "fog": (110, 20, 40),
    },
}


class RoomExit:
    def __init__(self, side, span, to_room, to_side, need=None):
        self.side = side
        self.span = span
        self.to_room = to_room
        self.to_side = to_side
        self.need = need


class Room:
    def __init__(self, rid, data):
        self.rid = rid
        self.name = data["name"]
        self.boss = data.get("boss")
        self.item = data.get("item")
        self.trigger_x = data.get("trigger_x")
        grid = _normalize_grid(data["map"])
        self.grid = grid
        self.rows = len(grid)
        self.cols = max(len(r) for r in grid)
        self.width = self.cols * TILE
        self.height = self.rows * TILE
        self.theme = THEMES[data["theme"]]
        tiles = []
        self.spikes = []
        self.spawns = []
        self.bonfires = []
        self.item_pos = None
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                px, py = x * TILE, y * TILE
                if ch == SOLID:
                    tiles.append(pygame.Rect(px, py, TILE, TILE))
                elif ch == SPIKE:
                    self.spikes.append(pygame.Rect(px + 4, py + 12, TILE - 8, TILE - 12))
                elif ch in ENEMY_CHARS:
                    self.spawns.append((ENEMY_CHARS[ch], px, py))
                elif ch == "B":
                    self.bonfires.append((px, py))
                elif ch == "O":
                    self.item_pos = (px + TILE // 2, py + TILE // 2)
        self.solids = _merge_rects(tiles)
        self.exits = [
            RoomExit(e["side"], e["span"], e["to"], e["to_side"], e.get("need"))
            for e in data.get("exits", [])
        ]
        rand = random.Random(rid)
        self.pillars = []
        for _ in range(9):
            px = rand.uniform(0, self.width)
            pw = rand.uniform(30, 90)
            ph = rand.uniform(80, 300)
            self.pillars.append(pygame.Rect(px, -20, pw, ph + 40))

    def solid_hits(self, rect):
        return [r for r in self.solids if rect.colliderect(r)]


def _normalize_grid(lines):
    width = max(len(r) for r in lines)
    return [r.ljust(width, AIR) for r in lines]


def _merge_rects(tiles):
    if not tiles:
        return []
    by_row = {}
    for t in tiles:
        by_row.setdefault(t.y, []).append(t)
    merged = []
    for y in sorted(by_row):
        row = sorted(by_row[y], key=lambda t: t.x)
        run = None
        for t in row:
            if run and t.x == run.right and t.w == TILE:
                run = run.union(t)
            else:
                if run:
                    merged.append(run)
                run = t.copy()
        if run:
            merged.append(run)
    return merged


def opposite_side(side):
    return {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}[side]


def find_exit(room, side):
    for e in room.exits:
        if e.side == side:
            return e
    return None


class Camera:
    def __init__(self, room):
        self.w = 1280
        self.h = 720
        self.room = room
        self.shake = 0.0
        self.x = 0.0
        self.y = 0.0

    def set_room(self, room):
        self.room = room

    def snap(self, target_rect):
        self.x = max(0, min(self.room.width - self.w, target_rect.centerx - self.w / 2))
        self.y = max(0, min(self.room.height - self.h, target_rect.centery - self.h / 2))

    def follow(self, target_rect, dt):
        k = min(1.0, dt * 8)
        tx = max(0, min(self.room.width - self.w, target_rect.centerx - self.w / 2))
        ty = max(0, min(self.room.height - self.h, target_rect.centery - self.h / 2))
        if self.room.width < self.w:
            tx = (self.room.width - self.w) / 2
        if self.room.height < self.h:
            ty = (self.room.height - self.h) / 2
        self.x += (tx - self.x) * k
        self.y += (ty - self.y) * k
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 26)

    def _jitter(self):
        if self.shake <= 0:
            return 0.0, 0.0
        return random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake)

    def apply(self, rect):
        jx, jy = self._jitter()
        return rect.move(int(-self.x + jx), int(-self.y + jy))

    def to_screen(self, x, y):
        jx, jy = self._jitter()
        return (int(x - self.x + jx), int(y - self.y + jy))
