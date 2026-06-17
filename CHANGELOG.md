# Changelog

## 3.0.0 — 2026

### Major
- **Bot NPC system** — full NPC class with movement, line-of-sight, scripting, and AI behaviors
- **Player light toggle** — press L to turn the flashlight on/off

### Bot features
- `goto(x, y)` — move to a position or a named reference (e.g. `"player"`, `"stat#0"`, `"bot#2"`)
- `lookto(x, y)` / `light_xy(ref)` — aim the bot's gaze/light at a point or entity
- `wot(ref)` — line-of-sight check; returns `True` if the bot can see the target
- `light(on)` — toggle the bot's flashlight
- `start_func(func)` — run a user-defined script each frame
- `wait(seconds)` — pause execution
- `set_state(name)` — state machine support (idle, patrol, chase, etc.)
- `follow_path(points)` — traverse a sequence of waypoints
- `follow(ref)` / `guard(ref, radius)` — follow another bot or guard an object
- `say(text)` — display a speech bubble above the bot
- `on(event, callback)` — event handlers (e.g. `"see_player"`)
- **Reference system** — strings like `"stat#0"`, `"dinam#1"`, `"bot#2"`, `"player"` resolve to world objects

### Lighting
- Bot flashlights contribute to scene illumination and wall edge lighting
- Wall edge lighting updated to include bot light sources

### Rendering
- Bots drawn as colored circles with triangular "eye" indicators and a glow ring when lit

---

## 2.0.0 — 2026

### Major
- **Three quality presets** — Low, Normal, Max control ray density, cast step, gradient resolution, particles, flicker, and colored lights
- **Colored lights** — each light source has an RGB tint
- **Light flicker** — sinusoidal modulation of light intensity
- **Dust particles** — floating motes that appear in illuminated areas
- **Wall edge lighting** — wall borders rendered with per-subsegment light contribution and a "spill" algorithm that spreads light to adjacent dark edges
- **Static light precomputation** — wall illumination calculated once at map load
- **Dynamic object lighting** — objects only emit light if they themselves are illuminated

### Performance
- Line-of-sight cache for repeated visibility checks
- `--test` CLI flag for automated performance benchmarking (records FPS/TPS over a duration)

### UI
- TPS (ticks per second) counter alongside FPS
- "LIGHT ON / LIGHT OFF" indicator

### Bot (early)
- `Bot` class introduced but with limited functionality compared to v3.0.0

---

## 1.0.0 — 2026

- Raycast cone-of-sight lighting with configurable FOV angle
- Static light sources (warm, blue, yellow)
- Dynamic (movable) light sources (red, green)
- Per-light cached gradient surfaces
- Ambient light setting
- Debug overlay (B key) and semi-debug mode (N key)
- WASD movement + mouse aiming

---

## 0.0.4 — 2026

- Radial gradient lighting (bright center fading to ambient)
- Cached gradient surface for performance
- Split debug / semi-debug / normal info overlays

## 0.0.3 — 2026

- Raycast-based FOV polygon (cone of rays from player)
- Shadow rendering via multiplication of a white polygon on black surface

## 0.0.2 — 2026

- JSON config file loading
- Mouse-aim (player faces cursor)
- Smooth per-cell lighting (multi-sample per cell)
- Angle and distance falloff

## 0.0.1 — 2026

- First prototype
- Bresenham line rasterization for visibility checks
- Arrow-key movement
- Hardcoded FOV radius of 8 cells
- Black fog-of-war outside visible cells
