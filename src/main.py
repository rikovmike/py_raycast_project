# src/main.py
"""Основной цикл игры: ввод, обновление, отрисовка."""

import pygame as pg
import numpy as np
import random
from . import config
from .utils import load_textures
from .entities import Spark
from .renderer import Renderer


class Game:
    """Основной класс игры."""

    def __init__(self):
        pg.init()
        self.screen = pg.display.set_mode((config.WIN_WIDTH, config.WIN_HEIGHT))
        pg.display.set_caption("Raycast Pygame Renderer")
        pg.mouse.set_visible(False)
        pg.event.set_grab(True)

        # Виртуальный буфер (низкое разрешение для ретро-эффекта)
        self.virt_surf = pg.Surface((config.VIRT_WIDTH, config.VIRT_HEIGHT))
        self.rays_surf = pg.Surface((config.VIRT_WIDTH, config.VIRT_HEIGHT), pg.SRCALPHA)

        # Загрузка ресурсов
        texture_paths = {
            1: "assets/textures/wall01.png",
            2: "assets/textures/wall02.png",
            3: "assets/textures/wall03.png",
            'floor': "assets/textures/floor01.png",
            'ceil': "assets/textures/ceil01.png",
        }
        textures = load_textures(texture_paths)

        # Инициализация рендерера
        self.renderer = Renderer(textures, config.DEFAULT_MAP)

        # Состояние игрока
        self.player = config.PLAYER_START.copy()

        # Параметры эффектов
        self.focus = 12.0  # фокусное расстояние
        self.brightness = 1.2  # яркость
        self.rays_intensity = 0.0  # интенсивность god rays

        # Частицы
        self.sparks = [Spark() for _ in range(config.SPARK_COUNT)]

        self.clock = pg.time.Clock()
        self.running = True

    def handle_input(self):
        """Обработка ввода: события и клавиши."""
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                self.running = False

        # Управление фокусом (ЛКМ)
        is_firing = pg.mouse.get_pressed()[0]
        target_focus = 280.0 if is_firing else 12.0
        target_bright = 15.0 if is_firing else 1.2
        target_rays = 1.0 if is_firing else 0.0

        # Плавное изменение параметров
        self.focus += (target_focus - self.focus) * 0.1
        self.brightness += (target_bright - self.brightness) * 0.1
        self.rays_intensity += (target_rays - self.rays_intensity) * 0.1

        # Поворот камеры мышью
        rel_x, _ = pg.mouse.get_rel()
        self.player['angle'] += rel_x * config.MOUSE_SENSITIVITY

        # Перемещение клавишами
        keys = pg.key.get_pressed()
        dx, dy = 0, 0
        sin_a, cos_a = np.sin(self.player['angle']), np.cos(self.player['angle'])

        if keys[pg.K_w]: dx += cos_a; dy += sin_a
        if keys[pg.K_s]: dx -= cos_a; dy -= sin_a
        if keys[pg.K_a]: dx += sin_a; dy -= cos_a
        if keys[pg.K_d]: dx -= sin_a; dy += cos_a

        # Коллизия с картой (упрощённая)
        next_x, next_y = self.player['x'] + dx * 0.3, self.player['y'] + dy * 0.3
        if 0 <= int(next_y) < self.renderer.map_h and \
                0 <= int(self.player['x'] + dx * 0.3) < self.renderer.map_w and \
                self.renderer.map[int(self.player['y']), int(self.player['x'] + dx * 0.3)] == 0:
            self.player['x'] += dx * config.MOVE_SPEED
        if 0 <= int(self.player['y'] + dy * 0.3) < self.renderer.map_h and \
                0 <= int(next_x) < self.renderer.map_w and \
                self.renderer.map[int(self.player['y'] + dy * 0.3), int(self.player['x'])] == 0:
            self.player['y'] += dy * config.MOVE_SPEED

        return is_firing

    def update_particles(self, is_firing, hit_info):
        """Обновление и отрисовка частиц."""
        # Спавн искр при "сварке"
        if is_firing and hit_info and hit_info[2] < 6:
            if random.random() > 0.4:
                for spark in self.sparks:
                    if not spark.is_active():
                        spark.spawn(hit_info[0], hit_info[1], self.player['angle'])
                        break

        # Обновление и отрисовка
        for spark in self.sparks:
            if spark.update():
                dx_s = spark.x - self.player['x']
                dy_s = spark.y - self.player['y']
                dist_s = dx_s * np.cos(self.player['angle']) + dy_s * np.sin(self.player['angle'])

                if dist_s > 0.1:
                    # Проекция на экран
                    screen_x = int(((dx_s * -np.sin(self.player['angle']) +
                                     dy_s * np.cos(self.player['angle'])) / dist_s / 1.1 + 0.5) * config.VIRT_WIDTH)
                    screen_y = int(config.VIRT_HEIGHT / 2 + (spark.z / dist_s * config.VIRT_HEIGHT))

                    # Отрисовка, если искра ближе, чем стена
                    if (0 <= screen_x < config.VIRT_WIDTH and
                            0 <= screen_y < config.VIRT_HEIGHT and
                            dist_s < self.renderer.z_buffer[screen_x, screen_y]):
                        size = max(1, int(3 / dist_s))
                        pg.draw.rect(self.virt_surf, (255, 200, 50),
                                     (screen_x, screen_y, size, size))

    def render(self, is_firing, hit_info):
        """Полный цикл рендеринга кадра."""
        # Буферы
        frame = np.zeros((config.VIRT_WIDTH, config.VIRT_HEIGHT, 3), dtype=np.float32)
        z_buf = np.full((config.VIRT_WIDTH, config.VIRT_HEIGHT), 99.0, dtype=np.float32)

        # 1. Пол и потолок
        self.renderer.render_floor_ceiling(frame, z_buf,
                                           self.player['x'], self.player['y'],
                                           self.player['angle'])

        # 2. Стены
        hit_info = self.renderer.render_walls(frame, z_buf,
                                              self.player['x'], self.player['y'],
                                              self.player['angle'])

        # 3. Пост-обработка
        final = self.renderer.apply_post_processing(
            frame, z_buf,
            focus=self.focus,
            brightness=self.brightness,
            saturation_mult=1.0
        )
        pg.surfarray.blit_array(self.virt_surf, final)

        # 4. God rays
        self.renderer.draw_god_rays(self.rays_surf, self.rays_intensity)
        self.virt_surf.blit(self.rays_surf, (0, 0))

        # 5. Частицы
        self.update_particles(is_firing, hit_info)

        # 6. Масштабирование на полный экран
        self.screen.blit(pg.transform.scale(self.virt_surf,
                                            (config.WIN_WIDTH, config.WIN_HEIGHT)),
                         (0, 0))
        pg.display.flip()

    def run(self):
        """Главный цикл игры."""
        while self.running:
            is_firing = self.handle_input()
            hit_info = None  # будет заполнено в renderer.render_walls
            self.render(is_firing, hit_info)
            self.clock.tick(config.FPS)

        pg.quit()


def run_engine():
    """Точка входа для запуска извне."""
    game = Game()
    game.run()