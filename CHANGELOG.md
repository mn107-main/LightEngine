# Changelog

## 4.0.0 — 2026

### Major
- **Weather system** — dynamic rain, snow, and fog with per-particle physics
- **Day/night cycle** — smooth ambient brightness oscillation, adjustable speed (+/- keys)
- **Extended bot AI** — three-state behavior: `patrol` (waypoints), `investigate` (last known player pos), `alert` (chase with visual pulse)
- **Ray debug mode** (R key) — visualizes every cast ray for debugging raycasting
- **Profiler** — per-stage timing (input, update, scene, objects, lighting, particles)
- **Event logging** — game events written to `lightengine.log`
- **Hot-reload** (H key) — reloads `config.json` at runtime
- **Sprite animation** — objects pulse/animate, bots have eyes and idle bob

### Weather
- Three types: rain (streaks, high density), snow (gentle fall with wobble), fog (large translucent circles)
- Quality-gated: enabled on Normal and Max presets
- Randomized on each launch

### Day/Night
- Ambient brightness varies sinusoidally over time
- `+`/`-` keys increase/decrease cycle speed
- Affects scene rendering and weather visibility

### Bot AI states
- `patrol` — walks through `patrol` waypoints from map JSON, loops automatically
- `investigate` — moves to last known player position when alert level drops
- `alert` — high-alert chase mode with pulsing red ring; triggers on player sight
- `set_patrol(points)` — API method to set patrol route
- Alert level system — 0.0–1.0, rises while player visible, decays when hidden
- Memory: bots remember last seen player position and investigate it

### New maps
- `maps/cave.json` — underground cave with narrow corridors and violet crystal light
- `maps/room.json` — multi-room interior with warm ceiling lights
- `maps/open_space.json` — large arena with sparse cover and roaming bots
- Bot patrol points supported in JSON: `"patrol": [[x,y], [x,y], ...]`

### Config
- `config.json` now uses forward-slash paths (cross-platform)
- Added `player_light_radius`, `fov_angle_deg`, `ray_step_deg` fields

### UI
- Weather type and day factor displayed in normal HUD
- Profiler data shown in debug overlay
- Controls hint updated with R (ray debug), H (hot-reload), +/- (day speed)

---

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
