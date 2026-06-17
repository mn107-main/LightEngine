import pygame
import json
import os
import sys
import subprocess

pygame.init()

SCREEN_WIDTH = 520
SCREEN_HEIGHT = 640
FPS = 30

BLACK = (10, 10, 10)
WHITE = (220, 220, 220)
GRAY = (60, 60, 60)
LIGHT_GRAY = (140, 140, 140)
ACCENT = (80, 180, 100)
ACCENT_HOVER = (100, 220, 120)
ORANGE = (220, 160, 60)
BLUE = (80, 140, 220)
BLUE_HOVER = (100, 170, 250)

VERSIONS = [
    {"id": "le1", "label": "LE 1.0", "file": "le1.0.0.py", "desc": "Original raycasting"},
    {"id": "le2", "label": "LE 2.0", "file": "le2.0.0.py", "desc": "Realistic lighting + effects"},
    {"id": "le3", "label": "LE 3.0", "file": "le3.0.0.py", "desc": "Bot NPCs + wall LOS + wait"},
    {"id": "le4", "label": "LE 4.0", "file": "le4.0.0.py", "desc": "Weather, day/night, AI states, logging, profiler"},
]

QUALITY_PRESETS = {
    "low": {
        "label": "Low",
        "desc": [
            "Coarse rays, fast rendering",
            "No colored lights or particles",
            "Reduced draw distance",
            "Best performance",
        ],
    },
    "normal": {
        "label": "Normal",
        "desc": [
            "Balanced quality & speed",
            "Colored lights + particles",
            "Weather + day/night cycle",
            "Light flickering effect",
            "Default experience",
        ],
    },
    "max": {
        "label": "Max",
        "desc": [
            "High quality raycasting",
            "Smooth gradients + colored lights",
            "Dust particles in light beams",
            "Weather + day/night cycle",
            "Heavy but beautiful",
        ],
    },
}

RESOLUTIONS = [(600, 600), (800, 600), (1000, 800)]


class Button:
    def __init__(self, rect, text, font, color, hover_color, text_color=WHITE, sel_color=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.sel_color = sel_color or hover_color
        self.hovered = False
        self.selected = False

    def draw(self, screen):
        color = self.sel_color if self.selected else (self.hover_color if self.hovered else self.color)
        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        if self.selected:
            pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=6)
        elif self.hovered:
            pygame.draw.rect(screen, (255, 255, 255, 60), self.rect, 1, border_radius=6)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def clicked(self, mouse_pos, mouse_down):
        return self.hovered and mouse_down


class Launcher:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("LightEngine Launcher")
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.Font(None, 40)
        self.font_heading = pygame.font.Font(None, 28)
        self.font_body = pygame.font.Font(None, 22)
        self.font_small = pygame.font.Font(None, 18)

        self.selected_version = 1
        self.selected_quality = "normal"
        self.selected_res = 0

        self.maps = self.scan_maps()
        self.selected_map = 0

        y_off = 90
        self._sections = {
            "version_y": y_off + 24,
            "quality_y": (y_off := y_off + 24 + 28 + 8 + 10 + 24 + 24),
            "res_y": (y_off := y_off + 38 + 3 * 18 + 6 + 6 + 10 + 24 + 24),
            "map_y": (y_off := y_off + 42 + 8 + 10 + 24 + 24),
        }

        self.play_button = Button(
            (SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT - 80, 160, 48),
            "PLAY", self.font_heading, ACCENT, ACCENT_HOVER,
        )

        self.version_buttons = []
        for i, v in enumerate(VERSIONS):
            n = len(VERSIONS)
            bw = min(130, (SCREEN_WIDTH - 80) // n)
            x = 30 + i * (bw + 15)
            self.version_buttons.append(Button(
                (x, self._sections["version_y"], bw, 36),
                v["label"], self.font_body, GRAY, BLUE_HOVER,
                text_color=(180, 200, 255), sel_color=BLUE,
            ))

        self.quality_buttons = []
        for i, q in enumerate(["low", "normal", "max"]):
            x = 30 + i * 160
            qc = [(180, 180, 80), (80, 200, 100), (200, 80, 80)]
            self.quality_buttons.append(Button(
                (x, self._sections["quality_y"], 140, 36),
                QUALITY_PRESETS[q]["label"].upper(),
                self.font_body, GRAY, LIGHT_GRAY,
                sel_color=qc[i],
            ))

        self.res_buttons = []
        for i, res in enumerate(RESOLUTIONS):
            x = 30 + i * 160
            self.res_buttons.append(Button(
                (x, self._sections["res_y"], 140, 34),
                f"{res[0]}x{res[1]}",
                self.font_small, GRAY, LIGHT_GRAY,
                sel_color=(100, 150, 220),
            ))

        self.map_buttons = []
        n_maps = len(self.maps)
        for i, m in enumerate(self.maps):
            btn_w = max(80, min(140, (SCREEN_WIDTH - 60) // n_maps - 10))
            x = 30 + i * (btn_w + 10)
            label = m["name"]
            # Truncate long names to fit button
            while self.font_small.size(label)[0] > btn_w - 8 and len(label) > 3:
                label = label[:-4] + "..."
            self.map_buttons.append(Button(
                (x, self._sections["map_y"], btn_w, 34),
                label, self.font_small, GRAY, LIGHT_GRAY,
                sel_color=(160, 120, 200),
            ))

        self.mouse_down = False

    def scan_maps(self):
        maps = []
        maps_dir = "maps"
        if os.path.isdir(maps_dir):
            for fname in sorted(os.listdir(maps_dir)):
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(maps_dir, fname)) as f:
                            data = json.load(f)
                        grid = data.get("map", [])
                        maps.append({
                            "name": data.get("name", fname.replace(".json", "")),
                            "file": os.path.join(maps_dir, fname),
                            "grid_size": len(grid),
                            "num_lights": len(data.get("static_lights", [])),
                            "num_dynamic": len(data.get("dynamic_objects", [])),
                            "num_bots": len(data.get("bots", [])),
                        })
                    except Exception:
                        pass
        if not maps:
            maps.append({"name": "Default", "file": "maps/default.json",
                         "grid_size": 20, "num_lights": 0, "num_dynamic": 0, "num_bots": 0})
        return maps

    def draw_background(self):
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(8 + t * 12)
            g = int(8 + t * 12)
            b = int(18 + t * 20)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)
            mouse_pos = pygame.mouse.get_pos()
            self.mouse_down = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.mouse_down = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.launch_game()
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)

            for i, btn in enumerate(self.version_buttons):
                btn.update(mouse_pos); btn.selected = (i == self.selected_version)
                if btn.clicked(mouse_pos, self.mouse_down):
                    self.selected_version = i

            for i, btn in enumerate(self.quality_buttons):
                q_id = ["low", "normal", "max"][i]
                btn.update(mouse_pos); btn.selected = (q_id == self.selected_quality)
                if btn.clicked(mouse_pos, self.mouse_down):
                    self.selected_quality = q_id

            for i, btn in enumerate(self.res_buttons):
                btn.update(mouse_pos); btn.selected = (i == self.selected_res)
                if btn.clicked(mouse_pos, self.mouse_down):
                    self.selected_res = i

            for i, btn in enumerate(self.map_buttons):
                btn.update(mouse_pos); btn.selected = (i == self.selected_map)
                if btn.clicked(mouse_pos, self.mouse_down):
                    self.selected_map = i

            self.play_button.update(mouse_pos)
            if self.play_button.clicked(mouse_pos, self.mouse_down):
                self.launch_game()

            self.draw_background()

            title = self.font_title.render("LightEngine", True, WHITE)
            self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 25))
            sub = self.font_small.render("Lighting Engine for Python / Pygame", True, LIGHT_GRAY)
            self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 62))

            y = 90
            head_v = self.font_body.render("VERSION", True, (180, 200, 255))
            self.screen.blit(head_v, (30, y))
            for btn in self.version_buttons:
                btn.draw(self.screen)
            ver_desc = self.font_small.render(VERSIONS[self.selected_version]["desc"], True, ORANGE)
            self.screen.blit(ver_desc, (30, self._sections["version_y"] + 40))

            y = self._sections["version_y"] + 56
            pygame.draw.line(self.screen, (50, 50, 60), (30, y), (SCREEN_WIDTH - 30, y))
            y += 8
            head_q = self.font_body.render("QUALITY", True, (180, 200, 100))
            self.screen.blit(head_q, (30, y))
            for btn in self.quality_buttons:
                btn.draw(self.screen)
            y = self._sections["quality_y"] + 40
            for line in QUALITY_PRESETS[self.selected_quality]["desc"]:
                self.screen.blit(self.font_small.render(line, True, ORANGE), (30, y))
                y += 18
            y += 4
            pygame.draw.line(self.screen, (50, 50, 60), (30, y), (SCREEN_WIDTH - 30, y))
            y += 8
            head_r = self.font_body.render("RESOLUTION", True, (100, 160, 230))
            self.screen.blit(head_r, (30, y))
            for btn in self.res_buttons:
                btn.draw(self.screen)
            y = self._sections["res_y"] + 42
            pygame.draw.line(self.screen, (50, 50, 60), (30, y), (SCREEN_WIDTH - 30, y))
            y += 8
            head_m = self.font_body.render("MAP", True, (180, 140, 220))
            self.screen.blit(head_m, (30, y))
            for btn in self.map_buttons:
                btn.draw(self.screen)
            m = self.maps[self.selected_map]
            parts = []
            if m["grid_size"]:
                parts.append(f"{m['grid_size']}x{m['grid_size']} grid")
            if m["num_lights"]:
                parts.append(f"{m['num_lights']} light{'s' if m['num_lights'] != 1 else ''}")
            if m["num_dynamic"]:
                parts.append(f"{m['num_dynamic']} object{'s' if m['num_dynamic'] != 1 else ''}")
            if m["num_bots"]:
                parts.append(f"{m['num_bots']} bot{'s' if m['num_bots'] != 1 else ''}")
            map_info = f"{m['name']}  \u2014  {', '.join(parts)}" if parts else m["name"]
            map_label = self.font_small.render(map_info, True, ORANGE)
            self.screen.blit(map_label, (30, self._sections["map_y"] + 40))

            self.play_button.draw(self.screen)

            hint = self.font_small.render("Enter = Play | Esc = Quit", True, GRAY)
            self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 25))

            pygame.display.flip()

    def launch_game(self):
        width, height = RESOLUTIONS[self.selected_res]
        quality = self.selected_quality
        ver = VERSIONS[self.selected_version]
        config = {
            "screen_width": width,
            "screen_height": height,
            "quality": quality,
            "map_file": self.maps[self.selected_map]["file"],
            "spawn_x": 10,
            "spawn_y": 10,
            "player_speed": 5.0,
        }
        with open("config.json", "w") as f:
            json.dump(config, f)

        pygame.display.quit()
        subprocess.run([sys.executable, ver["file"]])
        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    launcher = Launcher()
    launcher.run()
