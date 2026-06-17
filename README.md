# LightEngine

A 2D top-down lighting and visibility engine built with Python and Pygame. Features raycast-based field-of-view, colored light sources, dynamic/static lights, particle effects, flicker simulation, wall edge light spill, and NPC bots with line-of-sight AI.

## Versions

| Version | File | Highlights |
|---------|------|------------|
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
| B | Toggle debug overlay |
| N | Toggle semi-debug info |

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

## Map Format

Maps are JSON files with a 2D grid, static lights, dynamic objects, and bot definitions. See `maps/default.json` for an example.

## License

MIT License — see [LICENSE](LICENSE).
