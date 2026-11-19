"""Constantes globales de Cendre — L'Écho des Abysses."""

WS_WIDTH = 1280
WS_HEIGHT = 720
FPS = 60

TILE = 32

GRAVITY = 2200.0
MAX_FALL = 1300.0

PATH_SAVE = "sauvegarde.json"

COLORS = {
    "bg": (10, 10, 14),
    "hp": (178, 34, 34),
    "hp_back": (40, 10, 10),
    "stam": (90, 160, 90),
    "stam_back": (15, 30, 15),
    "soul": (200, 200, 160),
    "text": (210, 205, 190),
    "faded": (120, 116, 105),
    "accent": (200, 80, 40),
    "boss": (140, 20, 20),
    "white": (235, 235, 225),
    "gold": (212, 175, 55),
    "fog": (120, 60, 170),
}

ENTITY_DAMAGE = {
    "hollow": 15,
    "heavy": 25,
    "archer": 12,
    "flyer": 15,
    "gardien_slam": 30,
    "gardien_charge": 25,
    "gardien_swing": 28,
    "echo_bolt": 12,
    "echo_ash": 18,
    "echo_burst": 16,
    "spike": 20,
}

SOULS_KILL = {
    "hollow": 50,
    "heavy": 120,
    "archer": 80,
    "flyer": 60,
    "gardien": 2500,
    "echo": 5000,
}

LEVEL_BASE_COST = 120
LEVEL_GROWTH = 1.35
HP_PER_VIGOR = 25
STAM_PER_ENDURANCE = 12

FLASK_CHARGES = 3
FLASK_HEAL = 60
FLASK_DRINK_TIME = 0.7

PLAYER = {
    "base_hp": 100,
    "base_stamina": 100,
    "speed": 300.0,
    "jump_vel": -780.0,
    "air_jump_vel": -700.0,
    "roll_speed": 560.0,
    "roll_time": 0.28,
    "dash_speed": 920.0,
    "dash_time": 0.20,
    "attack_damage": 25,
    "attack_stamina": 16,
    "roll_stamina": 22,
    "dash_stamina": 26,
    "stamina_regen": 45.0,
    "stamina_regen_delay": 0.35,
    "iframes_hurt": 0.8,
    "roll_iframes": 0.30,
    "coyote_time": 0.10,
    "jump_buffer": 0.12,
}

CONTROLS_HINT = [
    ("Déplacement", "Q / D   ou   A / D   ou   flèches"),
    ("Saut (x2 avec les Ailes de Cendre)", "Espace  ou  Z / W  ou  haut"),
    ("Attaque", "J  ou  X"),
    ("Roulade / Passe d'Ombre", "L  ou  C"),
    ("Fiole de cendre (soin)", "K  ou  V"),
    ("Interagir (feux de cendre)", "E"),
    ("Pause", "Échap"),
]
