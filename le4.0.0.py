import argparse
import math
import json
import os
import random
import shutil
import time as time_mod
from collections import OrderedDict
from pathlib import Path

import pygame

pygame.init()

SPRITES_DIR = Path(__file__).parent / "sprites"
SPRITE_SIZE = 32


def load_sprite_sheet(fname, frame_w=SPRITE_SIZE, frame_h=SPRITE_SIZE):
    path = SPRITES_DIR / fname
    if not path.exists():
        return None
    sheet = pygame.image.load(str(path)).convert_alpha()
    sw, sh = sheet.get_size()
    frames = []
    for x in range(0, sw, frame_w):
        for y in range(0, sh, frame_h):
            if x + frame_w <= sw and y + frame_h <= sh:
                frame = sheet.subsurface((x, y, frame_w, frame_h))
                frames.append(frame)
    return frames if frames else None


def gen_sprite_frames(color, shape="arrow", n_frames=8, size=SPRITE_SIZE):
    frames = []
    half = size // 2
    r = half - 2
    for i in range(n_frames):
        angle = (2 * math.pi * i) / n_frames
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        glow = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, 50), (half, half), half)
        surf.blit(glow, (0, 0))
        if shape == "arrow":
            tip = (half + math.cos(angle) * r, half + math.sin(angle) * r)
            la = angle + 2.3
            ra = angle - 2.3
            l = (half + math.cos(la) * r * 0.55, half + math.sin(la) * r * 0.55)
            rp = (half + math.cos(ra) * r * 0.55, half + math.sin(ra) * r * 0.55)
            pygame.draw.polygon(surf, color, [tip, l, rp])
            pygame.draw.circle(surf, (min(255, color[0] + 60), min(255, color[1] + 60),
                                       min(255, color[2] + 60)), (half, half), max(2, half // 4))
        elif shape == "diamond":
            pulse = 0.8 + 0.2 * math.sin(i * math.pi / 1.5)
            c = tuple(min(255, int(v * pulse)) for v in color)
            pts = [(half, 2 + int(half * 0.2)), (size - 3, half),
                   (half, size - 3), (2, half)]
            pygame.draw.polygon(surf, c, pts)
            ip = (half, half + int(half * 0.3))
            pygame.draw.circle(surf, (min(255, c[0] + 40), min(255, c[1] + 40),
                                       min(255, c[2] + 40)), ip, max(1, half // 5))
        elif shape == "circle":
            pulse = 0.85 + 0.15 * math.sin(i * math.pi / 2)
            c = tuple(min(255, int(v * pulse)) for v in color)
            pygame.draw.circle(surf, c, (half, half), r - 2)
            pygame.draw.circle(surf, (min(255, c[0] + 30), min(255, c[1] + 30),
                                       min(255, c[2] + 30)), (half - r // 3, half - r // 3), max(1, r // 4))
        frames.append(surf)
    return frames

QUALITY_PRESETS = {
    "low": {
        "ray_step_deg": 3.0,
        "cast_step": 12,
        "gradient_resolution": 16,
        "gradient_cache_size": 4,
        "max_dynamic_lights": 1,
        "max_static_lights": 16,
        "max_dynamic_objects": 4,
        "colored_lights": False,
        "particles": False,
        "flicker": False,
        "ambient_light": 0,
        "weather": False,
        "day_night": False,
        "fog_of_war": False,
    },
    "normal": {
        "ray_step_deg": 1.2,
        "cast_step": 6,
        "gradient_resolution": 32,
        "gradient_cache_size": 16,
        "max_dynamic_lights": 3,
        "max_static_lights": 24,
        "max_dynamic_objects": 6,
        "colored_lights": True,
        "particles": True,
        "flicker": True,
        "ambient_light": 0,
        "weather": True,
        "day_night": True,
        "fog_of_war": True,
    },
    "max": {
        "ray_step_deg": 0.5,
        "cast_step": 3,
        "gradient_resolution": 64,
        "gradient_cache_size": 32,
        "max_dynamic_lights": 5,
        "max_static_lights": 32,
        "max_dynamic_objects": 8,
        "colored_lights": True,
        "particles": True,
        "flicker": True,
        "ambient_light": 0,
        "weather": True,
        "day_night": True,
        "fog_of_war": True,
    },
}


class Logger:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.log_file = "lightengine.log"
        if self.enabled:
            with open(self.log_file, "w") as f:
                f.write(f"LightEngine Log - {time_mod.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 60 + "\n")

    def log(self, event, details=""):
        if not self.enabled:
            return
        ts = time_mod.strftime("%H:%M:%S")
        with open(self.log_file, "a") as f:
            f.write(f"[{ts}] {event}: {details}\n")

    def event(self, category, message):
        self.log(category, message)


class Profiler:
    def __init__(self):
        self.timings = {}
        self.history = {}
        self.frame_count = 0

    def start(self, stage):
        self.timings[stage] = time_mod.perf_counter()

    def end(self, stage):
        if stage in self.timings:
            elapsed = (time_mod.perf_counter() - self.timings[stage]) * 1000
            if stage not in self.history:
                self.history[stage] = []
            self.history[stage].append(elapsed)
            if len(self.history[stage]) > 60:
                self.history[stage].pop(0)

    def get_avg(self, stage):
        vals = self.history.get(stage, [])
        return sum(vals) / len(vals) if vals else 0

    def get_all_avgs(self):
        return {s: self.get_avg(s) for s in self.history}


class AnimatedSprite:
    def __init__(self, frames, frame_duration=0.15, loop=True):
        self.frames = frames
        self.frame_duration = frame_duration
        self.loop = loop
        self.current_frame = 0
        self.timer = 0.0
        self.done = False

    def update(self, dt):
        if self.done:
            return
        self.timer += dt
        if self.timer >= self.frame_duration:
            self.timer -= self.frame_duration
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1
                    self.done = True

    def get_current_frame(self):
        return self.frames[self.current_frame] if self.frames else None

    def reset(self):
        self.current_frame = 0
        self.timer = 0.0
        self.done = False


class WeatherParticle:
    def __init__(self, x, y, wtype="rain"):
        self.x = x
        self.y = y
        self.wtype = wtype
        if wtype == "rain":
            self.vx = random.uniform(-10, -5)
            self.vy = random.uniform(80, 150)
            self.length = random.uniform(4, 8)
            self.alpha = random.randint(100, 200)
        elif wtype == "snow":
            self.vx = random.uniform(-8, 8)
            self.vy = random.uniform(15, 35)
            self.size = random.uniform(1.5, 3.5)
            self.alpha = random.randint(150, 230)
            self.wobble = random.uniform(0, math.pi * 2)
            self.wobble_speed = random.uniform(1.0, 3.0)
        elif wtype == "fog":
            self.vx = random.uniform(3, 8)
            self.vy = random.uniform(-1, 1)
            self.size = random.uniform(30, 80)
            self.alpha = random.randint(15, 40)

    def update(self, dt):
        if self.wtype == "rain":
            self.x += self.vx * dt
            self.y += self.vy * dt
        elif self.wtype == "snow":
            self.wobble += self.wobble_speed * dt
            self.x += self.vx * dt + math.sin(self.wobble) * 4 * dt
            self.y += self.vy * dt
        elif self.wtype == "fog":
            self.x += self.vx * dt
            self.y += self.vy * dt

    def draw(self, screen, camera_x, camera_y, day_factor=1.0):
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        sw, sh = screen.get_width(), screen.get_height()
        if sx < -100 or sx > sw + 100 or sy < -100 or sy > sh + 100:
            return
        alpha = int(self.alpha * day_factor)
        if self.wtype == "rain":
            color = (180, 190, 220, alpha)
            ex = int(sx + self.vx * 0.03)
            ey = int(sy + self.vy * 0.03)
            pygame.draw.line(screen, color, (sx, sy), (ex, ey), 1)
        elif self.wtype == "snow":
            color = (255, 255, 255, alpha)
            pygame.draw.circle(screen, color, (sx, sy), max(1, int(self.size)))
        elif self.wtype == "fog":
            color = (180, 180, 190, alpha)
            surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (int(self.size), int(self.size)), int(self.size))
            screen.blit(surf, (sx - int(self.size), sy - int(self.size)))


class DynamicObject:
    __slots__ = (
        'x', 'y', 'light_radius', 'light_intensity', 'color', 'size',
        '_last_pos', '_cached_light_surface', '_last_cache_key',
        'phase', 'flicker_offset', 'lid', 'anim_sprite', 'anim_timer',
        'frame', 'num_frames', 'engine',
    )

    def __init__(self, x, y, light_radius=0, light_intensity=1.0, color=(200, 100, 50), size=0.8, lid=-1):
        self.x = x
        self.y = y
        self.light_radius = light_radius
        self.light_intensity = light_intensity
        self.color = color
        self.size = size
        self.lid = lid
        self.engine = None
        self._last_pos = (x, y)
        self._cached_light_surface = None
        self._last_cache_key = None
        self.phase = random.uniform(0, math.pi * 2)
        self.flicker_offset = random.uniform(0.85, 1.15)
        self.anim_sprite = None
        self.anim_timer = 0.0
        self.frame = 0
        self.num_frames = 8

    def update(self, dt):
        self.phase += dt * 3.0
        self.anim_timer += dt
        if self.anim_timer > 0.1:
            self.anim_timer -= 0.1
            self.frame = (self.frame + 1) % self.num_frames

    def moved(self):
        if (self.x, self.y) != self._last_pos:
            self._last_pos = (self.x, self.y)
            return True
        return False

    def draw(self, screen, cell_size, camera_x, camera_y):
        screen_x = self.x * cell_size - camera_x
        screen_y = self.y * cell_size - camera_y
        frames = self.engine._sprite_cache.get("object") if self.engine else None
        if frames:
            f = self.anim_timer / 0.1
            idx = int(f) % len(frames)
            sprite = frames[idx]
            sw = sprite.get_width()
            scale = max(1, int(cell_size * self.size))
            scaled = pygame.transform.scale(sprite, (scale, scale))
            sr = scaled.get_rect(center=(int(screen_x), int(screen_y)))
            screen.blit(scaled, sr)
            return
        radius_px = int(cell_size * self.size // 2)
        anim_offset = math.sin(self.anim_timer * 5) * 2
        pulse = 0.85 + 0.15 * math.sin(self.phase)
        r = int(self.color[0] * pulse)
        g = int(self.color[1] * pulse)
        b = int(self.color[2] * pulse)
        pygame.draw.circle(screen, (r, g, b), (int(screen_x), int(screen_y + anim_offset)), radius_px)
        highlight = int(180 + 75 * math.sin(self.anim_timer * 8))
        pygame.draw.circle(screen, (highlight, highlight, highlight), (int(screen_x - radius_px * 0.3), int(screen_y + anim_offset - radius_px * 0.3)), max(1, radius_px // 3))


class Bot:
    def __init__(self, x, y, light_radius=0, light_intensity=1.0, color=(0, 100, 255), speed=2.0, lid=-1):
        self.x = x
        self.y = y
        self.light_radius = light_radius
        self.light_intensity = light_intensity
        self.color = color
        self.speed = speed
        self.lid = lid
        self.angle = 0.0
        self.light_on = True
        self.state = "idle"
        self._target_x = None
        self._target_y = None
        self._look_x = None
        self._look_y = None
        self._func = None
        self._cached_light_surface = None
        self._last_cache_key = None
        self._wait_remaining = 0.0
        self._tick_timer = 0.0
        self._tick_interval = 0.0
        self._handlers = {}
        self._path = []
        self._path_idx = 0
        self._follow_target = None
        self._guard_target = None
        self._guard_radius = 2.0
        self._say_text = None
        self._say_timer = 0.0
        self.engine = None

        self._alert_level = 0.0
        self._investigate_target = None
        self._last_known_player_pos = None
        self._patrol_points = []
        self._patrol_idx = 0
        self._suspicion_timer = 0.0
        self._anim_frame = 0
        self._anim_timer = 0.0

    def goto(self, *args):
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, str):
                x, y = self._resolve_ref(arg)
                if x is not None:
                    self._target_x, self._target_y = x, y
                    return
            try:
                x, y = arg
                self._target_x, self._target_y = x, y
            except (TypeError, ValueError):
                pass
        elif len(args) == 2:
            self._target_x, self._target_y = args[0], args[1]

    def lookto(self, *args):
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, str):
                x, y = self._resolve_ref(arg)
                if x is not None:
                    self._look_x, self._look_y = x, y
                    return
            try:
                x, y = arg
                self._look_x, self._look_y = x, y
            except (TypeError, ValueError):
                pass
        elif len(args) == 2:
            self._look_x, self._look_y = args[0], args[1]

    def light(self, on):
        self.light_on = bool(on)

    def start_func(self, func):
        self._func = func
        self._target_x = None
        self._target_y = None
        self._look_x = None
        self._look_y = None
        self._wait_remaining = 0.0
        self._tick_timer = 0.0

    def stop(self):
        self._func = None
        self._target_x = None
        self._target_y = None
        self._look_x = None
        self._look_y = None
        self._wait_remaining = 0.0
        self._tick_timer = 0.0
        self._path = []
        self._follow_target = None
        self._guard_target = None
        self._say_text = None

    def distance_to(self, x, y):
        return math.hypot(self.x - x, self.y - y)

    def wait(self, seconds):
        self._wait_remaining = seconds

    def rate(self, hz):
        self._tick_interval = 1.0 / hz if hz > 0 else 0.0

    def set_state(self, state):
        self.state = state

    def on(self, event, callback):
        self._handlers.setdefault(event, []).append(callback)

    def emit(self, event, *args):
        for cb in self._handlers.get(event, []):
            cb(self, *args)

    def follow_path(self, path):
        self._path = list(path)
        self._path_idx = 0
        self.state = "patrol"
        if self._path:
            self.goto(self._path[0][0], self._path[0][1])

    def follow(self, ref):
        self._follow_target = ref
        self.state = "follow"

    def guard(self, ref, radius=2.0):
        self._guard_target = ref
        self._guard_radius = radius
        self.state = "guard"

    def say(self, text, duration=2.0):
        self._say_text = text
        self._say_timer = duration

    def set_patrol(self, points):
        self._patrol_points = list(points)
        self._patrol_idx = 0
        self.state = "patrol"
        if self._patrol_points:
            self.goto(self._patrol_points[0][0], self._patrol_points[0][1])

    def investigate(self, x, y):
        self._investigate_target = (x, y)
        self.state = "investigate"
        self.goto(x, y)

    def _resolve_ref(self, ref):
        if self.engine is None or not isinstance(ref, str):
            return None, None
        type_name = ref.strip().lower()
        lid = 0
        if '#' in ref:
            parts = ref.split('#', 1)
            type_name = parts[0].strip().lower()
            lid = int(parts[1])
        if type_name in ('stat', 'static'):
            for l in self.engine.static_lights:
                if l.lid == lid:
                    return l.x, l.y
        elif type_name in ('dinam', 'dynamic', 'dyn'):
            for o in self.engine.dynamic_objects:
                if o.lid == lid:
                    return o.x, o.y
        elif type_name == 'bot':
            for b in self.engine.bots:
                if b.lid == lid:
                    return b.x, b.y
        elif type_name == 'player':
            return self.engine.player_x, self.engine.player_y
        return None, None

    def light_xy(self, *args):
        if len(args) == 1:
            arg = args[0]
            x, y = self._resolve_ref(arg)
            if x is None and y is None:
                try:
                    x, y = arg
                except (TypeError, ValueError):
                    return
            self.lookto(x, y)
        elif len(args) == 2:
            self.lookto(args[0], args[1])

    def wot(self, *args):
        if self.engine is None:
            return False
        if len(args) == 1:
            x, y = self._resolve_ref(args[0])
        elif len(args) == 2:
            x, y = args[0], args[1]
        else:
            return False
        if x is None or y is None:
            return False
        fx = self.x * self.engine.cell_size + self.engine.cell_size / 2
        fy = self.y * self.engine.cell_size + self.engine.cell_size / 2
        tx = x * self.engine.cell_size + self.engine.cell_size / 2
        ty = y * self.engine.cell_size + self.engine.cell_size / 2
        target_dist = math.hypot(tx - fx, ty - fy)
        if target_dist < 1:
            return False
        return not self.engine._has_line_of_sight(fx, fy, tx, ty, target_dist + self.engine.cell_size)

    def _update_ai_state(self, dt):
        if self.engine is None:
            return

        px = self.engine.player_x
        py = self.engine.player_y
        dist_to_player = self.distance_to(px, py)
        vision_range = 6.0

        can_see_player = False
        if dist_to_player < vision_range:
            fx = self.x * self.engine.cell_size + self.engine.cell_size / 2
            fy = self.y * self.engine.cell_size + self.engine.cell_size / 2
            tx = px * self.engine.cell_size + self.engine.cell_size / 2
            ty = py * self.engine.cell_size + self.engine.cell_size / 2
            fov_dx = math.cos(self.angle)
            fov_dy = math.sin(self.angle)
            to_player_dx = tx - fx
            to_player_dy = ty - fy
            dist_px = math.hypot(to_player_dx, to_player_dy)
            if dist_px > 0:
                dot = (to_player_dx * fov_dx + to_player_dy * fov_dy) / dist_px
                if dot > 0.3:
                    max_dist_px = vision_range * self.engine.cell_size
                    can_see_player = self.engine._has_line_of_sight(fx, fy, tx, ty, max_dist_px + self.engine.cell_size)

        if can_see_player:
            self._alert_level = min(1.0, self._alert_level + dt * 2.0)
            self._last_known_player_pos = (px, py)
            if self._alert_level >= 0.5:
                self.state = "alert"
                self.goto(px, py)
                if self.engine.logger:
                    self.engine.logger.event("BOT_ALERT", f"Bot#{self.lid} spotted player at ({px:.1f},{py:.1f})")
        else:
            if self._alert_level > 0:
                self._alert_level = max(0, self._alert_level - dt * 0.5)
                if self._alert_level < 0.3 and self.state == "alert":
                    if self._last_known_player_pos:
                        self.state = "investigate"
                        self.investigate(self._last_known_player_pos[0], self._last_known_player_pos[1])
                        if self.engine.logger:
                            self.engine.logger.event("BOT_INVESTIGATE", f"Bot#{self.lid} investigating last known position")
                    else:
                        self.state = "patrol"
                        self._alert_level = 0

        if self.state == "investigate" and self._investigate_target:
            ix, iy = self._investigate_target
            if self.distance_to(ix, iy) < 0.5:
                self._investigate_target = None
                self._last_known_player_pos = None
                self._alert_level = 0
                if self._patrol_points:
                    self.state = "patrol"
                    self.goto(self._patrol_points[0][0], self._patrol_points[0][1])
                else:
                    self.state = "idle"

        if self.state == "idle" and self._patrol_points:
            self.state = "patrol"

        if self.state == "patrol" and not self._path and self._patrol_points:
            self._path = self._patrol_points
            self._path_idx = 0
            if self._path:
                self.goto(self._path[0][0], self._path[0][1])

    def update(self, dt):
        self._anim_timer += dt
        if self._anim_timer > 0.15:
            self._anim_timer -= 0.15
            self._anim_frame = (self._anim_frame + 1) % 4

        self._update_ai_state(dt)

        if self._say_timer > 0:
            self._say_timer -= dt
            if self._say_timer <= 0:
                self._say_text = None
                self._say_timer = 0.0
        if self._wait_remaining > 0:
            self._wait_remaining -= dt
            if self._wait_remaining < 0:
                self._wait_remaining = 0.0
            if self._wait_remaining > 0:
                return
        if self._func:
            if self._tick_interval > 0:
                self._tick_timer += dt
                if self._tick_timer >= self._tick_interval:
                    self._tick_timer -= self._tick_interval
                    self._func(self, dt)
            else:
                self._func(self, dt)
        if self._follow_target:
            x, y = self._resolve_ref(self._follow_target)
            if x is not None:
                self.goto(x, y)
        if self._guard_target:
            x, y = self._resolve_ref(self._guard_target)
            if x is not None and self.distance_to(x, y) > self._guard_radius:
                self.goto(x, y)
        if self._look_x is not None and self._look_y is not None:
            dx = self._look_x - self.x
            dy = self._look_y - self.y
            if dx != 0 or dy != 0:
                self.angle = math.atan2(dy, dx)
        if self._target_x is not None and self._target_y is not None:
            dx = self._target_x - self.x
            dy = self._target_y - self.y
            dist = math.hypot(dx, dy)
            if dist > 0.2:
                self.x += (dx / dist) * self.speed * dt
                self.y += (dy / dist) * self.speed * dt
                if self._look_x is None:
                    self.angle = math.atan2(dy, dx)
            else:
                self.x = self._target_x
                self.y = self._target_y
                self._target_x = None
                self._target_y = None
                if self._path:
                    self._path_idx += 1
                    if self._path_idx < len(self._path):
                        self.goto(self._path[self._path_idx][0], self._path[self._path_idx][1])
                    else:
                        self._path = []

    def moved(self):
        return True

    def draw(self, screen, cell_size, camera_x, camera_y):
        sx = self.x * cell_size - camera_x
        sy = self.y * cell_size - camera_y
        frames = self.engine._sprite_cache.get("bot") if self.engine else None
        if frames:
            n = len(frames)
            idx = int((self.angle / (2 * math.pi)) * n + 0.5) % n
            sprite = frames[idx]
            scale = max(1, int(cell_size * 0.85))
            scaled = pygame.transform.scale(sprite, (scale, scale))
            sr = scaled.get_rect(center=(int(sx), int(sy)))
            screen.blit(scaled, sr)

            if self.state == "alert":
                warn_r = scale // 2 + 4
                pygame.draw.circle(screen, (255, 0, 0, int(100 + 155 * (0.5 + 0.5 * math.sin(time_mod.time() * 8)))), (int(sx), int(sy)), warn_r, 2)

            if self._say_text and self._say_timer > 0:
                if not hasattr(self, '_say_font'):
                    self._say_font = pygame.font.Font(None, 14)
                text_surf = self._say_font.render(self._say_text, True, (255, 255, 255))
                if text_surf:
                    screen.blit(text_surf, (int(sx - text_surf.get_width() / 2), int(sy - scale // 2 - 14)))
            return

        r = int(cell_size * 0.38)

        alert_pulse = 0.7 + 0.3 * math.sin(time_mod.time() * 4) if self.state == "alert" else 1.0
        dc = tuple(int(c * alert_pulse) for c in self.color)
        pygame.draw.circle(screen, dc, (int(sx), int(sy)), r)
        if self.light_on:
            light_pulse = 0.85 + 0.15 * math.sin(time_mod.time() * 3 + self.lid)
            lc = tuple(min(255, int(c * light_pulse)) for c in self.color)
            pygame.draw.circle(screen, lc, (int(sx), int(sy)), r + 3, 1)

        if self.state == "alert":
            warn_alpha = int(100 + 155 * (0.5 + 0.5 * math.sin(time_mod.time() * 8)))
            pygame.draw.circle(screen, (255, 0, 0, warn_alpha), (int(sx), int(sy)), r + 6, 2)

        if self._say_text and self._say_timer > 0:
            if not hasattr(self, '_say_font'):
                self._say_font = pygame.font.Font(None, 16)
            text_surf = self._say_font.render(self._say_text, True, (255, 255, 255))
            if text_surf:
                screen.blit(text_surf, (int(sx - text_surf.get_width() / 2), int(sy - r - 20)))


class StaticLight:
    __slots__ = (
        'x', 'y', 'radius_cells', 'intensity', 'color',
        '_cached_light_surface', '_last_cache_key',
        'phase', 'flicker_offset', 'lid',
    )

    def __init__(self, x, y, radius_cells, intensity=1.0, color=(255, 255, 200), lid=-1):
        self.x = x
        self.y = y
        self.radius_cells = radius_cells
        self.intensity = intensity
        self.color = color
        self.lid = lid
        self._cached_light_surface = None
        self._last_cache_key = None
        self.phase = random.uniform(0, math.pi * 2)
        self.flicker_offset = random.uniform(0.9, 1.1)

    def update(self, dt):
        self.phase += dt * random.uniform(1.5, 4.0)


class DustParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.size = random.uniform(1, 2.5)
        self.brightness = random.randint(120, 220)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx += random.uniform(-2, 2) * dt
        self.vy += random.uniform(-2, 2) * dt
        self.vx *= 0.99
        self.vy *= 0.99

    def draw(self, screen, camera_x, camera_y):
        sx = int(self.x - camera_x)
        sy = int(self.y - camera_y)
        if 0 <= sx <= screen.get_width() and 0 <= sy <= screen.get_height():
            alpha = int(self.brightness)
            color = (alpha, alpha, alpha, alpha)
            pygame.draw.circle(screen, color, (sx, sy), max(1, int(self.size)))


class LightEngine:
    def __init__(self, quality="normal", network_mode=None, server_host=None):
        self.network_mode = network_mode
        self.server_host = server_host
        self.quality = quality
        self.load_config()
        self.quality = quality
        self.apply_quality_preset()

        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        mode_str = ""
        if self.network_mode == "server":
            mode_str = " [SERVER]"
        elif self.network_mode == "client":
            mode_str = " [CLIENT]"
        pygame.display.set_caption(f"LightEngine v5.0.0{mode_str}")
        self.clock = pygame.time.Clock()
        self.debug = False
        self.semi_debug = False
        self.ray_debug = False
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        self.profiler = Profiler()
        self.logger = Logger(enabled=True)
        self.logger.event("INIT", "LightEngine v4.0.0 started")

        self.player_x = self.spawn_x + 0.5
        self.player_y = self.spawn_y + 0.5
        self.player_angle = 0.0
        self.player_light_intensity = 1.0

        self.ray_step = math.radians(self.ray_step_deg)
        self._sin_cache = {}
        self._cos_cache = {}
        self._los_cache = {}
        self._last_los_player_cell = None
        self._obj_lit_cache = {}
        self.bots = []
        self.player_light_on = True
        self._pressed_keys = set()
        self.load_map()
        self.load_static_lights()
        self.load_dynamic_objects()
        self.load_bots()
        self.init_particles()
        self.init_weather()
        self._precompute_static_wall_light()

        self._init_sprites()

        self.light_gradient_cache = OrderedDict()
        self.max_gradient_cache = self.gradient_cache_size

        self._empty_surface = pygame.Surface((1, 1))
        self._empty_surface.fill((0, 0, 0))

        self._last_camera = (-1, -1)
        self._cached_start_x = 0
        self._cached_end_x = 0
        self._cached_start_y = 0
        self._cached_end_y = 0

        self._illumination_map = pygame.Surface((self.screen_width, self.screen_height))
        self._light_work_surface = pygame.Surface((self.screen_width, self.screen_height))

        self._tps_timer = 0.0
        self._tick_count = 0
        self._current_tps = 0

        self._floor_colors = self._generate_floor_colors()

        self.day_cycle_time = 0.0
        self.day_cycle_speed = 0.02
        self.weather_type = "none"
        self.weather_particles = []

        self._ray_debug_lines = []

        self._hot_reload_timer = 0.0
        self._last_config_mtime = self._get_config_mtime()

        self.fog_explored = [[False] * self.grid_size for _ in range(self.grid_size)]
        self.fog_visible = set()
        if not self.fog_of_war:
            for y in range(self.grid_size):
                for x in range(self.grid_size):
                    self.fog_explored[y][x] = True

        self.logger.event("INIT", f"Map: {self.map_file}, Quality: {quality}, Weather: {self.weather_enabled}, Day/Night: {self.day_night_enabled}, Fog: {self.fog_of_war}")

        # Network setup
        self._client = None
        self._server = None
        if self.network_mode == "server":
            import network as net
            self._server = net.GameServer(self)
            self._server.start()
            self.logger.event("NET", "Server mode started")
        elif self.network_mode == "client" and self.server_host:
            import network as net
            self._client = net.GameClient(host=self.server_host)
            if self._client.connect():
                self.logger.event("NET", f"Connected to {self.server_host}")
            else:
                self.logger.event("NET", f"Failed to connect to {self.server_host}")
                self._client = None

    def _get_config_mtime(self):
        try:
            return os.path.getmtime("config.json")
        except OSError:
            return 0

    def _generate_floor_colors(self):
        colors = {}
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                if self.map_grid[y][x] == 1:
                    h = hash((x, y)) & 0xFF
                    colors[(x, y)] = (65 + h // 8, 60 + h // 8, 55 + h // 10)
                else:
                    h = hash((x * 7, y * 13)) & 0x7F
                    colors[(x, y)] = (90 + h // 4, 85 + h // 5, 80 + h // 6)
        return colors

    def load_config(self):
        config_file = "config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
            self.map_file = data.get("map_file", "maps/default.json")
            self.spawn_x = data.get("spawn_x", 10)
            self.spawn_y = data.get("spawn_y", 10)
            self.player_speed = data.get("player_speed", 5.0)
            self.screen_width = data.get("screen_width", 600)
            self.screen_height = data.get("screen_height", 600)
            self.cell_size = self.screen_width // 20
            self.screen_width = 20 * self.cell_size
            self.screen_height = 20 * self.cell_size
            self.quality = data.get("quality", self.quality)
            self.player_light_radius = data.get("player_light_radius", 8)
            self.fov_angle_deg = data.get("fov_angle_deg", 90)
            self.fov_angle = math.radians(self.fov_angle_deg)
        else:
            self.map_file = "maps/default.json"
            self.spawn_x = 10
            self.spawn_y = 10
            self.player_speed = 5.0
            self.screen_width = 600
            self.screen_height = 600
            self.cell_size = 30
            self.player_light_radius = 8
            self.fov_angle_deg = 90
            self.fov_angle = math.radians(self.fov_angle_deg)

    def hot_reload_config(self):
        current_mtime = self._get_config_mtime()
        if current_mtime != self._last_config_mtime:
            self._last_config_mtime = current_mtime
            try:
                with open("config.json", 'r') as f:
                    data = json.load(f)
                old_quality = self.quality
                self.player_speed = data.get("player_speed", self.player_speed)
                self.player_light_radius = data.get("player_light_radius", self.player_light_radius)
                self.fov_angle_deg = data.get("fov_angle_deg", math.degrees(self.fov_angle))
                self.fov_angle = math.radians(self.fov_angle_deg)
                new_quality = data.get("quality", self.quality)
                if new_quality != old_quality:
                    self.quality = new_quality
                    self.apply_quality_preset()
                    self.init_weather()
                    self.ray_step = math.radians(self.ray_step_deg)
                self.logger.event("HOT_RELOAD", "config.json reloaded")
            except Exception as e:
                self.logger.event("HOT_RELOAD_ERROR", str(e))

    def apply_quality_preset(self):
        preset = QUALITY_PRESETS.get(self.quality, QUALITY_PRESETS["normal"])
        print(f"using quality: {self.quality}")
        self.ray_step_deg = preset["ray_step_deg"]
        self.cast_step = preset["cast_step"]
        self.gradient_resolution = preset["gradient_resolution"]
        self.gradient_cache_size = preset["gradient_cache_size"]
        self.max_dynamic_lights = preset["max_dynamic_lights"]
        self.max_static_lights = preset["max_static_lights"]
        self.max_dynamic_objects = preset["max_dynamic_objects"]
        self.colored_lights_enabled = preset["colored_lights"]
        self.particles_enabled = preset["particles"]
        self.flicker_enabled = preset["flicker"]
        self.ambient_light = preset["ambient_light"]
        self.weather_enabled = preset["weather"]
        self.day_night_enabled = preset["day_night"]
        self.fog_of_war = preset.get("fog_of_war", True)

    def load_static_lights(self):
        if self._map_static_lights:
            count = len(self._map_static_lights)
            if count > self.max_static_lights:
                print(f"to much light static obj ({count} in map file) max count {self.max_static_lights}!!")
                self._map_static_lights = self._map_static_lights[:self.max_static_lights]
            print(f"static lights obj loaded: {len(self._map_static_lights)}")
            self.static_lights = [
                StaticLight(l["x"], l["y"], l["radius_cells"], l["intensity"],
                            tuple(l["color"]), lid=l.get("id", i))
                for i, l in enumerate(self._map_static_lights)
            ]
        else:
            default_static = [
                (5, 5, 4, 0.8, (255, 200, 130)),
                (15, 12, 3, 0.6, (130, 180, 255)),
                (8, 16, 5, 0.9, (255, 240, 160)),
                (3, 8, 2, 0.5, (180, 255, 180)),
                (17, 4, 2, 0.5, (255, 160, 160)),
            ]
            self.static_lights = [StaticLight(*args, lid=i) for i, args in enumerate(default_static)]
            print(f"static lights obj loaded: {len(self.static_lights)} (default)")

    def load_dynamic_objects(self):
        if self._map_dynamic_objects:
            count = len(self._map_dynamic_objects)
            if count > self.max_dynamic_objects:
                print(f"to much light dynamic obj ({count} in map file) max count {self.max_dynamic_objects}!!")
                self._map_dynamic_objects = self._map_dynamic_objects[:self.max_dynamic_objects]
            print(f"dynamic objects obj loaded: {len(self._map_dynamic_objects)}")
            self.dynamic_objects = []
            for i, o in enumerate(self._map_dynamic_objects):
                obj = DynamicObject(o["x"], o["y"], light_radius=o["light_radius"],
                                    light_intensity=o["light_intensity"],
                                    color=tuple(o["color"]), lid=o.get("id", i))
                obj.engine = self
                self.dynamic_objects.append(obj)
        else:
            default_dyn = [
                (12, 10, 2, 0.5, (220, 80, 80)),
                (7, 14, 1.5, 0.4, (80, 220, 80)),
                (4, 4, 1.5, 0.35, (220, 220, 80)),
            ]
            self.dynamic_objects = []
            for i, (x, y, lr, li, c) in enumerate(default_dyn):
                obj = DynamicObject(x, y, light_radius=lr, light_intensity=li, color=c, lid=i)
                obj.engine = self
                self.dynamic_objects.append(obj)
            print(f"dynamic objects obj loaded: {len(self.dynamic_objects)} (default)")

    def load_bots(self):
        self.bots = []
        if self._map_bots:
            for b in self._map_bots:
                bot = Bot(
                    b["x"], b["y"],
                    light_radius=b.get("light_radius", 2),
                    light_intensity=b.get("light_intensity", 0.5),
                    color=tuple(b.get("color", (0, 100, 255))),
                    speed=b.get("speed", 2.0),
                    lid=b.get("id", len(self.bots)),
                )
                bot.engine = self
                patrol = b.get("patrol", [])
                if patrol:
                    bot.set_patrol(patrol)
                self.bots.append(bot)
            print(f"bots loaded: {len(self.bots)}")

    def init_particles(self):
        self.particles = []
        if not self.particles_enabled:
            return
        for _ in range(80):
            x = random.uniform(0, self.grid_size * self.cell_size)
            y = random.uniform(0, self.grid_size * self.cell_size)
            self.particles.append(DustParticle(x, y))

    def _init_sprites(self):
        self._sprite_cache = {}
        sheet_order = [
            ("player", "arrow", (0, 220, 0), 8),
            ("bot", "arrow", (0, 100, 255), 8),
            ("object", "diamond", (200, 100, 50), 4),
        ]
        for name, shape, default_color, n in sheet_order:
            frames = load_sprite_sheet(f"{name}.png", SPRITE_SIZE, SPRITE_SIZE)
            if frames is None:
                frames = gen_sprite_frames(default_color, shape, n, SPRITE_SIZE)
            self._sprite_cache[name] = frames

    def init_weather(self):
        self.weather_particles = []
        if not self.weather_enabled:
            return
        self.weather_type = random.choice(["rain", "snow", "fog"])
        count = {"rain": 300, "snow": 150, "fog": 20}.get(self.weather_type, 0)
        for _ in range(count):
            x = random.uniform(0, self.grid_size * self.cell_size)
            y = random.uniform(0, self.grid_size * self.cell_size)
            self.weather_particles.append(WeatherParticle(x, y, self.weather_type))
        self.logger.event("WEATHER", f"Weather initialized: {self.weather_type} ({len(self.weather_particles)} particles)")

    def load_map(self):
        self.map_grid = [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        ]
        self.grid_size = len(self.map_grid)
        self._map_static_lights = None
        self._map_dynamic_objects = None
        self._map_bots = None

        if os.path.exists(self.map_file):
            with open(self.map_file, 'r') as f:
                data = json.load(f)
            if "map" in data:
                self.map_grid = data["map"]
                self.grid_size = len(self.map_grid)
            if "player_spawn" in data:
                self.spawn_x, self.spawn_y = data["player_spawn"]
                self.player_x = self.spawn_x + 0.5
                self.player_y = self.spawn_y + 0.5
            if "static_lights" in data:
                self._map_static_lights = data["static_lights"]
            if "dynamic_objects" in data:
                self._map_dynamic_objects = data["dynamic_objects"]
            if "bots" in data:
                self._map_bots = data["bots"]
            print(f"current map: {self.map_file} ({self.grid_size}x{self.grid_size})")

    def _fast_sin_cos(self, angle):
        key = int(angle * 1000)
        if key not in self._sin_cache:
            self._sin_cache[key] = math.sin(angle)
            self._cos_cache[key] = math.cos(angle)
        return self._cos_cache[key], self._sin_cache[key]

    def cast_ray(self, px, py, angle, max_dist_px, ignore_walls=False, cos_a=None, sin_a=None):
        step = self.cast_step
        dist = 0
        if cos_a is None or sin_a is None:
            cos_a, sin_a = self._fast_sin_cos(angle)
        points = [(px, py)]
        while dist < max_dist_px:
            x = px + cos_a * dist
            y = py + sin_a * dist
            cx = int(x // self.cell_size)
            cy = int(y // self.cell_size)
            if cx < 0 or cx >= self.grid_size or cy < 0 or cy >= self.grid_size:
                points.append((x, y))
                if self.ray_debug:
                    self._ray_debug_lines.append((px, py, x, y))
                return (x, y)
            if not ignore_walls and self.map_grid[cy][cx] == 1:
                prev_x = px + cos_a * (dist - step)
                prev_y = py + sin_a * (dist - step)
                points.append((prev_x, prev_y))
                if self.ray_debug:
                    self._ray_debug_lines.append((px, py, prev_x, prev_y))
                return (prev_x, prev_y)
            dist += step
        x = px + cos_a * max_dist_px
        y = py + sin_a * max_dist_px
        points.append((x, y))
        if self.ray_debug:
            self._ray_debug_lines.append((px, py, x, y))
        return (x, y)

    def can_move_to(self, x, y):
        cell_x = int(x)
        cell_y = int(y)
        if cell_x < 0 or cell_x >= self.grid_size or cell_y < 0 or cell_y >= self.grid_size:
            return False
        if self.map_grid[cell_y][cell_x] == 1:
            return False
        fx, fy = x - cell_x, y - cell_y
        if fx < 0.2 and cell_x - 1 >= 0 and self.map_grid[cell_y][cell_x - 1] == 1:
            return False
        if fx > 0.8 and cell_x + 1 < self.grid_size and self.map_grid[cell_y][cell_x + 1] == 1:
            return False
        if fy < 0.2 and cell_y - 1 >= 0 and self.map_grid[cell_y - 1][cell_x] == 1:
            return False
        if fy > 0.8 and cell_y + 1 < self.grid_size and self.map_grid[cell_y + 1][cell_x] == 1:
            return False
        return True

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        self._pressed_keys = set()
        if keys[pygame.K_w]:
            self._pressed_keys.add("w")
            move_y = -1
        else:
            move_y = 0
        if keys[pygame.K_s]:
            self._pressed_keys.add("s")
            move_y += 1
        if keys[pygame.K_a]:
            self._pressed_keys.add("a")
            move_x = -1
        else:
            move_x = 0
        if keys[pygame.K_d]:
            self._pressed_keys.add("d")
            move_x += 1

        if move_x != 0 or move_y != 0:
            length = math.hypot(move_x, move_y)
            move_x /= length
            move_y /= length
            new_x = self.player_x + move_x * self.player_speed * dt
            new_y = self.player_y + move_y * self.player_speed * dt
            if self.can_move_to(new_x, self.player_y):
                self.player_x = new_x
            if self.can_move_to(self.player_x, new_y):
                self.player_y = new_y
            self.player_x = max(0.5, min(self.grid_size - 0.5, self.player_x))
            self.player_y = max(0.5, min(self.grid_size - 0.5, self.player_y))

        mouse_x, mouse_y = pygame.mouse.get_pos()
        cam_x = self.player_x * self.cell_size - self.screen_width // 2
        cam_y = self.player_y * self.cell_size - self.screen_height // 2
        cam_x = max(0, min(cam_x, self.grid_size * self.cell_size - self.screen_width))
        cam_y = max(0, min(cam_y, self.grid_size * self.cell_size - self.screen_height))
        world_mouse_x = (mouse_x + cam_x) / self.cell_size
        world_mouse_y = (mouse_y + cam_y) / self.cell_size
        dx = world_mouse_x - self.player_x
        dy = world_mouse_y - self.player_y
        if dx != 0 or dy != 0:
            self.player_angle = math.atan2(dy, dx)

    def get_visible_cells_range(self, camera_x, camera_y):
        if (camera_x, camera_y) == self._last_camera:
            return self._cached_start_x, self._cached_end_x, self._cached_start_y, self._cached_end_y

        self._last_camera = (camera_x, camera_y)
        self._cached_start_x = max(0, camera_x // self.cell_size)
        self._cached_end_x = min(self.grid_size, (camera_x + self.screen_width + self.cell_size - 1) // self.cell_size)
        self._cached_start_y = max(0, camera_y // self.cell_size)
        self._cached_end_y = min(self.grid_size, (camera_y + self.screen_height + self.cell_size - 1) // self.cell_size)
        return self._cached_start_x, self._cached_end_x, self._cached_start_y, self._cached_end_y

    def draw_scene(self, screen, camera_x, camera_y):
        start_x, end_x, start_y, end_y = self.get_visible_cells_range(camera_x, camera_y)
        day_factor = self.get_day_factor()
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                screen_x = x * self.cell_size - camera_x
                screen_y = y * self.cell_size - camera_y
                base_color = self._floor_colors.get((x, y), (80, 80, 80))
                dist = math.hypot(x - self.player_x + 0.5, y - self.player_y + 0.5)
                shade = max(0.6, min(1.0, 1.8 / (dist + 0.3)))
                color = tuple(int(c * shade) for c in base_color)
                color = tuple(int(c * day_factor) for c in color)
                pygame.draw.rect(screen, color, (screen_x, screen_y, self.cell_size, self.cell_size))

    def draw_player(self, screen, camera_x, camera_y):
        screen_x = int(self.player_x * self.cell_size - camera_x)
        screen_y = int(self.player_y * self.cell_size - camera_y)
        frames = self._sprite_cache.get("player")
        if frames:
            n = len(frames)
            idx = int((self.player_angle / (2 * math.pi)) * n + 0.5) % n
            sprite = frames[idx]
            scale = max(1, int(self.cell_size * 0.8))
            scaled = pygame.transform.scale(sprite, (scale, scale))
            sr = scaled.get_rect(center=(screen_x, screen_y))
            screen.blit(scaled, sr)
            return
        pygame.draw.circle(screen, (0, 240, 0), (screen_x, screen_y), self.cell_size // 3)
        end_x = screen_x + math.cos(self.player_angle) * self.cell_size
        end_y = screen_y + math.sin(self.player_angle) * self.cell_size
        pygame.draw.line(screen, (255, 60, 60), (screen_x, screen_y), (end_x, end_y), 2)

    def update_fog(self):
        if not self.fog_of_war:
            return
        self.fog_visible.clear()
        px = self.player_x * self.cell_size + self.cell_size / 2
        py = self.player_y * self.cell_size + self.cell_size / 2
        max_dist = self.player_light_radius * self.cell_size
        start_angle = self.player_angle - self.fov_angle / 2
        num_rays = max(6, int(self.fov_angle / self.ray_step) + 1)
        for i in range(num_rays):
            angle = start_angle + i * self.ray_step
            cos_a, sin_a = self._fast_sin_cos(angle)
            dist = 0
            while dist < max_dist:
                fx = px + cos_a * dist
                fy = py + sin_a * dist
                cx = int(fx // self.cell_size)
                cy = int(fy // self.cell_size)
                if 0 <= cx < self.grid_size and 0 <= cy < self.grid_size:
                    self.fog_explored[cy][cx] = True
                    self.fog_visible.add((cx, cy))
                    if self.map_grid[cy][cx] == 1:
                        break
                else:
                    break
                dist += self.cast_step

    def draw_fog_overlay(self, screen, camera_x, camera_y):
        if not self.fog_of_war:
            return
        start_x, end_x, start_y, end_y = self.get_visible_cells_range(camera_x, camera_y)
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if not self.fog_explored[y][x]:
                    sx = x * self.cell_size - camera_x
                    sy = y * self.cell_size - camera_y
                    pygame.draw.rect(screen, (0, 0, 0), (sx, sy, self.cell_size, self.cell_size))
                elif (x, y) not in self.fog_visible:
                    sx = x * self.cell_size - camera_x
                    sy = y * self.cell_size - camera_y
                    dim = pygame.Surface((self.cell_size, self.cell_size))
                    dim.set_alpha(180)
                    dim.fill((0, 0, 0))
                    screen.blit(dim, (sx, sy))

    def _is_light_visible_on_screen(self, sx, sy, radius_px):
        return not (sx + radius_px < 0 or sx - radius_px > self.screen_width
                    or sy + radius_px < 0 or sy - radius_px > self.screen_height)

    def _get_contribution_gradient(self, radius_px, intensity, color=None):
        use_color = self.colored_lights_enabled and color is not None
        if use_color:
            q = 16
            key = (radius_px, int(intensity * 10), color[0] // q, color[1] // q, color[2] // q)
        else:
            key = (radius_px, int(intensity * 10))

        if key in self.light_gradient_cache:
            self.light_gradient_cache.move_to_end(key)
            return self.light_gradient_cache[key]

        size = radius_px * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (radius_px, radius_px)

        if use_color:
            max_color = tuple(min(255, int(c * intensity)) for c in color)
        else:
            b = min(255, int(255 * intensity))
            max_color = (b, b, b)

        step = max(1, radius_px // self.gradient_resolution)
        edge_fade = 0.25
        for r in range(radius_px, 0, -step):
            factor = r / radius_px
            smooth = 1 - factor
            col = tuple(int(mc * smooth) for mc in max_color)
            if factor > (1 - edge_fade):
                alpha = int(255 * (1 - factor) / edge_fade)
            else:
                alpha = 255
            pygame.draw.circle(surf, col + (alpha,), center, r)

        pygame.draw.circle(surf, max_color + (255,), center, step)

        if len(self.light_gradient_cache) >= self.max_gradient_cache:
            self.light_gradient_cache.popitem(last=False)
        self.light_gradient_cache[key] = surf
        return surf

    def _get_light_contribution(self, world_x, world_y, radius_cells, intensity,
                                camera_x, camera_y, color=None,
                                angle=None, fov_angle=None, for_cache=False):
        max_dist_px = radius_cells * self.cell_size
        radius_px = int(max_dist_px)
        sx = world_x - camera_x
        sy = world_y - camera_y

        if not self._is_light_visible_on_screen(sx, sy, radius_px):
            return self._empty_surface

        flicker_radius_px = radius_px
        flicker_intensity = intensity
        flicker_bucket = 0
        if self.flicker_enabled:
            flicker = 0.93 + 0.07 * math.sin(self._flicker_time * 2.0 + hash((world_x, world_y)) % 100)
            flicker_radius_px = max(1, int(max_dist_px * flicker))
            flicker_intensity = intensity * (0.92 + 0.08 * flicker)
            flicker_bucket = int(flicker * 5)

        self._light_work_surface.fill((0, 0, 0))

        if angle is not None and fov_angle is not None:
            start_angle = angle - fov_angle / 2
            num_rays = max(8, int(fov_angle / self.ray_step) + 1)
        else:
            start_angle = 0
            num_rays = max(12, int(2 * math.pi / self.ray_step) + 1)

        cos_arr = [math.cos(start_angle + i * self.ray_step) for i in range(num_rays)]
        sin_arr = [math.sin(start_angle + i * self.ray_step) for i in range(num_rays)]
        points = [(sx, sy)]
        for i in range(num_rays):
            hx, hy = self.cast_ray(world_x, world_y, 0, max_dist_px, cos_a=cos_arr[i], sin_a=sin_arr[i])
            points.append((hx - camera_x, hy - camera_y))

        if len(points) >= 3:
            pygame.draw.polygon(self._light_work_surface, (255, 255, 255), points)

        grad_radius = max(radius_px, int(radius_px * 1.15) + 1)
        grad = self._get_contribution_gradient(grad_radius, flicker_intensity, color)
        grad_x = sx - grad_radius
        grad_y = sy - grad_radius
        self._light_work_surface.blit(grad, (grad_x, grad_y), special_flags=pygame.BLEND_RGBA_MULT)

        if for_cache:
            return self._light_work_surface.copy()
        return self._light_work_surface

    def _get_cached_light(self, light_obj, world_x, world_y, radius_cells, intensity,
                          camera_x, camera_y, color=None, angle=None, fov_angle=None):
        flicker_bucket = 0
        if self.flicker_enabled:
            flicker = 0.93 + 0.07 * math.sin(self._flicker_time * 2.0 + hash((world_x, world_y)) % 100)
            flicker_bucket = int(flicker * 5)

        cache_key = (camera_x, camera_y, flicker_bucket)
        if hasattr(light_obj, '_last_cache_key'):
            if light_obj._last_cache_key == cache_key and light_obj._cached_light_surface is not None:
                return light_obj._cached_light_surface

        surf = self._get_light_contribution(
            world_x, world_y, radius_cells, intensity,
            camera_x, camera_y, color, angle, fov_angle,
            for_cache=True,
        )

        light_obj._cached_light_surface = surf
        light_obj._last_cache_key = cache_key
        return surf

    def _has_line_of_sight(self, from_x, from_y, to_x, to_y, max_dist):
        key = (int(from_x // self.cell_size), int(from_y // self.cell_size),
               int(to_x // self.cell_size), int(to_y // self.cell_size))
        if key in self._los_cache:
            return self._los_cache[key]
        angle = math.atan2(to_y - from_y, to_x - from_x)
        hit_x, hit_y = self.cast_ray(from_x, from_y, angle, max_dist + self.cast_step)
        hit_cx = int(hit_x // self.cell_size)
        hit_cy = int(hit_y // self.cell_size)
        target_cx = int(to_x // self.cell_size)
        target_cy = int(to_y // self.cell_size)
        if hit_cx == target_cx and hit_cy == target_cy:
            result = True
        else:
            hit_dist = math.hypot(hit_x - from_x, hit_y - from_y)
            target_dist = math.hypot(to_x - from_x, to_y - from_y)
            result = hit_dist >= target_dist - self.cell_size * 0.85
        self._los_cache[key] = result
        return result

    def _is_obj_lit(self, wx, wy):
        key = (int(wx // self.cell_size), int(wy // self.cell_size))
        if key in self._obj_lit_cache:
            return self._obj_lit_cache[key]
        for light in self.static_lights:
            lx = light.x * self.cell_size + self.cell_size / 2
            ly = light.y * self.cell_size + self.cell_size / 2
            max_d = light.radius_cells * self.cell_size
            if math.hypot(wx - lx, wy - ly) < max_d:
                if self._has_line_of_sight(lx, ly, wx, wy, max_d):
                    self._obj_lit_cache[key] = True
                    return True
        px = self.player_x * self.cell_size
        py = self.player_y * self.cell_size
        ambient_r = 1.5 * self.cell_size
        if math.hypot(wx - px, wy - py) < ambient_r and self._has_line_of_sight(px, py, wx, wy, ambient_r):
            self._obj_lit_cache[key] = True
            return True
        max_d = self.player_light_radius * self.cell_size
        if self.player_light_on and math.hypot(wx - px, wy - py) < max_d:
            if self._has_line_of_sight(px, py, wx, wy, max_d):
                self._obj_lit_cache[key] = True
                return True
        self._obj_lit_cache[key] = False
        return False

    def _precompute_static_wall_light(self):
        self._wall_static_light_cache = {}
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                if self.map_grid[y][x] != 1:
                    continue
                cx = (x + 0.5) * self.cell_size
                cy = (y + 0.5) * self.cell_size
                r = g = b = 0.0
                for light in self.static_lights:
                    lx = light.x * self.cell_size + self.cell_size / 2
                    ly = light.y * self.cell_size + self.cell_size / 2
                    max_d = light.radius_cells * self.cell_size
                    dist = math.hypot(cx - lx, cy - ly)
                    if dist < max_d and self._has_line_of_sight(lx, ly, cx, cy, max_d):
                        falloff = (1 - dist / max_d) ** 2
                        i = light.intensity * falloff
                        lc = light.color if self.colored_lights_enabled else (255, 255, 255)
                        r += lc[0] * i; g += lc[1] * i; b += lc[2] * i
                self._wall_static_light_cache[(x, y)] = (r, g, b)

    def _player_dynamic_at_point(self, wx, wy, dyn_lit):
        r = g = b = 0.0
        px = self.player_x * self.cell_size
        py = self.player_y * self.cell_size
        if not self.player_light_on:
            ambient_max_d = 2.0 * self.cell_size
            ambient_dist = math.hypot(wx - px, wy - py)
            if ambient_dist < ambient_max_d:
                r += 120 * (1 - ambient_dist / ambient_max_d) ** 2
                g += 120 * (1 - ambient_dist / ambient_max_d) ** 2
                b += 120 * (1 - ambient_dist / ambient_max_d) ** 2
        max_d = self.player_light_radius * self.cell_size
        dist = math.hypot(wx - px, wy - py)
        if self.player_light_on and dist < max_d and self._has_line_of_sight(px, py, wx, wy, max_d):
            angle_to = math.atan2(wy - py, wx - px)
            diff = abs((angle_to - self.player_angle + math.pi) % (2 * math.pi) - math.pi)
            if diff < self.fov_angle / 2 + 0.15:
                falloff = (1 - dist / max_d) ** 2
                i = self.player_light_intensity * falloff
                r += 255 * i; g += 255 * i; b += 255 * i
        for idx, obj in enumerate(self.dynamic_objects):
            if obj.light_radius <= 0 or not dyn_lit[idx]:
                continue
            ox = obj.x * self.cell_size
            oy = obj.y * self.cell_size
            max_d = obj.light_radius * self.cell_size
            dist = math.hypot(wx - ox, wy - oy)
            if dist < max_d:
                falloff = (1 - dist / max_d) ** 2
                i = obj.light_intensity * falloff
                oc = obj.color if self.colored_lights_enabled else (255, 255, 255)
                r += oc[0] * i; g += oc[1] * i; b += oc[2] * i
        for bot in self.bots:
            if not bot.light_on or bot.light_radius <= 0:
                continue
            bx = bot.x * self.cell_size
            by = bot.y * self.cell_size
            max_d = bot.light_radius * self.cell_size
            dist = math.hypot(wx - bx, wy - by)
            if dist < max_d:
                falloff = (1 - dist / max_d) ** 2
                i = bot.light_intensity * falloff
                bc = bot.color if self.colored_lights_enabled else (255, 255, 255)
                r += bc[0] * i; g += bc[1] * i; b += bc[2] * i
        return (r, g, b)

    def _draw_wall_borders(self, screen, camera_x, camera_y):
        start_x, end_x, start_y, end_y = self.get_visible_cells_range(camera_x, camera_y)
        subdivs = 4
        spill_passes = 3
        spill_factor = 0.25
        spill_decay = 0.85
        spill_threshold = 3

        dyn_lit = [obj.light_radius > 0 and self._is_obj_lit(
            obj.x * self.cell_size, obj.y * self.cell_size
        ) for obj in self.dynamic_objects]

        edge_segs = {}
        edge_avg = {}

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if self.map_grid[y][x] != 1:
                    continue
                sr, sg, sb = self._wall_static_light_cache.get((x, y), (0.0, 0.0, 0.0))
                sz = self.cell_size
                wx = x * sz
                wy = y * sz

                chk = []
                if y == 0 or self.map_grid[y - 1][x] != 1:
                    chk.append((x, y, 0, wx, wy, wx + sz, wy))
                if y == self.grid_size - 1 or self.map_grid[y + 1][x] != 1:
                    chk.append((x, y, 1, wx, wy + sz, wx + sz, wy + sz))
                if x == 0 or self.map_grid[y][x - 1] != 1:
                    chk.append((x, y, 2, wx, wy, wx, wy + sz))
                if x == self.grid_size - 1 or self.map_grid[y][x + 1] != 1:
                    chk.append((x, y, 3, wx + sz, wy, wx + sz, wy + sz))

                for ex, ey, ed, wxs, wys, wxe, wye in chk:
                    key = (ex, ey, ed)
                    segs = []
                    s_r = s_g = s_b = 0
                    for i in range(subdivs):
                        t = (i + 0.5) / subdivs
                        wmx = wxs + (wxe - wxs) * t
                        wmy = wys + (wye - wys) * t
                        pr, pg, pb = self._player_dynamic_at_point(wmx, wmy, dyn_lit)
                        cr = min(255, int(sr + pr))
                        cg = min(255, int(sg + pg))
                        cb = min(255, int(sb + pb))
                        segs.append((cr, cg, cb))
                        s_r += cr; s_g += cg; s_b += cb
                    edge_segs[key] = segs
                    edge_avg[key] = (s_r // subdivs, s_g // subdivs, s_b // subdivs)

        for pass_num in range(spill_passes):
            decay = spill_decay ** pass_num
            current_avg = dict(edge_avg)
            for key, (ar, ag, ab) in current_avg.items():
                current_bright = (ar + ag + ab) // 3
                if current_bright == 0:
                    continue
                x, y, d = key
                nbrs = [(x - 1, y, d), (x + 1, y, d)] if d in (0, 1) else [(x, y - 1, d), (x, y + 1, d)]
                for nk in nbrs:
                    if nk not in edge_avg:
                        continue
                    nr, ng, nb = edge_avg[nk]
                    neighbor_bright = (nr + ng + nb) // 3
                    if neighbor_bright < current_bright:
                        diff = current_bright - neighbor_bright
                        transfer = min(diff * spill_factor * decay, current_bright * 0.4)
                        if transfer < spill_threshold:
                            continue
                        new_bright = neighbor_bright + transfer
                        if neighbor_bright > 0:
                            weight = transfer / new_bright
                            edge_avg[nk] = (
                                min(255, int(nr * (1 - weight) + ar * weight)),
                                min(255, int(ng * (1 - weight) + ag * weight)),
                                min(255, int(nb * (1 - weight) + ab * weight)),
                            )
                        else:
                            brightness_ratio = transfer / 255
                            edge_avg[nk] = (
                                min(255, int(ar * brightness_ratio)),
                                min(255, int(ag * brightness_ratio)),
                                min(255, int(ab * brightness_ratio)),
                            )

        for key in edge_segs:
            if key not in edge_avg:
                continue
            ar, ag, ab = edge_avg[key]
            segs = edge_segs[key]
            or_ = sum(s[0] for s in segs) // subdivs
            og = sum(s[1] for s in segs) // subdivs
            ob = sum(s[2] for s in segs) // subdivs
            if (or_, og, ob) != (ar, ag, ab):
                for i in range(subdivs):
                    cr, cg, cb = segs[i]
                    if or_ > 0:
                        cr = min(255, int(cr * ar / or_))
                    if og > 0:
                        cg = min(255, int(cg * ag / og))
                    if ob > 0:
                        cb = min(255, int(cb * ab / ob))
                    segs[i] = (cr, cg, cb)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if self.map_grid[y][x] != 1:
                    continue
                sx = x * self.cell_size - camera_x
                sy = y * self.cell_size - camera_y
                sz = self.cell_size
                for d, (xp1, yp1, xp2, yp2) in enumerate([
                    (sx, sy, sx + sz, sy),
                    (sx, sy + sz, sx + sz, sy + sz),
                    (sx, sy, sx, sy + sz),
                    (sx + sz, sy, sx + sz, sy + sz),
                ]):
                    segs = edge_segs.get((x, y, d))
                    if segs is None:
                        continue
                    for i in range(subdivs):
                        col = segs[i]
                        if sum(col) == 0:
                            continue
                        t0 = i / subdivs
                        t1 = (i + 1) / subdivs
                        x1 = xp1 + (xp2 - xp1) * t0
                        y1 = yp1 + (yp2 - yp1) * t0
                        x2 = xp1 + (xp2 - xp1) * t1
                        y2 = yp1 + (yp2 - yp1) * t1
                        pygame.draw.line(screen, col, (int(x1), int(y1)), (int(x2), int(y2)), 2)

    def _light_blit_rect(self, surf, world_x, world_y, radius_cells, camera_x, camera_y):
        sx = world_x - camera_x
        sy = world_y - camera_y
        radius_px = max(1, int(radius_cells * self.cell_size * 1.5))
        blit_rect = pygame.Rect(sx - radius_px, sy - radius_px, radius_px * 2, radius_px * 2)
        blit_rect.clamp_ip(self._illumination_map.get_rect())
        if blit_rect.width <= 0 or blit_rect.height <= 0:
            return
        self._illumination_map.blit(surf, blit_rect, blit_rect, special_flags=pygame.BLEND_RGB_ADD)

    def get_day_factor(self):
        if not self.day_night_enabled:
            return 1.0
        phase = (math.sin(self.day_cycle_time) + 1) / 2
        day_factor = 0.45 + 0.55 * phase
        return day_factor

    def apply_lighting(self, screen, camera_x, camera_y):
        self._illumination_map.fill((0, 0, 0))

        day_factor = self.get_day_factor()

        for light in self.static_lights:
            surf = self._get_cached_light(
                light,
                light.x * self.cell_size + self.cell_size / 2,
                light.y * self.cell_size + self.cell_size / 2,
                light.radius_cells, light.intensity,
                camera_x, camera_y,
                color=light.color if self.colored_lights_enabled else None,
                angle=None, fov_angle=None,
            )
            if surf is not self._empty_surface:
                lx = light.x * self.cell_size + self.cell_size / 2
                ly = light.y * self.cell_size + self.cell_size / 2
                self._light_blit_rect(surf, lx, ly, light.radius_cells, camera_x, camera_y)

        if self.player_light_on:
            player_surf = self._get_light_contribution(
                self.player_x * self.cell_size,
                self.player_y * self.cell_size,
                self.player_light_radius, self.player_light_intensity,
                camera_x, camera_y,
                color=None,
                angle=self.player_angle, fov_angle=self.fov_angle,
            )
            if player_surf is not self._empty_surface:
                px = self.player_x * self.cell_size
                py = self.player_y * self.cell_size
                self._light_blit_rect(player_surf, px, py, self.player_light_radius, camera_x, camera_y)

        if not self.player_light_on:
            ambient_surf = self._get_light_contribution(
                self.player_x * self.cell_size, self.player_y * self.cell_size,
                1.5, 0.35, camera_x, camera_y,
                color=None, angle=None, fov_angle=None,
            )
            if ambient_surf is not self._empty_surface:
                self._light_blit_rect(ambient_surf, self.player_x * self.cell_size, self.player_y * self.cell_size,
                                      1.5, camera_x, camera_y)

        if self.dynamic_objects:
            px = self.player_x * self.cell_size
            py = self.player_y * self.cell_size
            objs = []
            for obj in self.dynamic_objects:
                if obj.light_radius > 0 and self._is_obj_lit(obj.x * self.cell_size, obj.y * self.cell_size):
                    d2 = (obj.x * self.cell_size - px) ** 2 + (obj.y * self.cell_size - py) ** 2
                    objs.append((d2, obj))
            objs.sort(key=lambda x: x[0])
            for _, obj in objs[:self.max_dynamic_lights]:
                if obj.moved():
                    obj._cached_light_surface = None
                surf = self._get_cached_light(
                    obj,
                    obj.x * self.cell_size,
                    obj.y * self.cell_size,
                    obj.light_radius, obj.light_intensity,
                    camera_x, camera_y,
                    color=obj.color if self.colored_lights_enabled else None,
                    angle=None, fov_angle=None,
                )
                if surf is not self._empty_surface:
                    ox = obj.x * self.cell_size
                    oy = obj.y * self.cell_size
                    self._light_blit_rect(surf, ox, oy, obj.light_radius, camera_x, camera_y)

        for bot in self.bots:
            if not bot.light_on or bot.light_radius <= 0:
                continue
            surf = self._get_cached_light(
                bot,
                bot.x * self.cell_size,
                bot.y * self.cell_size,
                bot.light_radius, bot.light_intensity,
                camera_x, camera_y,
                color=bot.color if self.colored_lights_enabled else None,
                angle=None, fov_angle=None,
            )
            if surf is not self._empty_surface:
                self._light_blit_rect(surf, bot.x * self.cell_size, bot.y * self.cell_size,
                                      bot.light_radius, camera_x, camera_y)

        screen.blit(self._illumination_map, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def update_particles(self, dt, camera_x, camera_y):
        if not self.particles_enabled:
            return
        for p in self.particles:
            p.update(dt)
            margin = 100
            sw = self.screen_width
            sh = self.screen_height
            if p.x < camera_x - margin:
                p.x = camera_x + sw + margin
                p.y = random.uniform(camera_y, camera_y + sh)
            elif p.x > camera_x + sw + margin:
                p.x = camera_x - margin
                p.y = random.uniform(camera_y, camera_y + sh)
            if p.y < camera_y - margin:
                p.y = camera_y + sh + margin
            elif p.y > camera_y + sh + margin:
                p.y = camera_y - margin

    def update_weather(self, dt, camera_x, camera_y):
        if not self.weather_enabled or not self.weather_particles:
            return
        day_factor = self.get_day_factor()
        for p in self.weather_particles:
            p.update(dt)
            margin = 200
            sw = self.screen_width
            sh = self.screen_height
            if p.x < camera_x - margin:
                p.x = camera_x + sw + margin
            elif p.x > camera_x + sw + margin:
                p.x = camera_x - margin
            if p.y < camera_y - margin:
                p.y = camera_y + sh + margin
            elif p.y > camera_y + sh + margin:
                p.y = camera_y - margin

    def draw_weather(self, camera_x, camera_y):
        if not self.weather_enabled or not self.weather_particles:
            return
        day_factor = self.get_day_factor()
        for p in self.weather_particles:
            p.draw(self.screen, camera_x, camera_y, day_factor)

    def draw_particles(self, camera_x, camera_y):
        if not self.particles_enabled:
            return
        for p in self.particles:
            p.draw(self.screen, camera_x, camera_y)

    def draw_ray_debug(self, camera_x, camera_y):
        if not self.ray_debug:
            return
        for line in self._ray_debug_lines:
            fx, fy, tx, ty = line
            sx1 = int(fx - camera_x)
            sy1 = int(fy - camera_y)
            sx2 = int(tx - camera_x)
            sy2 = int(ty - camera_y)
            pygame.draw.line(self.screen, (255, 100, 100, 80), (sx1, sy1), (sx2, sy2), 1)
        self._ray_debug_lines = []

    def draw_debug_info(self):
        y = 10
        profiler_data = self.profiler.get_all_avgs()
        profile_str = " | ".join(f"{s}: {t:.1f}ms" for s, t in profiler_data.items()) if profiler_data else "no data"
        overloaded = 0 < self.clock.get_fps() < 30
        info = [
            f"DEBUG MODE ON (B to toggle)",
            f"Player: ({self.player_x:.2f}, {self.player_y:.2f}) | Angle: {math.degrees(self.player_angle):.1f}",
            f"Quality: {self.quality} | Weather: {self.weather_type} | Day/Night: {self.day_night_enabled}",
            f"Stats: {len(self.static_lights)}S + {len(self.dynamic_objects)}D + {len(self.bots)}B",
            f"FPS: {self.clock.get_fps():.1f} | TPS: {self._current_tps}{'  **OVERLOADED**' if overloaded else ''}",
            f"Profiler: {profile_str}",
        ]
        for line in info:
            text = self.small_font.render(line, True, (255, 255, 0))
            self.screen.blit(text, (10, y))
            y += 18

        camera_x = self.player_x * self.cell_size - self.screen_width // 2
        camera_y = self.player_y * self.cell_size - self.screen_height // 2
        camera_x = max(0, min(camera_x, self.grid_size * self.cell_size - self.screen_width))
        camera_y = max(0, min(camera_y, self.grid_size * self.cell_size - self.screen_height))

        for light in self.static_lights:
            sx = light.x * self.cell_size - camera_x
            sy = light.y * self.cell_size - camera_y
            if -10 <= sx <= self.screen_width + 10 and -10 <= sy <= self.screen_height + 10:
                r, g, b = light.color if self.colored_lights_enabled else (255, 255, 255)
                pygame.draw.circle(self.screen, (r, g, b), (int(sx), int(sy)), 3)
                label = f"#{light.lid} R{light.radius_cells} I{light.intensity}"
                text = self.small_font.render(label, True, (r, g, b))
                self.screen.blit(text, (sx + 8, sy - 8))

        for obj in self.dynamic_objects:
            sx = obj.x * self.cell_size - camera_x
            sy = obj.y * self.cell_size - camera_y
            if -10 <= sx <= self.screen_width + 10 and -10 <= sy <= self.screen_height + 10:
                r, g, b = obj.color if self.colored_lights_enabled else (255, 255, 255)
                pygame.draw.circle(self.screen, (r, g, b), (int(sx), int(sy)), 3)
                label = f"#{obj.lid} R{obj.light_radius} I{obj.light_intensity}"
                text = self.small_font.render(label, True, (r, g, b))
                self.screen.blit(text, (sx + 8, sy - 8))

        for bot in self.bots:
            sx = bot.x * self.cell_size - camera_x
            sy = bot.y * self.cell_size - camera_y
            if -10 <= sx <= self.screen_width + 10 and -10 <= sy <= self.screen_height + 10:
                r, g, b = bot.color if self.colored_lights_enabled else (255, 255, 255)
                pygame.draw.circle(self.screen, (r, g, b), (int(sx), int(sy)), 3)
                l_on = "ON" if bot.light_on else "OFF"
                w = f" W{bot._wait_remaining:.1f}" if bot._wait_remaining > 0 else ""
                r_str = f" @{1/bot._tick_interval:.0f}Hz" if bot._tick_interval > 0 else ""
                alert_str = f" AL:{bot._alert_level:.2f}" if bot._alert_level > 0 else ""
                label = f"#{bot.lid} S:{bot.state} R{bot.light_radius} L{l_on}{w}{r_str}{alert_str}"
                text = self.small_font.render(label, True, (r, g, b))
                self.screen.blit(text, (sx + 8, sy - 8))

        for light in self.static_lights:
            text = self.small_font.render(
                f"  S#{light.lid} ({light.x},{light.y}) r={light.radius_cells} i={light.intensity} c={light.color}",
                True, (180, 255, 180),
            )
            self.screen.blit(text, (10, y))
            y += 14

        for obj in self.dynamic_objects:
            text = self.small_font.render(
                f"  D#{obj.lid} ({obj.x},{obj.y}) r={obj.light_radius} i={obj.light_intensity} c={obj.color}",
                True, (255, 180, 180),
            )
            self.screen.blit(text, (10, y))
            y += 14

        for bot in self.bots:
            l_on = "ON" if bot.light_on else "OFF"
            w = f" wait={bot._wait_remaining:.1f}" if bot._wait_remaining > 0 else ""
            r_str = f" rate={1/bot._tick_interval:.1f}Hz" if bot._tick_interval > 0 else ""
            extra = ""
            if bot._follow_target:
                extra = f" follow={bot._follow_target}"
            if bot._guard_target:
                extra = f" guard={bot._guard_target} R{bot._guard_radius}"
            p_str = f" path[{len(bot._path)}]" if bot._path else ""
            patrol_str = f" patrol[{len(bot._patrol_points)}]" if bot._patrol_points else ""
            text = self.small_font.render(
                f"  B#{bot.lid} ({bot.x},{bot.y}) S:{bot.state} r={bot.light_radius} L{l_on} spd={bot.speed}{w}{r_str}{extra}{p_str}{patrol_str}",
                True, (180, 180, 255),
            )
            self.screen.blit(text, (10, y))
            y += 14

    def draw_semi_debug_info(self):
        y = 10
        overloaded = 0 < self.clock.get_fps() < 30
        info = [
            f"SEMI-DEBUG (N to toggle)",
            f"Quality: {self.quality} | FPS: {self.clock.get_fps():.1f} | TPS: {self._current_tps}{'  **OVERLOADED**' if overloaded else ''}",
            f"Weather: {self.weather_type} | Day cycle: {self.get_day_factor():.2f}x",
        ]
        for line in info:
            text = self.small_font.render(line, True, (200, 200, 100))
            self.screen.blit(text, (10, y))
            y += 18

        camera_x = self.player_x * self.cell_size - self.screen_width // 2
        camera_y = self.player_y * self.cell_size - self.screen_height // 2
        camera_x = max(0, min(camera_x, self.grid_size * self.cell_size - self.screen_width))
        camera_y = max(0, min(camera_y, self.grid_size * self.cell_size - self.screen_height))

        for light in self.static_lights:
            sx = light.x * self.cell_size - camera_x
            sy = light.y * self.cell_size - camera_y
            if -10 <= sx <= self.screen_width + 10 and -10 <= sy <= self.screen_height + 10:
                r, g, b = light.color if self.colored_lights_enabled else (255, 255, 255)
                label = f"#{light.lid} R{light.radius_cells} I{light.intensity}"
                text = self.small_font.render(label, True, (r, g, b))
                self.screen.blit(text, (sx + 6, sy - 6))

        for obj in self.dynamic_objects:
            sx = obj.x * self.cell_size - camera_x
            sy = obj.y * self.cell_size - camera_y
            if -10 <= sx <= self.screen_width + 10 and -10 <= sy <= self.screen_height + 10:
                r, g, b = obj.color if self.colored_lights_enabled else (255, 255, 255)
                label = f"#{obj.lid} R{obj.light_radius} I{obj.light_intensity}"
                text = self.small_font.render(label, True, (r, g, b))
                self.screen.blit(text, (sx + 6, sy - 6))

        for bot in self.bots:
            sx = bot.x * self.cell_size - camera_x
            sy = bot.y * self.cell_size - camera_y
            if -10 <= sx <= self.screen_width + 10 and -10 <= sy <= self.screen_height + 10:
                r, g, b = bot.color if self.colored_lights_enabled else (255, 255, 255)
                l_on = "ON" if bot.light_on else "OFF"
                label = f"B#{bot.lid} S:{bot.state} R{bot.light_radius} L{l_on}"
                text = self.small_font.render(label, True, (r, g, b))
                self.screen.blit(text, (sx + 6, sy - 6))

    def draw_normal_info(self):
        overloaded = 0 < self.clock.get_fps() < 30
        day_factor = self.get_day_factor()
        weather_str = f" | {self.weather_type.upper()}" if self.weather_enabled and self.weather_type != "none" else ""
        day_str = f" | Day {day_factor:.2f}x" if self.day_night_enabled else ""
        fog_str = " | FOG ON" if self.fog_of_war else " | FOG OFF"
        label = f"{self.clock.get_fps():.1f} FPS | {self._current_tps} TPS | {self.quality}{weather_str}{day_str}{fog_str}"
        if overloaded:
            label += "  **OVERLOADED**"
        light_icon = "LIGHT ON" if self.player_light_on else "LIGHT OFF"
        label += f"  | {light_icon}"
        fps_text = self.small_font.render(label, True, (255, 255, 255))
        self.screen.blit(fps_text, (10, 10))
        help_text = self.small_font.render(
            "WASD move | Mouse look | B-debug | N-semi | L-light | R-raydebug | H-hotreload",
            True, (180, 180, 180),
        )
        self.screen.blit(help_text, (10, self.screen_height - 25))

    def run_test(self, duration_ms, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        running = True
        self._flicker_time = 0.0
        start_time = time_mod.perf_counter()
        end_time = start_time + duration_ms / 1000.0
        frames = 0
        fps_log = []
        self._tps_timer = 0.0
        self._tick_count = 0
        self._current_tps = 0

        while running and time_mod.perf_counter() < end_time:
            dt = self.clock.tick(60) / 1000.0
            self._flicker_time += dt
            self._obj_lit_cache.clear()

            self._tick_count += 1
            self._tps_timer += dt
            if self._tps_timer >= 1.0:
                self._current_tps = self._tick_count
                self._tick_count = 0
                self._tps_timer -= 1.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            for obj in self.dynamic_objects:
                obj.update(dt)
            for bot in self.bots:
                bot.update(dt)
            for light in self.static_lights:
                light.update(dt)

            cam_x = self.player_x * self.cell_size - self.screen_width // 2
            cam_y = self.player_y * self.cell_size - self.screen_height // 2
            cam_x = max(0, min(cam_x, self.grid_size * self.cell_size - self.screen_width))
            cam_y = max(0, min(cam_y, self.grid_size * self.cell_size - self.screen_height))

            self.screen.fill((0, 0, 0))
            self.draw_scene(self.screen, cam_x, cam_y)

            for obj in self.dynamic_objects:
                obj.draw(self.screen, self.cell_size, cam_x, cam_y)
            for bot in self.bots:
                bot.draw(self.screen, self.cell_size, cam_x, cam_y)

            self.draw_player(self.screen, cam_x, cam_y)

            if not self.debug:
                self.apply_lighting(self.screen, cam_x, cam_y)
                self._draw_wall_borders(self.screen, cam_x, cam_y)
                self.update_particles(dt, cam_x, cam_y)
                self.draw_particles(cam_x, cam_y)
                self.update_weather(dt, cam_x, cam_y)
                self.draw_weather(cam_x, cam_y)

            if self.debug:
                self.draw_debug_info()
            elif self.semi_debug:
                self.draw_semi_debug_info()
            else:
                self.draw_normal_info()

            self.draw_ray_debug(cam_x, cam_y)

            frames += 1
            if frames % 5 == 0:
                fps_log.append(frames / (time_mod.perf_counter() - start_time))

            pygame.display.flip()

        actual_duration = time_mod.perf_counter() - start_time
        avg_fps = round(sum(fps_log) / len(fps_log), 1) if fps_log else round(frames / actual_duration, 1)
        report = {
            "quality": self.quality,
            "duration_ms": duration_ms,
            "actual_duration_s": round(actual_duration, 3),
            "total_frames": frames,
            "avg_fps": avg_fps,
            "min_fps": round(min(fps_log), 1) if fps_log else avg_fps,
            "max_fps": round(max(fps_log), 1) if fps_log else avg_fps,
        }
        report_path = os.path.join(output_dir, "test_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  [{self.quality}] {frames} frames, avg {avg_fps} FPS ({report['min_fps']}-{report['max_fps']})")
        return report

    def _render_remote_state(self, state):
        if state is None:
            return
        cam_x = 0
        cam_y = 0
        players = state.get("_players", [])
        if players:
            me = players[0]
            cam_x = me["x"] * self.cell_size - self.screen_width // 2
            cam_y = me["y"] * self.cell_size - self.screen_height // 2
            cam_x = max(0, min(cam_x, self.grid_size * self.cell_size - self.screen_width))
            cam_y = max(0, min(cam_y, self.grid_size * self.cell_size - self.screen_height))

        self.screen.fill((0, 0, 0))

        # Draw map grid from state
        grid = state.get("map", self.map_grid)
        cell = state.get("cell_size", self.cell_size)
        gs = state.get("grid_size", self.grid_size)
        floor_colors = {}
        for y in range(gs):
            for x in range(gs):
                if grid[y][x] == 1:
                    h = hash((x, y)) & 0xFF
                    floor_colors[(x, y)] = (65 + h // 8, 60 + h // 8, 55 + h // 10)
                else:
                    h = hash((x * 7, y * 13)) & 0x7F
                    floor_colors[(x, y)] = (90 + h // 4, 85 + h // 5, 80 + h // 6)

        start_x = max(0, cam_x // cell)
        end_x = min(gs, (cam_x + self.screen_width + cell - 1) // cell)
        start_y = max(0, cam_y // cell)
        end_y = min(gs, (cam_y + self.screen_height + cell - 1) // cell)
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                sx = x * cell - cam_x
                sy = y * cell - cam_y
                color = floor_colors.get((x, y), (80, 80, 80))
                if grid[y][x] == 1:
                    pygame.draw.rect(self.screen, (65, 60, 55), (sx, sy, cell, cell))
                else:
                    pygame.draw.rect(self.screen, color, (sx, sy, cell, cell))

        # Draw static lights
        for l in state.get("static_lights", []):
            lx = int(l["x"] * cell - cam_x)
            ly = int(l["y"] * cell - cam_y)
            r = int(l["radius_cells"] * cell * 1.5)
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            c = tuple(l.get("color", (255, 200, 100)))
            for ri in range(r, 0, -max(1, r // 16)):
                a = int(60 * (1 - ri / r))
                pygame.draw.circle(surf, c + (a,), (r, r), ri)
            self.screen.blit(surf, (lx - r, ly - r))

        # Draw dynamic objects
        for o in state.get("dynamic_objects", []):
            ox = int(o["x"] * cell - cam_x)
            oy = int(o["y"] * cell - cam_y)
            c = tuple(o.get("color", (200, 100, 50)))
            s = int(cell * o.get("size", 0.8) // 2)
            pygame.draw.circle(self.screen, c, (ox, oy), s)
            pygame.draw.circle(self.screen, (255, 255, 255), (ox, oy), s, 1)

        # Draw bots
        for b in state.get("bots", []):
            bx = int(b["x"] * cell - cam_x)
            by = int(b["y"] * cell - cam_y)
            c = tuple(b.get("color", (0, 100, 255)))
            r = int(cell * 0.38)
            pygame.draw.circle(self.screen, c, (bx, by), r)
            ang = b.get("angle", 0.0)
            ex = bx + math.cos(ang + 0.4) * cell * 0.55
            ey = by + math.sin(ang + 0.4) * cell * 0.55
            ex2 = bx + math.cos(ang - 0.4) * cell * 0.55
            ey2 = by + math.sin(ang - 0.4) * cell * 0.55
            pygame.draw.line(self.screen, (255, 255, 255), (bx, by), (int(ex), int(ey)), 2)
            pygame.draw.line(self.screen, (255, 255, 255), (bx, by), (int(ex2), int(ey2)), 2)

        # Draw all players
        for p in players:
            px = int(p["x"] * cell - cam_x)
            py = int(p["y"] * cell - cam_y)
            c = tuple(p.get("color", (0, 240, 0)))
            pr = cell // 3
            pygame.draw.circle(self.screen, (20, 20, 20), (px, py), pr + 3)
            pygame.draw.circle(self.screen, c, (px, py), pr)
            ang = p.get("angle", 0.0)
            ex = px + math.cos(ang) * cell
            ey = py + math.sin(ang) * cell
            pygame.draw.line(self.screen, (255, 60, 60), (px, py), (int(ex), int(ey)), 2)
            # Player label
            pid = p.get("id", 0)
            label = self.small_font.render(f"P{pid}", True, (255, 255, 255))
            self.screen.blit(label, (px - label.get_width() // 2, py - pr - 18))

        # Network info
        conn_text = self.small_font.render("[CLIENT] Connected to server", True, (100, 200, 100))
        self.screen.blit(conn_text, (10, 10))

    def run(self):
        running = True
        self._flicker_time = 0.0
        while running:
            dt = self.clock.tick(60) / 1000.0
            self._flicker_time += dt
            self._obj_lit_cache.clear()

            self.profiler.start("frame")

            self._tick_count += 1
            self._tps_timer += dt
            if self._tps_timer >= 1.0:
                self._current_tps = self._tick_count
                self._tick_count = 0
                self._tps_timer -= 1.0

            self.day_cycle_time += dt * self.day_cycle_speed
            self._hot_reload_timer += dt
            if self._hot_reload_timer >= 2.0:
                self._hot_reload_timer = 0.0
                self.hot_reload_config()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_b:
                        self.debug = not self.debug
                        if self.debug:
                            self.semi_debug = False
                    elif event.key == pygame.K_n:
                        self.semi_debug = not self.semi_debug
                        if self.semi_debug:
                            self.debug = False
                    elif event.key == pygame.K_l:
                        self.player_light_on = not self.player_light_on
                        self.logger.event("PLAYER", f"Light {'ON' if self.player_light_on else 'OFF'}")
                    elif event.key == pygame.K_r:
                        self.ray_debug = not self.ray_debug
                        self.logger.event("DEBUG", f"Ray debug {'ON' if self.ray_debug else 'OFF'}")
                    elif event.key == pygame.K_f:
                        self.fog_of_war = not self.fog_of_war
                        if not self.fog_of_war:
                            for yy in range(self.grid_size):
                                for xx in range(self.grid_size):
                                    self.fog_explored[yy][xx] = True
                            self.fog_visible.clear()
                        self.logger.event("FOG", f"Fog of war {'ON' if self.fog_of_war else 'OFF'}")
                    elif event.key == pygame.K_h:
                        self.hot_reload_config()
                    elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                        self.day_cycle_speed = min(0.5, self.day_cycle_speed * 2)
                    elif event.key == pygame.K_MINUS:
                        self.day_cycle_speed = max(0.001, self.day_cycle_speed / 2)

            self.profiler.start("input")
            self.handle_input(dt)
            self.profiler.end("input")

            self.update_fog()

            pc = (int(self.player_x), int(self.player_y))
            if pc != self._last_los_player_cell:
                self._los_cache.clear()
                self._last_los_player_cell = pc

            self.profiler.start("update")
            for obj in self.dynamic_objects:
                obj.update(dt)
            for bot in self.bots:
                bot.update(dt)
            for light in self.static_lights:
                light.update(dt)
            self.profiler.end("update")

            self.screen.fill((0, 0, 0))

            if self.network_mode == "client" and self._client:
                state = self._client.get_state()
                self._render_remote_state(state)
                # Send input to server
                keys = {k: True for k in self._pressed_keys if hasattr(pygame, f"K_{k}")}
                self._client.send_input(self._pressed_keys, angle=self.player_angle, light_on=self.player_light_on)
                self.profiler.end("frame")
                pygame.display.flip()
                continue

            cam_x = self.player_x * self.cell_size - self.screen_width // 2
            cam_y = self.player_y * self.cell_size - self.screen_height // 2
            cam_x = max(0, min(cam_x, self.grid_size * self.cell_size - self.screen_width))
            cam_y = max(0, min(cam_y, self.grid_size * self.cell_size - self.screen_height))

            self.profiler.start("scene")
            self.draw_scene(self.screen, cam_x, cam_y)
            self.profiler.end("scene")

            self.profiler.start("objects")
            for obj in self.dynamic_objects:
                obj.draw(self.screen, self.cell_size, cam_x, cam_y)
            for bot in self.bots:
                bot.draw(self.screen, self.cell_size, cam_x, cam_y)
            self.draw_player(self.screen, cam_x, cam_y)
            self.profiler.end("objects")

            if not self.debug:
                self.profiler.start("lighting")
                self.apply_lighting(self.screen, cam_x, cam_y)
                self._draw_wall_borders(self.screen, cam_x, cam_y)
                self.profiler.end("lighting")

                self.profiler.start("particles")
                self.update_particles(dt, cam_x, cam_y)
                self.draw_particles(cam_x, cam_y)
                self.update_weather(dt, cam_x, cam_y)
                self.draw_weather(cam_x, cam_y)
                self.draw_fog_overlay(self.screen, cam_x, cam_y)
                self.profiler.end("particles")

            if self.network_mode == "server" and self._server:
                # Overlay server info
                nc = self._server.get_client_count()
                srv_text = self.small_font.render(f"[SERVER] {nc} client(s)", True, (200, 200, 80))
                self.screen.blit(srv_text, (10, 10))

                # Draw remote players
                for pid, pdata in self.network_players.items():
                    px = int(pdata["x"] * self.cell_size - cam_x)
                    py = int(pdata["y"] * self.cell_size - cam_y)
                    if px < -50 or px > self.screen_width + 50 or py < -50 or py > self.screen_height + 50:
                        continue
                    c = pdata.get("color", [0, 240, 0])
                    pr = self.cell_size // 3
                    pygame.draw.circle(self.screen, (20, 20, 20), (px, py), pr + 3)
                    pygame.draw.circle(self.screen, tuple(c), (px, py), pr)
                    ang = pdata.get("angle", 0.0)
                    ex = px + math.cos(ang) * self.cell_size
                    ey = py + math.sin(ang) * self.cell_size
                    pygame.draw.line(self.screen, (255, 60, 60), (px, py), (int(ex), int(ey)), 2)
                    label = self.small_font.render(f"P{pid}", True, (255, 255, 255))
                    self.screen.blit(label, (px - label.get_width() // 2, py - pr - 18))

            if self.debug:
                self.draw_debug_info()
            elif self.semi_debug:
                self.draw_semi_debug_info()
            else:
                self.draw_normal_info()

            self.draw_ray_debug(cam_x, cam_y)

            if self.network_mode == "server" and self._server:
                self._server.broadcast_state()

            self.profiler.end("frame")

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LightEngine v4.0.0")
    parser.add_argument("--test", choices=["low", "normal", "max", "full"], help="Run in test mode")
    parser.add_argument("--time", type=int, default=6000, help="Test duration per mode in ms (default: 6000)")
    parser.add_argument("--server", action="store_true", help="Run as multiplayer server")
    parser.add_argument("--client", type=str, metavar="HOST", help="Connect to server at HOST:PORT")
    parser.add_argument("--port", type=int, default=54321, help="Network port (default: 54321)")
    args = parser.parse_args()

    if args.test:
        output_root = "test_last_call"
        if os.path.exists(output_root):
            try:
                shutil.rmtree(output_root)
            except PermissionError:
                pass

        qualities = ["low", "normal", "max"] if args.test == "full" else [args.test]
        all_reports = []

        for quality in qualities:
            print(f"=== Testing: {quality} ({args.time}ms) ===")
            game = LightEngine(quality=quality)
            report = game.run_test(args.time, os.path.join(output_root, quality))
            all_reports.append(report)

        summary_path = os.path.join(output_root, "summary.json")
        with open(summary_path, "w") as f:
            json.dump({"mode": args.test, "duration_ms": args.time, "reports": all_reports}, f, indent=2)
        pygame.quit()
        print(f"\nDone. Results in '{output_root}/'")
    else:
        quality = "normal"
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                cfg = json.load(f)
            quality = cfg.get("quality", "normal")

        network_mode = None
        server_host = None
        if args.server:
            network_mode = "server"
        elif args.client:
            network_mode = "client"
            server_host = args.client

        game = LightEngine(quality=quality, network_mode=network_mode, server_host=server_host)
        game.run()
