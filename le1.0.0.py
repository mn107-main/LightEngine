import pygame
import math
import json
import os
from collections import OrderedDict

pygame.init()

class DynamicObject:
    __slots__ = ('x', 'y', 'light_radius', 'light_intensity', 'color', 'size', '_last_pos', '_cached_light_surface', '_last_camera')
    def __init__(self, x, y, light_radius=0, light_intensity=1.0, color=(200,100,50), size=0.8):
        self.x = x
        self.y = y
        self.light_radius = light_radius
        self.light_intensity = light_intensity
        self.color = color
        self.size = size
        self._last_pos = (x, y)
        self._cached_light_surface = None
        self._last_camera = (-1, -1)

    def update(self, dt):
        pass

    def moved(self):
        if (self.x, self.y) != self._last_pos:
            self._last_pos = (self.x, self.y)
            return True
        return False

    def draw(self, screen, cell_size, camera_x, camera_y):
        screen_x = self.x * cell_size - camera_x
        screen_y = self.y * cell_size - camera_y
        radius_px = int(cell_size * self.size // 2)
        pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), radius_px)

class StaticLight:
    __slots__ = ('x', 'y', 'radius_cells', 'intensity', 'color', '_cached_light_surface', '_last_camera')
    def __init__(self, x, y, radius_cells, intensity=1.0, color=(255,255,200)):
        self.x = x
        self.y = y
        self.radius_cells = radius_cells
        self.intensity = intensity
        self.color = color
        self._cached_light_surface = None
        self._last_camera = (-1, -1)

class Game:
    def __init__(self):
        self.load_config()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("LightEngine v1.0.0")
        self.clock = pygame.time.Clock()
        self.debug = False
        self.semi_debug = False
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        self.ambient_light = 20

        self.player_x = self.spawn_x + 0.5
        self.player_y = self.spawn_y + 0.5
        self.player_angle = 0.0
        self.player_light_radius = self.fov_radius
        self.player_light_intensity = 1.0

        self.ray_step = math.radians(1.2)
        self.ray_cast_step = 6

        self.load_map()
        self.load_static_lights()
        self.load_dynamic_objects()

        self.light_gradient_cache = OrderedDict()
        self.max_gradient_cache = 8

        self._empty_surface = pygame.Surface((1, 1), pygame.SRCALPHA)
        self._empty_surface.fill((0,0,0,0))

        self._sin_cache = {}
        self._cos_cache = {}

        self._last_camera = (-1, -1)
        self._cached_start_x = 0
        self._cached_end_x = 0
        self._cached_start_y = 0
        self._cached_end_y = 0

    def load_config(self):
        config_file = "config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
            self.map_file = data.get("map_file", "map.json")
            self.spawn_x = data.get("spawn_x", 10)
            self.spawn_y = data.get("spawn_y", 10)
            self.player_speed = data.get("player_speed", 5.0)
            self.fov_radius = data.get("fov_radius", 8)
            self.fov_angle_deg = data.get("fov_angle_deg", 90)
            self.screen_width = data.get("screen_width", 600)
            self.screen_height = data.get("screen_height", 600)
            self.cell_size = self.screen_width // 20
            self.screen_width = 20 * self.cell_size
            self.screen_height = 20 * self.cell_size
            self.max_dynamic_lights = data.get("max_dynamic_lights", 3)
        else:
            self.map_file = "map.json"
            self.spawn_x = 10
            self.spawn_y = 10
            self.player_speed = 5.0
            self.fov_radius = 8
            self.fov_angle_deg = 90
            self.screen_width = 600
            self.screen_height = 600
            self.cell_size = 30
            self.max_dynamic_lights = 3

        self.fov_angle = math.radians(self.fov_angle_deg)

    def load_static_lights(self):
        self.static_lights = [
            StaticLight(5, 5, 4, 0.8, (255, 200, 150)),
            StaticLight(15, 12, 3, 0.6, (150, 200, 255)),
            StaticLight(8, 16, 5, 0.9, (255, 255, 180)),
        ]

    def load_dynamic_objects(self):
        obj1 = DynamicObject(12, 10, light_radius=2, light_intensity=0.5, color=(200, 80, 80))
        obj2 = DynamicObject(7, 14, light_radius=1.5, light_intensity=0.4, color=(80, 200, 80))
        self.dynamic_objects = [obj1, obj2]

    def load_map(self):
        if os.path.exists(self.map_file):
            with open(self.map_file, 'r') as f:
                data = json.load(f)
            self.map_grid = data["map"]
            self.grid_size = len(self.map_grid)
            if "player_spawn" in data:
                self.spawn_x, self.spawn_y = data["player_spawn"]
                self.player_x = self.spawn_x + 0.5
                self.player_y = self.spawn_y + 0.5
        else:
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

    def _fast_sin_cos(self, angle):
        key = round(angle, 3)
        if key not in self._sin_cache:
            self._sin_cache[key] = math.sin(angle)
            self._cos_cache[key] = math.cos(angle)
            if len(self._sin_cache) > 360:
                first_key = next(iter(self._sin_cache))
                del self._sin_cache[first_key]
                del self._cos_cache[first_key]
        return self._cos_cache[key], self._sin_cache[key]

    def cast_ray(self, px, py, angle, max_dist_px, ignore_walls=False):
        step = self.ray_cast_step
        dist = 0
        cos_a, sin_a = self._fast_sin_cos(angle)
        while dist < max_dist_px:
            x = px + cos_a * dist
            y = py + sin_a * dist
            cx = int(x // self.cell_size)
            cy = int(y // self.cell_size)
            if cx < 0 or cx >= self.grid_size or cy < 0 or cy >= self.grid_size:
                return (x, y)
            if not ignore_walls and self.map_grid[cy][cx] == 1:
                prev_x = px + cos_a * (dist - step)
                prev_y = py + sin_a * (dist - step)
                return (prev_x, prev_y)
            dist += step
        x = px + cos_a * max_dist_px
        y = py + sin_a * max_dist_px
        return (x, y)

    def can_move_to(self, x, y):
        cell_x = int(x)
        cell_y = int(y)
        if cell_x < 0 or cell_x >= self.grid_size or cell_y < 0 or cell_y >= self.grid_size:
            return False
        if self.map_grid[cell_y][cell_x] == 1:
            return False
        fx, fy = x - cell_x, y - cell_y
        if fx < 0.2 and cell_x-1 >= 0 and self.map_grid[cell_y][cell_x-1] == 1:
            return False
        if fx > 0.8 and cell_x+1 < self.grid_size and self.map_grid[cell_y][cell_x+1] == 1:
            return False
        if fy < 0.2 and cell_y-1 >= 0 and self.map_grid[cell_y-1][cell_x] == 1:
            return False
        if fy > 0.8 and cell_y+1 < self.grid_size and self.map_grid[cell_y+1][cell_x] == 1:
            return False
        return True

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        move_x, move_y = 0, 0
        if keys[pygame.K_w]:
            move_y -= 1
        if keys[pygame.K_s]:
            move_y += 1
        if keys[pygame.K_a]:
            move_x -= 1
        if keys[pygame.K_d]:
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

    def draw_map(self, screen, camera_x, camera_y):
        start_x, end_x, start_y, end_y = self.get_visible_cells_range(camera_x, camera_y)
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                screen_x = x * self.cell_size - camera_x
                screen_y = y * self.cell_size - camera_y
                if self.map_grid[y][x] == 1:
                    color = (80, 80, 80)
                else:
                    color = (100, 100, 100)
                pygame.draw.rect(screen, color, (screen_x, screen_y, self.cell_size, self.cell_size))
                pygame.draw.rect(screen, (50,50,50), (screen_x, screen_y, self.cell_size, self.cell_size), 1)

    def draw_player(self, screen, camera_x, camera_y):
        screen_x = self.player_x * self.cell_size - camera_x
        screen_y = self.player_y * self.cell_size - camera_y
        pygame.draw.circle(screen, (0,200,0), (int(screen_x), int(screen_y)), self.cell_size // 3)
        end_x = screen_x + math.cos(self.player_angle) * self.cell_size
        end_y = screen_y + math.sin(self.player_angle) * self.cell_size
        pygame.draw.line(screen, (255,0,0), (screen_x, screen_y), (end_x, end_y), 2)

    def _is_light_visible_on_screen(self, source_screen_x, source_screen_y, radius_px):
        return not (source_screen_x + radius_px < 0 or 
                   source_screen_x - radius_px > self.screen_width or
                   source_screen_y + radius_px < 0 or 
                   source_screen_y - radius_px > self.screen_height)

    def _get_radial_gradient(self, radius_px, ambient, intensity):
        key = (radius_px, int(ambient), int(intensity * 10))
        if key in self.light_gradient_cache:
            self.light_gradient_cache.move_to_end(key)
            return self.light_gradient_cache[key]

        size = radius_px * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (radius_px, radius_px)
        max_bright = min(255, int(255 * intensity))
        step = max(1, radius_px // 30)
        for r in range(radius_px, 0, -step):
            factor = r / radius_px
            brightness = int(ambient + (max_bright - ambient) * (1 - factor))
            brightness = min(255, max(0, brightness))
            color = (brightness, brightness, brightness, 255)
            pygame.draw.circle(surf, color, center, r)
        pygame.draw.circle(surf, (max_bright, max_bright, max_bright, 255), center, step)

        if len(self.light_gradient_cache) >= self.max_gradient_cache:
            self.light_gradient_cache.popitem(last=False)
        self.light_gradient_cache[key] = surf
        return surf

    def _get_light_polygon(self, source_x_world, source_y_world, radius_cells, intensity, camera_x, camera_y, angle=None, fov_angle=None):
        max_dist_px = radius_cells * self.cell_size
        radius_px = int(max_dist_px)
        
        px_world = source_x_world
        py_world = source_y_world
        source_screen = (px_world - camera_x, py_world - camera_y)

        if not self._is_light_visible_on_screen(source_screen[0], source_screen[1], radius_px):
            return self._empty_surface

        light_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        light_surf.fill((0,0,0,0))

        if angle is not None and fov_angle is not None:
            start_angle = angle - fov_angle/2
            num_rays = max(8, int(fov_angle / self.ray_step) + 1)
        else:
            start_angle = 0
            num_rays = max(12, int(2*math.pi / self.ray_step) + 1)

        points = [source_screen]
        for i in range(num_rays):
            cur_angle = start_angle + i * self.ray_step
            hit_x, hit_y = self.cast_ray(px_world, py_world, cur_angle, max_dist_px)
            screen_pos = (hit_x - camera_x, hit_y - camera_y)
            points.append(screen_pos)

        if len(points) >= 3:
            pygame.draw.polygon(light_surf, (255,255,255,255), points)

        grad = self._get_radial_gradient(radius_px, self.ambient_light, intensity)
        grad_x = source_screen[0] - radius_px
        grad_y = source_screen[1] - radius_px
        light_surf.blit(grad, (grad_x, grad_y), special_flags=pygame.BLEND_RGBA_MULT)

        return light_surf

    def _get_cached_light(self, light_obj, world_x, world_y, radius_cells, intensity, camera_x, camera_y, angle=None, fov_angle=None):
        if hasattr(light_obj, '_last_camera') and light_obj._last_camera == (camera_x, camera_y):
            if light_obj._cached_light_surface is not None:
                return light_obj._cached_light_surface
        
        light_surf = self._get_light_polygon(world_x, world_y, radius_cells, intensity, camera_x, camera_y, angle, fov_angle)
        
        if hasattr(light_obj, '_last_camera'):
            light_obj._cached_light_surface = light_surf
            light_obj._last_camera = (camera_x, camera_y)
        
        return light_surf

    def apply_lighting(self, screen, camera_x, camera_y):
        temp_surface = screen.copy()
        temp_surface.fill((self.ambient_light, self.ambient_light, self.ambient_light))
        screen.blit(temp_surface, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        for light in self.static_lights:
            light_surf = self._get_cached_light(
                light,
                light.x * self.cell_size + self.cell_size/2,
                light.y * self.cell_size + self.cell_size/2,
                light.radius_cells, light.intensity,
                camera_x, camera_y,
                angle=None, fov_angle=None
            )
            if light_surf is not self._empty_surface:
                screen.blit(light_surf, (0,0), special_flags=pygame.BLEND_RGBA_ADD)

        player_light = self._get_light_polygon(
            self.player_x * self.cell_size,
            self.player_y * self.cell_size,
            self.player_light_radius, self.player_light_intensity,
            camera_x, camera_y,
            angle=self.player_angle, fov_angle=self.fov_angle
        )
        if player_light is not self._empty_surface:
            screen.blit(player_light, (0,0), special_flags=pygame.BLEND_RGBA_ADD)

        if self.dynamic_objects:
            player_px = self.player_x * self.cell_size
            player_py = self.player_y * self.cell_size
            objects_with_dist = []
            for obj in self.dynamic_objects:
                if obj.light_radius > 0:
                    dist_sq = (obj.x * self.cell_size - player_px)**2 + (obj.y * self.cell_size - player_py)**2
                    objects_with_dist.append((dist_sq, obj))
            objects_with_dist.sort(key=lambda x: x[0])
            for _, obj in objects_with_dist[:self.max_dynamic_lights]:
                if obj.moved():
                    obj._cached_light_surface = None
                light_surf = self._get_cached_light(
                    obj,
                    obj.x * self.cell_size,
                    obj.y * self.cell_size,
                    obj.light_radius, obj.light_intensity,
                    camera_x, camera_y,
                    angle=None, fov_angle=None
                )
                if light_surf is not self._empty_surface:
                    screen.blit(light_surf, (0,0), special_flags=pygame.BLEND_RGBA_ADD)

    def draw_debug_info(self):
        y = 10
        info = [
            f"DEBUG MODE ON (B to toggle)",
            f"Player: ({self.player_x:.2f}, {self.player_y:.2f}) | Angle: {math.degrees(self.player_angle):.1f}°",
            f"Ray: {math.degrees(self.ray_step):.1f}° | Cast step: {self.ray_cast_step}px",
            f"Lights: {len(self.static_lights)} static + {len(self.dynamic_objects)} dynamic (max {self.max_dynamic_lights} active)",
            f"Gradient cache: {len(self.light_gradient_cache)}/{self.max_gradient_cache} | Sin/cos cache: {len(self._sin_cache)}",
            f"FPS: {self.clock.get_fps():.1f}"
        ]
        for line in info:
            text = self.small_font.render(line, True, (255,255,0))
            self.screen.blit(text, (10, y))
            y += 18

    def draw_semi_debug_info(self):
        y = 10
        info = [
            f"SEMI-DEBUG (N to toggle)",
            f"FPS: {self.clock.get_fps():.1f}"
        ]
        for line in info:
            text = self.small_font.render(line, True, (200,200,100))
            self.screen.blit(text, (10, y))
            y += 18

    def draw_normal_info(self):
        fps_text = self.small_font.render(f"FPS: {self.clock.get_fps():.1f}", True, (255,255,255))
        self.screen.blit(fps_text, (10, 10))
        help_text = self.small_font.render("WASD move | Mouse look | B - debug | N - semi-debug", True, (200,200,200))
        self.screen.blit(help_text, (10, self.screen_height - 25))

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0

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

            self.handle_input(dt)

            for obj in self.dynamic_objects:
                obj.update(dt)

            cam_x = self.player_x * self.cell_size - self.screen_width // 2
            cam_y = self.player_y * self.cell_size - self.screen_height // 2
            cam_x = max(0, min(cam_x, self.grid_size * self.cell_size - self.screen_width))
            cam_y = max(0, min(cam_y, self.grid_size * self.cell_size - self.screen_height))

            self.screen.fill((0,0,0))
            self.draw_map(self.screen, cam_x, cam_y)

            for obj in self.dynamic_objects:
                obj.draw(self.screen, self.cell_size, cam_x, cam_y)

            self.draw_player(self.screen, cam_x, cam_y)

            if not self.debug:
                self.apply_lighting(self.screen, cam_x, cam_y)

            if self.debug:
                self.draw_debug_info()
            elif self.semi_debug:
                self.draw_semi_debug_info()
            else:
                self.draw_normal_info()

            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()