# src/utils.py
"""Вспомогательные функции."""

import os
import pygame as pg
import numpy as np
from . import config


def load_texture(path=None, size=None):
    """
    Загружает текстуру и возвращает её как numpy-массив float32.
    Если путь не указан или файл не найден — возвращает серую заглушку.
    """
    if size is None:
        size = (config.TEX_SIZE, config.TEX_SIZE)

    if path and os.path.exists(path):
        try:
            img = pg.image.load(path).convert()
            surf = pg.Surface(size)
            surf.blit(img, (0, 0))
            return pg.surfarray.array3d(surf).astype(np.float32)
        except Exception:
            pass  # fallback to placeholder

    # Заглушка: серая текстура
    surf = pg.Surface(size)
    surf.fill((100, 100, 100))
    return pg.surfarray.array3d(surf).astype(np.float32)


def load_textures(texture_map):
    """
    Загружает словарь текстур.
    :param texture_map: dict {key: path_or_none}
    :return: dict {key: numpy_array}
    """
    return {key: load_texture(path) for key, path in texture_map.items()}


def clamp(value, min_val, max_val):
    """Ограничивает значение диапазоном [min_val, max_val]."""
    return max(min_val, min(value, max_val))