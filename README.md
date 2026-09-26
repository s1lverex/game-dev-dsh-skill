# game-dev-dsh-skill

A DeepSeek Harness **skill** that captures a complete, proven pipeline:

> procedural Blender assets -> Godot 4 runtime -> Web/WASM export -> hosting ->
> live browser verification, fix, repeat

It is not theory. Everything here was used to build and ship a playable third-person
cyberpunk game in a browser: a 200x200 m neon city, a rigged character with six keyframed
clips, a socketed pistol plus a first-person viewmodel, sedans/trucks/bikes you can steal and
drive, humanoid enforcers, quadruped mechs, an AR HUD, live HP/stamina/ammo, and a scripted
self-test that prints numeric evidence for every one of those systems.

## Install

```bash
git clone https://github.com/s1lverex/game-dev-dsh-skill.git
cd game-dev-dsh-skill
./install.sh          # copies into ~/.agents/skills and ~/.claude/skills
```

The harness picks skills up from `~/.agents/skills/<name>/SKILL.md`. Restart the session (or
reload plugins) and `blender-godot-web-pipeline` appears in the skill catalog.

## Contents

| Path | What it is |
|---|---|
| `SKILL.md` | Entry point: the five stages, the non-negotiable rules, the deliverable checklist |
| `reference/blender-assets.md` | Headless asset scripting, the coordinate contract, part-scoped skinning, pivots, sockets, viewer publishing |
| `reference/godot-runtime.md` | Web-compatible project settings, code-built scenes, the physics traps, camera architecture for TPS/FPS/vehicles, the raw-mouse bridge |
| `reference/hosting-and-verification.md` | Gzip serve, the tunnel 503 trap, cache-busting builds, the self-test harness, live verification loop |
| `templates/blender/*.py` | The actual generators: `common.py` helpers, character, city, vehicles, enemies, viewmodel, gun, hero render |
| `templates/godot/` | `project.godot` for a web build + `verify_pattern.gd`, a real self-test |
| `templates/serve.py`, `run.sh`, `run-public.sh` | Gzip-aware static server, local launcher, public tunnel launcher |

## The five expensive lessons it encodes

1. **Part-scoped skinning.** Distance-only auto weights tear a mesh apart when body parts are
   near each other (a hand beside a thigh stretched 17x).
2. **Pivots.** Anything the engine rotates - wheels, legs, turrets - needs its own origin,
   because Blender geometry bakes into world space.
3. **AABB vs node transform.** Merging raw mesh AABBs produces a collision box below the
   ground; the car accelerates to 27 m/s while barely moving.
4. **One unit per quantity.** A degrees pitch advanced by a radian constant made vertical aim
   57x too slow - "the crosshair won't go up".
5. **Raw mouse deltas on web.** Godot's window-relative deltas pin the camera at the screen
   edge; accumulate `movementX` in JS and drain it in `_physics_process`.

MIT licensed. See `LICENSE`.
