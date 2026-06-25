import pygame
import json
import os
import sys
import math
from collections import OrderedDict

pygame.init()

SCREEN_W, SCREEN_H = 1100, 700
SIDEBAR_W = 240
TOOLBAR_H = 44
STATUSBAR_H = 28
GRID_AREA_W = SCREEN_W - SIDEBAR_W
GRID_AREA_H = SCREEN_H - TOOLBAR_H - STATUSBAR_H

BLACK = (10, 10, 10)
WHITE = (220, 220, 220)
GRAY = (60, 60, 60)
LIGHT_GRAY = (130, 130, 130)
DARK_GRAY = (35, 35, 35)
ACCENT = (80, 180, 100)
ACCENT_HOVER = (100, 220, 120)
BLUE = (60, 120, 220)
RED = (220, 60, 60)
ORANGE = (220, 160, 60)
WALL_COLOR = (45, 45, 55)
WALL_BORDER = (60, 60, 75)
GRID_LINE = (30, 30, 38)
PLAYER_COLOR = (0, 240, 0)
BG_COLOR = (15, 15, 20)

COLOR_PRESETS = [
    (255, 200, 130), (130, 180, 255), (255, 240, 160),
    (180, 255, 180), (255, 160, 160), (200, 130, 255),
    (255, 200, 200), (160, 200, 255), (255, 220, 100),
    (100, 255, 200), (255, 150, 200), (150, 200, 200),
]

TOOLS = ["wall", "eraser", "light", "object", "bot", "player", "select"]
TOOL_LABELS = {
    "wall": "Wall", "eraser": "Eraser", "light": "Light", "object": "Object",
    "bot": "Bot", "player": "Player", "select": "Select",
}
TOOL_COLORS = {
    "wall": (100, 100, 120), "eraser": (200, 60, 60), "light": (255, 200, 80),
    "object": (220, 120, 60), "bot": (80, 160, 255), "player": (0, 240, 0),
    "select": (180, 180, 180),
}
TOOL_HOTKEYS = {
    "1": "wall", "2": "eraser", "3": "light", "4": "object",
    "5": "bot", "6": "player", "7": "select",
}


class Button:
    def __init__(self, rect, text, color, hover_color, text_color=WHITE, font_size=16):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font = pygame.font.Font(None, font_size)
        self.hovered = False

    def draw(self, screen):
        c = self.hover_color if self.hovered else self.color
        pygame.draw.rect(screen, c, self.rect, border_radius=4)
        if self.hovered:
            pygame.draw.rect(screen, WHITE, self.rect, 1, border_radius=4)
        t = self.font.render(self.text, True, self.text_color)
        r = t.get_rect(center=self.rect.center)
        screen.blit(t, r)

    def update(self, pos):
        self.hovered = self.rect.collidepoint(pos)

    def clicked(self, pos, btn):
        return self.hovered and btn


class MapEditor:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("LightEngine Map Editor")
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_small = pygame.font.Font(None, 16)
        self.font_body = pygame.font.Font(None, 20)
        self.font_heading = pygame.font.Font(None, 24)
        self.font_tool = pygame.font.Font(None, 18)

        self.tool = "wall"
        self.grid_size = 20
        self.map_grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self._init_default_map()
        self.player_spawn = [10, 10]
        self.static_lights = []
        self.dynamic_objects = []
        self.bots = []
        self.next_id = 0

        self.camera_x = 0.0
        self.camera_y = 0.0
        self.dragging = False
        self.drag_start = None
        self.drag_entity = None
        self.drag_entity_offset = (0, 0)
        self.selected_entity = None
        self.selected_type = None
        self.hover_cell = None
        self.mouse_pos = (0, 0)
        self.mouse_buttons = [False, False, False]
        self.keys = {}
        self.unsaved = False

        self.current_file = None
        self.status_msg = "Ready"
        self.status_timer = 0

        self.grid_cell_size = 24
        self._calc_cell_size()

        self._init_ui()
        self._make_buttons()

    def _init_default_map(self):
        sz = self.grid_size
        for i in range(sz):
            self.map_grid[0][i] = 1
            self.map_grid[sz - 1][i] = 1
            self.map_grid[i][0] = 1
            self.map_grid[i][sz - 1] = 1

    def _calc_cell_size(self):
        mw = self.grid_size
        mh = self.grid_size
        self.grid_cell_size = max(8, min(
            GRID_AREA_W // mw,
            GRID_AREA_H // mh,
            40,
        ))
        self.grid_pixel_w = mw * self.grid_cell_size
        self.grid_pixel_h = mh * self.grid_cell_size
        self.grid_offset_x = (GRID_AREA_W - self.grid_pixel_w) // 2
        self.grid_offset_y = TOOLBAR_H + (GRID_AREA_H - self.grid_pixel_h) // 2

    def _init_ui(self):
        pass

    def _make_buttons(self):
        self.tool_buttons = OrderedDict()
        x = 8
        for tid in TOOLS:
            w = 58
            self.tool_buttons[tid] = Button(
                (x, 8, w, TOOLBAR_H - 12),
                TOOL_LABELS[tid], DARK_GRAY, LIGHT_GRAY,
                font_size=14,
            )
            x += w + 4

        self.save_btn = Button((SCREEN_W - SIDEBAR_W - 180, 8, 72, TOOLBAR_H - 12), "Save", ACCENT, ACCENT_HOVER)
        self.load_btn = Button((SCREEN_W - SIDEBAR_W - 104, 8, 72, TOOLBAR_H - 12), "Load", GRAY, LIGHT_GRAY)
        self.new_btn = Button((SCREEN_W - SIDEBAR_W - 28, 8, 24, TOOLBAR_H - 12), "N", GRAY, LIGHT_GRAY, font_size=14)

        self.prop_buttons = {}

    def screen_to_grid(self, sx, sy):
        gx = sx - self.grid_offset_x
        gy = sy - self.grid_offset_y
        cx = int(gx // self.grid_cell_size)
        cy = int(gy // self.grid_cell_size)
        return cx, cy

    def grid_to_screen(self, cx, cy):
        return (cx * self.grid_cell_size + self.grid_offset_x,
                cy * self.grid_cell_size + self.grid_offset_y)

    def get_entity_at(self, cx, cy):
        margin = 0.4
        for i, l in enumerate(self.static_lights):
            if abs(l["x"] - cx) <= margin and abs(l["y"] - cy) <= margin:
                return ("light", i), l
        for i, o in enumerate(self.dynamic_objects):
            if abs(o["x"] - cx) <= margin and abs(o["y"] - cy) <= margin:
                return ("object", i), o
        for i, b in enumerate(self.bots):
            if abs(b["x"] - cx) <= margin and abs(b["y"] - cy) <= margin:
                return ("bot", i), b
        if abs(self.player_spawn[0] - cx) <= margin and abs(self.player_spawn[1] - cy) <= margin:
            return ("player", 0), self.player_spawn
        return None, None

    def add_entity(self, etype, cx, cy):
        eid = self.next_id
        self.next_id += 1
        if etype == "light":
            c = COLOR_PRESETS[len(self.static_lights) % len(COLOR_PRESETS)]
            self.static_lights.append({
                "id": eid, "x": cx, "y": cy, "radius_cells": 3, "intensity": 0.7, "color": c,
            })
        elif etype == "object":
            c = COLOR_PRESETS[(len(self.dynamic_objects) + 3) % len(COLOR_PRESETS)]
            self.dynamic_objects.append({
                "id": eid, "x": cx, "y": cy, "light_radius": 1.5, "light_intensity": 0.4, "color": c,
            })
        elif etype == "bot":
            c = COLOR_PRESETS[(len(self.bots) + 6) % len(COLOR_PRESETS)]
            self.bots.append({
                "id": eid, "x": cx, "y": cy, "light_radius": 2.0, "light_intensity": 0.5,
                "color": c, "speed": 1.5,
            })
        elif etype == "player":
            self.player_spawn = [cx, cy]
        self.unsaved = True

    def remove_entity(self, etype, idx):
        if etype == "light" and 0 <= idx < len(self.static_lights):
            self.static_lights.pop(idx)
        elif etype == "object" and 0 <= idx < len(self.dynamic_objects):
            self.dynamic_objects.pop(idx)
        elif etype == "bot" and 0 <= idx < len(self.bots):
            self.bots.pop(idx)
        elif etype == "player":
            self.player_spawn = [self.grid_size // 2, self.grid_size // 2]
        self.selected_entity = None
        self.selected_type = None
        self.unsaved = True

    def cycle_color(self, entity, forward=True):
        if "color" in entity:
            pal = COLOR_PRESETS
            cur = entity["color"]
            try:
                i = pal.index(tuple(cur))
            except ValueError:
                i = -1
            nxt = (i + (1 if forward else -1)) % len(pal)
            entity["color"] = list(pal[nxt])
            self.unsaved = True

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            if self.unsaved:
                r = self._confirm_dialog("Unsaved changes. Quit?")
                if r:
                    self.running = False
            else:
                self.running = False
            return

        if event.type == pygame.KEYDOWN:
            self.keys[event.key] = True
            if event.key == pygame.K_ESCAPE:
                self.tool = "select"
                self.selected_entity = None
                self.selected_type = None
            elif event.key == pygame.K_TAB:
                idx = TOOLS.index(self.tool)
                self.tool = TOOLS[(idx + 1) % len(TOOLS)]
                self.set_status(f"Tool: {TOOL_LABELS[self.tool]}")
            elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                if self.selected_entity is not None:
                    self.remove_entity(self.selected_type, self.selected_entity)
            elif event.key == pygame.K_c:
                if self.selected_entity is not None:
                    e = self._get_selected_entity_data()
                    if e is not None:
                        self.cycle_color(e, forward=False)
            elif event.key == pygame.K_r:
                if self.selected_entity is not None:
                    e = self._get_selected_entity_data()
                    if e is not None:
                        self.cycle_color(e, forward=True)
            elif event.key == pygame.K_s and (self.keys.get(pygame.K_LCTRL) or self.keys.get(pygame.K_RCTRL)):
                self.save_map()
            elif event.key == pygame.K_o and (self.keys.get(pygame.K_LCTRL) or self.keys.get(pygame.K_RCTRL)):
                self.load_map()
            elif event.key == pygame.K_n and (self.keys.get(pygame.K_LCTRL) or self.keys.get(pygame.K_RCTRL)):
                self.new_map()
            else:
                for k, tid in TOOL_HOTKEYS.items():
                    km = getattr(pygame, f"K_{k}", None)
                    if km is not None and event.key == km:
                        self.tool = tid
                        self.set_status(f"Tool: {TOOL_LABELS[self.tool]}")
                        break
            return

        if event.type == pygame.KEYUP:
            self.keys[event.key] = False
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            btn = event.button
            self.mouse_buttons[btn - 1] = True

            if btn == 1:
                handled = self._handle_toolbar_click(pos)
                if handled:
                    return
                handled = self._handle_sidebar_click(pos)
                if handled:
                    return

                if pos[0] < GRID_AREA_W:
                    cx, cy = self.screen_to_grid(pos[0], pos[1])
                    if 0 <= cx < self.grid_size and 0 <= cy < self.grid_size:
                        self._handle_grid_click(cx, cy, pos)
            elif btn == 3:
                cx, cy = self.screen_to_grid(pos[0], pos[1])
                if 0 <= cx < self.grid_size and 0 <= cy < self.grid_size:
                    if self.tool == "eraser" or self.tool == "wall":
                        self.map_grid[cy][cx] = 0
                        self.unsaved = True
                    else:
                        etype_idx, _ = self.get_entity_at(cx, cy)
                        if etype_idx:
                            self.remove_entity(etype_idx[0], etype_idx[1])
                            self.set_status(f"Removed {etype_idx[0]}")
            elif btn == 4:
                self._adjust_selected_prop(-1)
            elif btn == 5:
                self._adjust_selected_prop(1)
            return

        if event.type == pygame.MOUSEBUTTONUP:
            pos = event.pos
            btn = event.button
            self.mouse_buttons[btn - 1] = False
            if btn == 1 and self.dragging:
                self.dragging = False
                self.drag_entity = None
            return

        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos

    def _handle_toolbar_click(self, pos):
        for tid, btn in self.tool_buttons.items():
            if btn.clicked(pos, True):
                self.tool = tid
                self.set_status(f"Tool: {TOOL_LABELS[tid]}")
                return True
        if self.save_btn.clicked(pos, True):
            self.save_map()
            return True
        if self.load_btn.clicked(pos, True):
            self.load_map()
            return True
        if self.new_btn.clicked(pos, True):
            self.new_map()
            return True
        return False

    def _handle_sidebar_click(self, pos):
        if pos[0] < GRID_AREA_W:
            return False
        return False

    def _get_selected_entity_data(self):
        if self.selected_type == "light" and self.selected_entity is not None:
            idx = self.selected_entity
            if 0 <= idx < len(self.static_lights):
                return self.static_lights[idx]
        elif self.selected_type == "object" and self.selected_entity is not None:
            idx = self.selected_entity
            if 0 <= idx < len(self.dynamic_objects):
                return self.dynamic_objects[idx]
        elif self.selected_type == "bot" and self.selected_entity is not None:
            idx = self.selected_entity
            if 0 <= idx < len(self.bots):
                return self.bots[idx]
        elif self.selected_type == "player":
            return self.player_spawn
        return None

    def _adjust_selected_prop(self, direction):
        e = self._get_selected_entity_data()
        if e is None:
            return
        if isinstance(e, list):
            return
        keys = ["radius_cells", "light_radius", "intensity", "light_intensity", "speed"]
        for k in keys:
            if k in e:
                delta = 0.5 if direction > 0 else -0.5
                if k in ("radius_cells",):
                    delta = 1 if direction > 0 else -1
                v = e[k] + delta
                if k in ("radius_cells",) and v >= 1:
                    e[k] = int(v)
                elif k in ("intensity", "light_intensity", "speed"):
                    e[k] = max(0.1, min(3.0, round(v, 2)))
                self.unsaved = True
                self.set_status(f"{k}: {e[k]}")
                break

    def _handle_grid_click(self, cx, cy, pos):
        if self.tool == "wall":
            self.map_grid[cy][cx] = 1
            self.unsaved = True
        elif self.tool == "eraser":
            self.map_grid[cy][cx] = 0
            self.unsaved = True
        elif self.tool == "select":
            etype_idx, edata = self.get_entity_at(cx, cy)
            if etype_idx:
                self.selected_type, self.selected_entity = etype_idx
                self.dragging = True
                self.drag_entity = etype_idx
                dx = (pos[0] - self.grid_offset_x) / self.grid_cell_size - edata["x"] if isinstance(edata, dict) else 0
                dy = (pos[1] - self.grid_offset_y) / self.grid_cell_size - edata["y"] if isinstance(edata, dict) else 0
                self.drag_entity_offset = (dx, dy)
            else:
                self.selected_entity = None
                self.selected_type = None
        elif self.tool in ("light", "object", "bot", "player"):
            if self.tool == "player":
                self.player_spawn = [cx, cy]
                self.unsaved = True
                self.set_status(f"Player spawn: ({cx}, {cy})")
            else:
                self.add_entity(self.tool, cx, cy)
                self.set_status(f"Placed {TOOL_LABELS[self.tool]} at ({cx}, {cy})")

    def _confirm_dialog(self, msg):
        w, h = 360, 120
        sx, sy = (SCREEN_W - w) // 2, (SCREEN_H - h) // 2
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, DARK_GRAY, (sx, sy, w, h), border_radius=8)
        pygame.draw.rect(self.screen, LIGHT_GRAY, (sx, sy, w, h), 1, border_radius=8)
        t = self.font_body.render(msg, True, WHITE)
        self.screen.blit(t, (sx + 20, sy + 20))

        yes_btn = Button((sx + 30, sy + 70, 80, 32), "Yes", RED, (255, 100, 100))
        no_btn = Button((sx + w - 110, sy + 70, 80, 32), "No", GRAY, LIGHT_GRAY)
        pygame.display.flip()

        waiting = True
        result = False
        while waiting:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return True
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    p = ev.pos
                    if yes_btn.clicked(p, True):
                        result = True
                        waiting = False
                    elif no_btn.clicked(p, True):
                        result = False
                        waiting = False
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    waiting = False
            mp = pygame.mouse.get_pos()
            yes_btn.update(mp)
            no_btn.update(mp)
            yes_btn.draw(self.screen)
            no_btn.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(30)
        return result

    def set_status(self, msg):
        self.status_msg = msg
        self.status_timer = 180

    def new_map(self):
        if self.unsaved:
            r = self._confirm_dialog("Unsaved changes. Create new?")
            if not r:
                return
        self.map_grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self._init_default_map()
        self.static_lights = []
        self.dynamic_objects = []
        self.bots = []
        self.player_spawn = [self.grid_size // 2, self.grid_size // 2]
        self.next_id = 0
        self.selected_entity = None
        self.selected_type = None
        self.current_file = None
        self.unsaved = False
        self.set_status("New map created")

    def save_map(self):
        data = {
            "name": os.path.splitext(os.path.basename(self.current_file or "untitled"))[0],
            "player_spawn": self.player_spawn,
            "map": self.map_grid,
            "static_lights": self.static_lights,
            "dynamic_objects": self.dynamic_objects,
            "bots": self.bots,
        }
        if self.current_file is None:
            self.current_file = "maps/untitled.json"
        with open(self.current_file, "w") as f:
            json.dump(data, f, indent=4)
        self.unsaved = False
        self.set_status(f"Saved: {self.current_file}")

    def load_map(self, fpath=None):
        if self.unsaved:
            r = self._confirm_dialog("Unsaved changes. Load another?")
            if not r:
                return
        if fpath is None:
            fpath = self._file_dialog()
        if not fpath or not os.path.exists(fpath):
            return
        with open(fpath) as f:
            data = json.load(f)
        self.map_grid = data.get("map", self.map_grid)
        self.grid_size = len(self.map_grid)
        self.player_spawn = data.get("player_spawn", [self.grid_size // 2, self.grid_size // 2])
        self.static_lights = data.get("static_lights", [])
        self.dynamic_objects = data.get("dynamic_objects", [])
        self.bots = data.get("bots", [])
        self.current_file = fpath
        self.unsaved = False
        self.selected_entity = None
        self.selected_type = None
        self._calc_cell_size()
        self.set_status(f"Loaded: {fpath}")

    def _file_dialog(self):
        maps_dir = "maps"
        if not os.path.isdir(maps_dir):
            return None
        files = sorted([f for f in os.listdir(maps_dir) if f.endswith(".json")])
        if not files:
            return None
        w, h = 400, 300
        sx, sy = (SCREEN_W - w) // 2, (SCREEN_H - h) // 2
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, DARK_GRAY, (sx, sy, w, h), border_radius=8)
        pygame.draw.rect(self.screen, LIGHT_GRAY, (sx, sy, w, h), 1, border_radius=8)

        buttons = []
        fh = 28
        for i, fn in enumerate(files):
            by = sy + 16 + i * (fh + 4)
            if by + fh > sy + h - 10:
                break
            btn = Button((sx + 10, by, w - 20, fh), fn, GRAY, LIGHT_GRAY, font_size=16)
            buttons.append((btn, fn))
            btn.draw(self.screen)
        cancel_btn = Button((sx + w // 2 - 40, sy + h - 36, 80, 28), "Cancel", GRAY, LIGHT_GRAY)
        cancel_btn.draw(self.screen)
        pygame.display.flip()

        waiting = True
        result = None
        while waiting:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    p = ev.pos
                    if cancel_btn.clicked(p, True):
                        waiting = False
                    for btn, fn in buttons:
                        if btn.clicked(p, True):
                            result = os.path.join(maps_dir, fn)
                            waiting = False
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    waiting = False
            mp = pygame.mouse.get_pos()
            for btn, _ in buttons:
                btn.update(mp)
                btn.draw(self.screen)
            cancel_btn.update(mp)
            cancel_btn.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(30)
        return result

    def update(self):
        dt = self.clock.get_time() / 1000.0
        if self.status_timer > 0:
            self.status_timer -= 1

        for tid, btn in self.tool_buttons.items():
            btn.update(self.mouse_pos)
        self.save_btn.update(self.mouse_pos)
        self.load_btn.update(self.mouse_pos)
        self.new_btn.update(self.mouse_pos)

        cx, cy = self.screen_to_grid(self.mouse_pos[0], self.mouse_pos[1])
        self.hover_cell = (cx, cy) if 0 <= cx < self.grid_size and 0 <= cy < self.grid_size else None

        if self.dragging and self.mouse_buttons[0] and self.drag_entity:
            gx = (self.mouse_pos[0] - self.grid_offset_x) / self.grid_cell_size - self.drag_entity_offset[0]
            gy = (self.mouse_pos[1] - self.grid_offset_y) / self.grid_cell_size - self.drag_entity_offset[1]
            gx = max(0, min(self.grid_size - 0.01, gx))
            gy = max(0, min(self.grid_size - 0.01, gy))
            etype, idx = self.drag_entity
            if etype == "light" and 0 <= idx < len(self.static_lights):
                self.static_lights[idx]["x"] = round(gx, 2)
                self.static_lights[idx]["y"] = round(gy, 2)
                self.unsaved = True
            elif etype == "object" and 0 <= idx < len(self.dynamic_objects):
                self.dynamic_objects[idx]["x"] = round(gx, 2)
                self.dynamic_objects[idx]["y"] = round(gy, 2)
                self.unsaved = True
            elif etype == "bot" and 0 <= idx < len(self.bots):
                self.bots[idx]["x"] = round(gx, 2)
                self.bots[idx]["y"] = round(gy, 2)
                self.unsaved = True
            elif etype == "player":
                self.player_spawn[0] = round(gx, 2)
                self.player_spawn[1] = round(gy, 2)
                self.unsaved = True

        if self.mouse_buttons[0] and self.tool in ("wall", "eraser") and self.hover_cell:
            cx, cy = self.hover_cell
            v = 1 if self.tool == "wall" else 0
            if self.map_grid[cy][cx] != v:
                self.map_grid[cy][cx] = v
                self.unsaved = True

    def draw(self):
        self.screen.fill(BG_COLOR)

        self._draw_grid()
        self._draw_entities()
        self._draw_toolbar()
        self._draw_sidebar()
        self._draw_statusbar()

        pygame.display.flip()

    def _draw_toolbar(self):
        pygame.draw.rect(self.screen, DARK_GRAY, (0, 0, SCREEN_W, TOOLBAR_H))
        pygame.draw.line(self.screen, GRAY, (0, TOOLBAR_H), (SCREEN_W, TOOLBAR_H))
        for tid, btn in self.tool_buttons.items():
            bs = (tid == self.tool)
            if bs:
                c = TOOL_COLORS[tid]
                btn.color = c
                btn.text_color = BLACK
            else:
                btn.color = DARK_GRAY
                btn.text_color = WHITE
            btn.draw(self.screen)
        self.save_btn.draw(self.screen)
        self.load_btn.draw(self.screen)
        self.new_btn.draw(self.screen)

    def _draw_statusbar(self):
        y = SCREEN_H - STATUSBAR_H
        pygame.draw.rect(self.screen, DARK_GRAY, (0, y, SCREEN_W, STATUSBAR_H))
        pygame.draw.line(self.screen, GRAY, (0, y), (SCREEN_W, y))

        parts = [f"Tool: {TOOL_LABELS[self.tool]}"]
        if self.hover_cell:
            parts.append(f"Cell: ({self.hover_cell[0]}, {self.hover_cell[1]})")
        parts.append(f"Grid: {self.grid_size}x{self.grid_size}")
        parts.append(f"Walls: {sum(row.count(1) for row in self.map_grid)}")
        parts.append(f"L: {len(self.static_lights)} O: {len(self.dynamic_objects)} B: {len(self.bots)}")
        if self.unsaved:
            parts.append("*unsaved*")

        msg = self.status_msg if self.status_timer > 0 else " | ".join(parts)
        t = self.font_small.render(msg, True, LIGHT_GRAY)
        self.screen.blit(t, (10, y + 6))

    def _draw_grid(self):
        cs = self.grid_cell_size
        ox, oy = self.grid_offset_x, self.grid_offset_y

        for y in range(self.grid_size):
            for x in range(self.grid_size):
                sx = ox + x * cs
                sy = oy + y * cs
                if self.map_grid[y][x] == 1:
                    pygame.draw.rect(self.screen, WALL_COLOR, (sx, sy, cs, cs))
                    if cs >= 6:
                        pygame.draw.rect(self.screen, WALL_BORDER, (sx, sy, cs, cs), 1)
                else:
                    pygame.draw.rect(self.screen, BG_COLOR, (sx, sy, cs, cs))
                    if cs >= 6:
                        pygame.draw.rect(self.screen, GRID_LINE, (sx, sy, cs, cs), 1)

        if self.hover_cell and 0 <= self.hover_cell[0] < self.grid_size and 0 <= self.hover_cell[1] < self.grid_size:
            hx, hy = self.hover_cell
            hsx = ox + hx * cs
            hsy = oy + hy * cs
            s = pygame.Surface((cs, cs), pygame.SRCALPHA)
            s.fill((255, 255, 255, 40))
            self.screen.blit(s, (hsx, hsy))

    def _draw_entities(self):
        cs = self.grid_cell_size
        ox, oy = self.grid_offset_x, self.grid_offset_y

        for l in self.static_lights:
            sx = int(ox + l["x"] * cs)
            sy = int(oy + l["y"] * cs)
            r = int(cs * 0.5)
            c = tuple(l["color"])
            pygame.draw.circle(self.screen, c, (sx, sy), r + 2)
            pygame.draw.circle(self.screen, WHITE, (sx, sy), r)
            pygame.draw.circle(self.screen, c, (sx, sy), r, 2)

        for o in self.dynamic_objects:
            sx = int(ox + o["x"] * cs)
            sy = int(oy + o["y"] * cs)
            r = int(cs * 0.35)
            c = tuple(o["color"])
            pygame.draw.circle(self.screen, c, (sx, sy), r + 1)
            pygame.draw.circle(self.screen, WHITE, (sx, sy), r)
            pts = [(sx, sy - r - 3), (sx - 3, sy + r), (sx + 3, sy + r)]
            pygame.draw.polygon(self.screen, c, pts)

        for b in self.bots:
            sx = int(ox + b["x"] * cs)
            sy = int(oy + b["y"] * cs)
            r = int(cs * 0.42)
            c = tuple(b["color"])
            pygame.draw.circle(self.screen, c, (sx, sy), r + 1)
            pygame.draw.circle(self.screen, WHITE, (sx, sy), r)
            eye_off = r // 3
            for ex, ey_dir in [(-1, -1), (1, -1)]:
                ex_pos = (sx + ex * eye_off, sy + ey_dir * eye_off)
                pygame.draw.circle(self.screen, BLACK, ex_pos, 2)
                pygame.draw.circle(self.screen, WHITE, ex_pos, 1)

        psx = int(ox + self.player_spawn[0] * cs)
        psy = int(oy + self.player_spawn[1] * cs)
        pr = int(cs * 0.4)
        pygame.draw.circle(self.screen, BLACK, (psx, psy), pr + 2)
        pygame.draw.circle(self.screen, PLAYER_COLOR, (psx, psy), pr)
        pex = psx + int(math.cos(0) * pr * 0.9)
        pey = psy + int(math.sin(0) * pr * 0.9)
        pygame.draw.line(self.screen, BLACK, (psx, psy), (pex, pey), 3)

    def _draw_sidebar(self):
        x = GRID_AREA_W
        pygame.draw.rect(self.screen, DARK_GRAY, (x, 0, SIDEBAR_W, SCREEN_H))
        pygame.draw.line(self.screen, GRAY, (x, 0), (x, SCREEN_H))

        yy = TOOLBAR_H + 8
        head = self.font_heading.render("Properties", True, WHITE)
        self.screen.blit(head, (x + 10, yy))
        yy += 30

        e = self._get_selected_entity_data()
        if e is not None and self.selected_type is not None:
            t = self.font_body.render(f"Type: {self.selected_type}", True, ORANGE)
            self.screen.blit(t, (x + 10, yy))
            yy += 22

            if self.selected_type == "player" and isinstance(e, list):
                t = self.font_small.render(f"Spawn: ({e[0]:.1f}, {e[1]:.1f})", True, LIGHT_GRAY)
                self.screen.blit(t, (x + 10, yy))
                yy += 18
                t = self.font_small.render("Drag to move | C/R = color", True, LIGHT_GRAY)
                self.screen.blit(t, (x + 10, yy))
                yy += 18
            elif isinstance(e, dict):
                for k, v in e.items():
                    if k == "id":
                        continue
                    if isinstance(v, list):
                        v = f"({v[0]}, {v[1]}, {v[2]})"
                    txt = f"{k}: {v}"
                    t = self.font_small.render(txt, True, LIGHT_GRAY)
                    self.screen.blit(t, (x + 10, yy))
                    yy += 16
                yy += 8
                t = self.font_small.render("Scroll: adjust value", True, (180, 180, 100))
                self.screen.blit(t, (x + 10, yy))
                yy += 16
                t = self.font_small.render("C/R: cycle color", True, (180, 180, 100))
                self.screen.blit(t, (x + 10, yy))
                yy += 16
        else:
            t = self.font_small.render("No entity selected", True, GRAY)
            self.screen.blit(t, (x + 10, yy))
            yy += 22

        yy = max(yy, TOOLBAR_H + 200)
        yy += 16
        help_items = [
            ("1-7", "Select tool"),
            ("Tab", "Cycle tools"),
            ("LMB", "Place / Select"),
            ("RMB", "Delete entity"),
            ("Drag", "Move entity"),
            ("Scroll", "Adjust value"),
            ("C/R", "Cycle color"),
            ("Del", "Remove selected"),
            ("Ctrl+S", "Save"),
            ("Ctrl+O", "Load"),
            ("Ctrl+N", "New"),
        ]
        t = self.font_heading.render("Help", True, WHITE)
        self.screen.blit(t, (x + 10, yy))
        yy += 22
        for key, desc in help_items:
            t = self.font_small.render(f"{key}: {desc}", True, GRAY)
            self.screen.blit(t, (x + 10, yy))
            yy += 16

    def run(self):
        while self.running:
            self.clock.tick(60)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update()
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    editor = MapEditor()
    if len(sys.argv) > 1:
        editor.load_map(sys.argv[1])
    editor.run()
