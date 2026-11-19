"""Sons synthétisés à la volée (aucun fichier externe requis)."""

import math
import random

import pygame

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

SAMPLE_RATE = 22050
_sounds = {}


def _synth(dur, fn, vol=0.5):
    n = int(SAMPLE_RATE * dur)
    buf = np.zeros(n, dtype=np.int16)
    for i in range(n):
        t = i / SAMPLE_RATE
        buf[i] = int(max(-1.0, min(1.0, fn(t)) * vol) * 32767)
    stereo = np.column_stack((buf, buf))
    return pygame.sndarray.make_sound(stereo.copy())


def _envelope(t, dur, attack=0.005):
    if t < attack:
        return t / attack
    return max(0.0, 1.0 - (t - attack) / dur)


def _noise(t):
    return random.uniform(-1.0, 1.0)


def init():
    if not HAS_NUMPY:
        return False
    try:
        pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
    except pygame.error:
        return False
    _build()
    return True


def _build():
    _sounds["attack"] = _synth(
        0.12,
        lambda t: (_noise(t) * 0.6 + math.sin(2 * math.pi * (900 - 500 * t) * t) * 0.4)
        * _envelope(t, 0.12),
        0.30,
    )
    _sounds["hit"] = _synth(
        0.15,
        lambda t: math.sin(2 * math.pi * 110 * t) * 0.6 * _envelope(t, 0.15)
        + _noise(t) * 0.3 * _envelope(t, 0.08),
        0.45,
    )
    _sounds["hurt"] = _synth(
        0.25,
        lambda t: math.sin(2 * math.pi * (200 - 120 * t) * t) * _envelope(t, 0.25),
        0.5,
    )
    _sounds["jump"] = _synth(
        0.12,
        lambda t: math.sin(2 * math.pi * (300 + 250 * t) * t) * _envelope(t, 0.10),
        0.25,
    )
    _sounds["roll"] = _synth(
        0.18, lambda t: _noise(t) * 0.5 * _envelope(t, 0.16, 0.02), 0.20
    )
    _sounds["pickup"] = _synth(
        0.5,
        lambda t: math.sin(2 * math.pi * (440 + 220 * t * 4) * t) * _envelope(t, 0.5),
        0.35,
    )
    _sounds["fire"] = _synth(
        0.6,
        lambda t: _noise(t) * 0.4 * _envelope(t, 0.6, 0.05)
        + math.sin(2 * math.pi * 90 * t) * 0.3 * _envelope(t, 0.6),
        0.4,
    )
    _sounds["die"] = _synth(
        0.9,
        lambda t: math.sin(2 * math.pi * (220 - 160 * t) * t) * 0.5 * _envelope(t, 0.9)
        + math.sin(2 * math.pi * 55 * t) * 0.5 * _envelope(t, 0.9, 0.02),
        0.5,
    )
    _sounds["roar"] = _synth(
        1.1,
        lambda t: (
            math.sin(2 * math.pi * (70 + 30 * math.sin(2 * math.pi * 8 * t)) * t) * 0.6
            + _noise(t) * 0.35
        )
        * _envelope(t, 1.1, 0.08),
        0.5,
    )
    _sounds["victory"] = _synth(
        1.4,
        lambda t: (
            math.sin(2 * math.pi * 220 * t) * 0.4
            + math.sin(2 * math.pi * 330 * t) * 0.3
            + math.sin(2 * math.pi * 550 * t) * 0.2
        )
        * _envelope(t, 1.4, 0.05),
        0.4,
    )


def play(name):
    snd = _sounds.get(name)
    if snd:
        snd.play()


def has(name):
    return name in _sounds
