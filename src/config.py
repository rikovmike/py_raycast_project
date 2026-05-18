# src/config.py
"""Глобальные настройки рендерера."""

# Разрешения
VIRT_WIDTH = 320
VIRT_HEIGHT = 200
WIN_WIDTH = 960
WIN_HEIGHT = 600

# Рендеринг
TEX_SIZE = 64
FOV = 0.6  # поле зрения в радианах
FPS = 30

# Физика частиц
SPARK_COUNT = 50
SPARK_SPEED_MIN = 0.02
SPARK_SPEED_MAX = 0.05
SPARK_GRAVITY = 0.008
SPARK_LIFE_DECAY = 0.05

# God rays
GOD_RAY_COUNT = 60

# Управление
MOUSE_SENSITIVITY = 0.003
MOVE_SPEED = 0.07

# Карта по умолчанию (5×8)
DEFAULT_MAP = [
    [1, 1, 1, 1, 3, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 2, 0, 0, 2, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 3, 1, 1, 1, 1, 1],
]

# Стартовая позиция игрока
PLAYER_START = {"x": 1.5, "y": 1.5, "angle": 0.0}