from __future__ import annotations

import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

from focusboard.paths import data_dir


def gonk_path() -> Path:
    return data_dir() / "gonk.wav"


def ensure_gonk_wav() -> Path:
    path = gonk_path()
    if path.exists() and path.stat().st_size > 100:
        return path
    rate = 22050
    duration = 0.5
    n = int(rate * duration)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            t = i / rate
            envelope = min(1.0, t / 0.015) * math.exp(-t * 5.5)
            freq = 98.0 if t < 0.2 else 62.0
            sample = envelope * 0.95 * math.sin(2 * math.pi * freq * t)
            frames += struct.pack("<h", int(max(-1.0, min(1.0, sample)) * 30000))
        handle.writeframes(frames)
    return path


def _spawn(command: list[str]) -> bool:
    if not shutil.which(command[0]):
        return False
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except OSError:
        return False


def play_gonk(*, announce: bool = True) -> None:
    path = ensure_gonk_wav()
    played = False
    for command in (
        ["paplay", str(path)],
        ["pw-play", str(path)],
        ["aplay", "-q", str(path)],
        ["canberra-gtk-play", "-f", str(path)],
    ):
        if _spawn(command):
            played = True
            break
    if announce:
        for command in (
            ["spd-say", "It is paused"],
            ["espeak-ng", "It is paused"],
            ["espeak", "It is paused"],
        ):
            if _spawn(command):
                break
    if not played and not announce:
        return
