# src/entities.py
"""Классы сущностей: частицы, эффекты."""

import random
import math
from . import config


class Spark:
    """Частица искры для эффекта сварки."""

    __slots__ = ("x", "y", "z", "vx", "vy", "vz",
                 "gravity", "life", "active")

    def __init__(self):
        self.active = False

    def spawn(self, x, y, angle):
        """Создать искру в точке (x, y) с направлением angle."""
        self.x, self.y, self.z = x, y, 0.0
        speed = random.uniform(config.SPARK_SPEED_MIN, config.SPARK_SPEED_MAX)
        # Случайный разброс направления
        self.vx = -math.cos(angle) * speed + random.uniform(-0.02, 0.02)
        self.vy = -math.sin(angle) * speed + random.uniform(-0.02, 0.02)
        self.vz = random.uniform(-0.04, 0.01)
        self.gravity = config.SPARK_GRAVITY
        self.life = 1.0
        self.active = True

    def update(self):
        """Обновить состояние частицы. Возвращает False, если частица умерла."""
        if not self.active:
            return False

        # Физика
        self.x += self.vx
        self.y += self.vy
        self.z += self.vz
        self.vz += self.gravity

        # Отскок от "пола" (максимальная высота)
        if self.z > 0.45:
            self.z = 0.45
            self.vx *= 0.4
            self.vy *= 0.4
            self.vz = 0

        # Угасание
        self.life -= config.SPARK_LIFE_DECAY
        if self.life <= 0:
            self.active = False
            return False
        return True

    def is_active(self):
        return self.active