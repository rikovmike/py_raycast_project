# src/renderer.py
"""Логика рендеринга: геометрия, пост-обработка, эффекты."""

import numpy as np
import pygame as pg
import math
import random
from . import config
from .utils import clamp


class Renderer:
    """Основной класс рендерера."""

    def __init__(self, textures, game_map):
        self.textures = textures
        self.map = np.array(game_map, dtype=int)
        self.map_h, self.map_w = self.map.shape

        # Буферы
        self.z_buffer = np.full((config.VIRT_WIDTH, config.VIRT_HEIGHT),
                                99.0, dtype=np.float32)

        # God rays параметры
        self._init_god_rays()

    def _init_god_rays(self):
        """Инициализация параметров лучей."""
        self.ray_angles = [random.uniform(0, math.pi * 2)
                           for _ in range(config.GOD_RAY_COUNT)]
        self.ray_phases = [random.uniform(0, math.pi * 2)
                           for _ in range(config.GOD_RAY_COUNT)]
        self.ray_mults = [random.uniform(0.5, 1.0)
                          for _ in range(config.GOD_RAY_COUNT)]

    def render_floor_ceiling(self, frame, z_buf, px, py, pa):
        """Отрисовка пола и потолка методом проекции."""
        rx0 = math.cos(pa - config.FOV)
        ry0 = math.sin(pa - config.FOV)
        rx1 = math.cos(pa + config.FOV)
        ry1 = math.sin(pa + config.FOV)

        for y in range(config.VIRT_HEIGHT // 2, config.VIRT_HEIGHT):
            dist = (0.5 * config.VIRT_HEIGHT) / (y - config.VIRT_HEIGHT // 2 + 0.0001)

            # Координаты на плоскости пола/потолка
            xs = np.linspace(0, 1, config.VIRT_WIDTH)
            cx = px + dist * (rx0 + xs * (rx1 - rx0))
            cy = py + dist * (ry0 + xs * (ry1 - ry0))

            # Текстурные координаты
            tx = (cx * 63).astype(int) % config.TEX_SIZE
            ty = (cy * 63).astype(int) % config.TEX_SIZE

            # Пол
            frame[:, y] = self.textures['floor'][tx, ty]
            z_buf[:, y] = dist

            # Потолок (зеркально)
            ceiling_y = config.VIRT_HEIGHT - y - 1
            frame[:, ceiling_y] = self.textures['ceil'][tx, ty]
            z_buf[:, ceiling_y] = dist

    def cast_ray_dda(self, px, py, ray_angle, player_angle):
        """
        DDA-алгоритм трассировки луча.
        :return: (hit_x, hit_y, distance, side) или None при выходе за границы
        """
        rdx, rdy = math.cos(ray_angle), math.sin(ray_angle)
        mx, my = int(px), int(py)

        # Дельты для DDA
        ddx = abs(1 / rdx) if rdx != 0 else 1e30
        ddy = abs(1 / rdy) if rdy != 0 else 1e30

        # Направление шага и начальное расстояние до следующей границы
        sx, step_x = (-1, (px - mx) * ddx) if rdx < 0 else (1, (mx + 1 - px) * ddx)
        sy, step_y = (-1, (py - my) * ddy) if rdy < 0 else (1, (my + 1 - py) * ddy)

        side = 0  # 0 = вертикальная стена, 1 = горизонтальная
        while True:
            if step_x < step_y:
                step_x += ddx
                mx += sx
                side = 0
            else:
                step_y += ddy
                my += sy
                side = 1

            # Выход за границы карты
            if not (0 <= my < self.map_h and 0 <= mx < self.map_w):
                return None

            # Попадание в стену
            if self.map[my, mx] > 0:
                # Коррекция "рыбьего глаза"
                dist = (step_x - ddx if side == 0 else step_y - ddy) * math.cos(ray_angle - player_angle)
                return mx, my, dist, side

    def render_walls(self, frame, z_buf, px, py, pa):
        """Отрисовка стен методом рейкастинга."""
        hit_info = None

        for x in range(config.VIRT_WIDTH):
            ray_angle = pa - config.FOV + (x / config.VIRT_WIDTH) * 2 * config.FOV
            result = self.cast_ray_dda(px, py, ray_angle, pa)

            if result is None:
                continue

            mx, my, dist, side = result
            rdx, rdy = math.cos(ray_angle), math.sin(ray_angle)

            # Высота стены на экране
            wall_height = int(config.VIRT_HEIGHT / (dist + 0.0001))

            # Координата текстуры по ширине
            if side == 0:
                wall_hit = py + dist * rdy
            else:
                wall_hit = px + dist * rdx
            tx = int((wall_hit % 1) * config.TEX_SIZE)

            # Вертикальный диапазон отрисовки
            y0 = max(0, config.VIRT_HEIGHT // 2 - wall_height // 2)
            y1 = min(config.VIRT_HEIGHT, config.VIRT_HEIGHT // 2 + wall_height // 2)

            if y1 > y0:
                # Интерполяция текстурных координат по высоте
                v_coords = np.linspace(
                    (y0 - (config.VIRT_HEIGHT // 2 - wall_height // 2)) / wall_height * config.TEX_SIZE,
                    (y1 - (config.VIRT_HEIGHT // 2 - wall_height // 2)) / wall_height * config.TEX_SIZE,
                    y1 - y0
                ).astype(int)

                texture = self.textures.get(self.map[my, mx])
                if texture is not None:
                    frame[x, y0:y1] = texture[tx % config.TEX_SIZE, v_coords % config.TEX_SIZE]
                    z_buf[x, y0:y1] = dist

            # Сохраняем информацию о попадании в центр экрана
            if x == config.VIRT_WIDTH // 2:
                hit_info = (px + dist * rdx, py + dist * rdy, dist)

        return hit_info

    def apply_post_processing(self, frame, z_buf, focus, brightness, saturation_mult):
        """
        Пост-обработка: виньетка, глубина резкости, насыщенность.
        :return: frame как uint8 для отрисовки
        """
        # Координатные сетки
        xs = np.linspace(-0.5, 0.5, config.VIRT_WIDTH)
        ys = np.linspace(-0.5, 0.5, config.VIRT_HEIGHT)
        xm, ym = np.meshgrid(xs, ys, indexing='ij')

        # Виньетка + затенение по глубине
        radial = np.exp(-focus * (xm ** 2 + ym ** 2))
        depth_mask = np.exp(-0.3 * z_buf)
        light_mask = radial * depth_mask * brightness

        # Насыщенность: центр — цветной, края — ч/б
        gray = np.stack([np.dot(frame, [0.299, 0.587, 0.114])] * 3, axis=-1)
        sat_map = np.clip(
            np.exp(-(focus / 15.0) * (xm ** 2 + ym ** 2)) +
            (1.0 - (focus - 12) / 250.0),
            0, 1
        )[..., np.newaxis]

        # Финальная композиция
        blended = frame * sat_map + gray * (1 - sat_map)
        result = (blended * (light_mask[..., np.newaxis] + 0.06)).clip(0, 255)

        return result.astype(np.uint8)

    def draw_god_rays(self, surface, rays_intensity, center=None):
        """Отрисовка процедурных god rays на поверхности с альфа-каналом."""
        if rays_intensity < 0.05:
            # Когда интенсивность падает, поверхность всё равно нужно очищать
            surface.fill((0, 0, 0, 0))
            return

        # ⬇️ ВАЖНО: очищаем слой каждый кадр, иначе лучи остаются навсегда
        surface.fill((0, 0, 0, 0))

        if center is None:
            center = (config.VIRT_WIDTH // 2, config.VIRT_HEIGHT // 2)
        cx, cy = center

        t = pg.time.get_ticks() * 0.005
        for i in range(config.GOD_RAY_COUNT):
            length = (5 + math.sin(t + self.ray_phases[i]) * 30) * self.ray_mults[i] * rays_intensity
            ex = cx + math.cos(self.ray_angles[i]) * length
            ey = cy + math.sin(self.ray_angles[i]) * length
            alpha = int(35 * rays_intensity)
            pg.draw.line(surface, (255, 210, 160, alpha),
                         (cx, cy), (int(ex), int(ey)), 1)