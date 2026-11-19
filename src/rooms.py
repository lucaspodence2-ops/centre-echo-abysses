"""Définition des salles : génération des grilles + connexions métroidvania."""

WALL = "#"


def _grid(width, floor=18, ceiling=2):
    g = []
    for y in range(22):
        if y < ceiling or y >= floor:
            g.append([WALL] * width)
        else:
            g.append(["."] * width)
    return g


def _fill(g, x0, y0, x1, y1, ch=WALL):
    for y in range(max(0, y0), min(len(g), y1 + 1)):
        for x in range(max(0, x0), min(len(g[0]), x1 + 1)):
            g[y][x] = ch


def _put(g, x, y, ch):
    g[y][x] = ch


def _col(g, x, y0, y1, ch=WALL):
    _fill(g, x, y0, x, y1, ch)


def _strings(g):
    return ["".join(row) for row in g]


def _room(name, theme, g, exits, boss=None, item=None, trigger_x=None, reward=None):
    d = {"name": name, "theme": theme, "map": _strings(g), "exits": exits}
    if boss:
        d["boss"] = boss
    if item:
        d["item"] = item
    if trigger_x is not None:
        d["trigger_x"] = trigger_x
    if reward:
        d["reward"] = reward
    return d


def build_rooms():
    rooms = {}

    g = _grid(64)
    _col(g, 0, 2, 21)
    _col(g, 1, 2, 21)
    _col(g, 24, 2, 12)
    _col(g, 44, 5, 10)
    _put(g, 8, 17, "B")
    _put(g, 32, 17, "1")
    _put(g, 52, 17, "1")
    _fill(g, 62, 12, 63, 17, ".")
    rooms["crypt"] = _room(
        "Crypte des Origines",
        "crypt",
        g,
        [{"side": "right", "span": (12, 17), "to": "hall", "to_side": "left"}],
    )

    g = _grid(96)
    _fill(g, 7, 14, 11, 14)
    _fill(g, 36, 12, 40, 12)
    _fill(g, 58, 14, 61, 14)
    _fill(g, 66, 8, 69, 8)
    _fill(g, 70, 0, 73, 1, ".")
    _fill(g, 70, 3, 73, 3)
    _fill(g, 30, 18, 33, 20, ".")
    _fill(g, 30, 20, 33, 20, "^")
    _put(g, 20, 17, "1")
    _put(g, 46, 17, "1")
    _put(g, 82, 17, "4")
    _put(g, 9, 13, "2")
    rooms["hall"] = _room(
        "Salle des Étroits",
        "hall",
        g,
        [
            {"side": "left", "span": (12, 17), "to": "crypt", "to_side": "right"},
            {"side": "right", "span": (12, 17), "to": "sanctuary", "to_side": "left"},
            {"side": "top", "span": (70, 73), "to": "tower", "to_side": "bottom",
             "need": "double_jump"},
        ],
    )

    g = _grid(72)
    _col(g, 0, 2, 21)
    _col(g, 1, 2, 21)
    _col(g, 30, 2, 7)
    _fill(g, 40, 12, 43, 12)
    _put(g, 5, 17, "B")
    rooms["sanctuary"] = _room(
        "Sanctuaire Déchu",
        "sanctuary",
        g,
        [{"side": "left", "span": (12, 17), "to": "hall", "to_side": "right"}],
        boss="gardien",
        trigger_x=640,
        reward="double_jump",
    )

    g = _grid(56)
    _fill(g, 10, 18, 12, 20, ".")
    _fill(g, 10, 20, 12, 20, "^")
    _fill(g, 44, 18, 47, 21, ".")
    _fill(g, 18, 13, 20, 13)
    _fill(g, 10, 8, 12, 8)
    _fill(g, 28, 10, 30, 10)
    _put(g, 11, 7, "2")
    _put(g, 29, 9, "3")
    _put(g, 38, 17, "1")
    rooms["tower"] = _room(
        "Balgard de la Tour",
        "tower",
        g,
        [
            {"side": "bottom", "span": (44, 47), "to": "hall", "to_side": "top"},
            {"side": "right", "span": (12, 17), "to": "cave", "to_side": "left"},
        ],
    )

    g = _grid(96)
    _col(g, 0, 2, 21)
    _col(g, 1, 2, 21)
    _fill(g, 20, 17, 30, 18, WALL)
    _fill(g, 44, 14, 47, 14)
    _fill(g, 50, 12, 53, 13)
    _col(g, 50, 14, 17)
    _col(g, 53, 14, 17)
    _fill(g, 66, 14, 70, 14)
    _fill(g, 74, 17, 83, 20, ".")
    _fill(g, 74, 20, 83, 20, "^")
    _fill(g, 88, 18, 91, 21, ".")
    _fill(g, 16, 17, 19, 21, ".")
    _put(g, 6, 17, "B")
    _put(g, 25, 16, "1")
    _put(g, 28, 16, "1")
    _put(g, 31, 9, "3")
    _put(g, 60, 9, "3")
    _put(g, 68, 13, "2")
    _put(g, 51, 11, "O")
    rooms["cave"] = _room(
        "Grotte Murmurante",
        "cave",
        g,
        [
            {"side": "left", "span": (12, 17), "to": "tower", "to_side": "right"},
            {"side": "bottom", "span": (12, 15), "to": "hall", "to_side": "top"},
            {"side": "bottom", "span": (88, 91), "to": "abyss", "to_side": "top"},
        ],
        item="dash",
    )

    g = _grid(72)
    _fill(g, 24, 0, 27, 1, ".")
    _col(g, 18, 2, 13)
    _col(g, 50, 12, 17)
    _put(g, 10, 17, "B")
    _put(g, 34, 17, "B")
    rooms["abyss"] = _room(
        "Sanctum des Abysses",
        "abyss",
        g,
        [{"side": "top", "span": (24, 27), "to": "cave", "to_side": "bottom",
          "need": "double_jump"}],
        boss="echo",
        trigger_x=1250,
    )

    return rooms
