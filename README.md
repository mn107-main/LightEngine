# LightEngine

A 2D top-down lighting and visibility engine built with Python and Pygame. Features raycast-based field-of-view, colored light sources, dynamic/static lights, particle effects, flicker simulation, wall edge light spill, and NPC bots with line-of-sight AI.

## Versions

| Version | File | Highlights |
|---------|------|------------|
| **LE 4.0.0** | `le4.0.0.py` | Weather (rain/snow/fog), day/night cycle, bot AI states (patrol/investigate/alert), ray debug, logging, profiler, hot-reload, sprite animation |
| **LE 3.0.0** | `le3.0.0.py` | Bot NPCs with LOS, scripting, pathfinding; player light toggle |
| **LE 2.0.0** | `le2.0.0.py` | Quality presets, colored lights, flicker, particles, wall spill |
| **LE 1.0.0** | `le1.0.0.py` | Raycast cone-of-sight, static & dynamic lights, debug modes |
| **oldver/le0.0.1-4** | `oldver/` | Early prototypes: Bresenham FOV, raycast polygons, gradients |

## Requirements

- Python 3
- Pygame (`pip install pygame`)

## Quick Start

```bash
python launcher.py
```

Or run a specific version directly:

```bash
python le3.0.0.py
```

## Controls

| Key | Action |
|-----|--------|
| WASD | Move player |
| Mouse | Aim |
| L | Toggle player light |
| B | Toggle full debug overlay |
| N | Toggle semi-debug info |
| R | Toggle ray debug visualization |
| H | Hot-reload config.json |
| + / - | Speed up / slow down day cycle |

## Configuration

Edit `config.json` to set screen size, quality preset, map file, spawn position, and player speed.

### Quality Presets

| Parameter | Low | Normal | Max |
|-----------|-----|--------|-----|
| Ray step | 3.0° | 1.2° | 0.5° |
| Cast step | 12 px | 6 px | 3 px |
| Gradient resolution | 16 | 32 | 64 |
| Colored lights | No | Yes | Yes |
| Particles | No | Yes | Yes |
| Flicker | No | Yes | Yes |
| Weather | No | Yes | Yes |
| Day/Night | No | Yes | Yes |

## Maps

| Map | File | Description |
|-----|------|-------------|
| Default | `maps/default.json` | Basic arena with central obstruction |
| Cave | `maps/cave.json` | Underground cave with narrow passages |
| Room | `maps/room.json` | Indoor environment with multiple rooms |
| Open Space | `maps/open_space.json` | Large open area with few obstacles |

## Map Format

Maps are JSON files with a 2D grid, static lights, dynamic objects, and bot definitions. See `maps/default.json` for an example.

### Bot Patrol System

Bots in LE 4.0.0 support AI states: `idle`, `patrol`, `investigate`, `alert`, `follow`, `guard`. Add patrol points to bot definitions:

```json
{
    "id": 0, "x": 6, "y": 6,
    "light_radius": 2.5, "light_intensity": 0.6,
    "color": [0, 120, 255], "speed": 1.5,
    "patrol": [[6,6], [14,6], [14,14], [6,14]]
}
```

### Bot Scripting API

| Method | Description |
|--------|-------------|
| `bot.goto(x, y)` | Move to grid cell |
| `bot.lookto(x, y)` | Look towards position |
| `bot.light(on)` | Enable/disable bot light |
| `bot.wait(seconds)` | Wait for duration |
| `bot.rate(hz)` | Set script tick rate |
| `bot.say(text, duration)` | Display speech bubble |
| `bot.follow(ref)` | Follow a reference (player, bot, light) |
| `bot.guard(ref, radius)` | Guard within radius of reference |
| `bot.follow_path(path)` | Follow a list of waypoints |
| `bot.set_patrol(points)` | Set patrol waypoints with AI state |
| `bot.set_state(state)` | Force AI state |
| `bot.distance_to(x, y)` | Distance to position |
| `bot.wot(x, y)` | Check line-of-sight obstruction |
| `bot.on(event, cb)` | Register event handler |
| `bot.emit(event)` | Emit event |

References: `"player"`, `"static#0"`, `"dynamic#0"`, `"bot#0"`

### Weather System

LE 4.0.0 features dynamic weather: rain, snow, and fog. Weather is randomly selected on startup when quality is Normal or Max. The day/night cycle smoothly transitions ambient brightness with a sinusoidal curve (use +/- keys to adjust speed).

## Future Ideas

- **Map Editor** — visual editor inside Pygame for placing walls, lights, and NPC spawn points, saving to JSON
- **Fog of War** — classic RTS fog that clears only around the player and allies, stays gray beyond
- **Entity Animation** — sprites with frame animation from atlas for NPCs and the player
- **Network Mode** — client-server via sockets/websockets for multiplayer movement

## License

MIT License — see [LICENSE](LICENSE).
