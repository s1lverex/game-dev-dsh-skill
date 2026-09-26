# game-dev-dsh-skill

A DeepSeek Harness **skill** that captures a complete, proven pipeline:

> procedural Blender assets -> Unity 6 **or** Godot 4 runtime -> WebGL/WASM export -> hosting ->
> live verification in the harness sidebar, fix, repeat

It is not theory. Everything here was used to build and ship a playable third-person cyberpunk
game in a browser — twice: once on Godot 4, then ported to **Unity 6.3 URP** with an upgraded
look (procedural PBR maps, HDR bloom, shadowed neon night, NavMesh AI, real `WheelCollider`
vehicles) and the same mechanics contract. Both builds have a scripted self-test that prints
numeric evidence for every system: a 200x200 m neon city, a rigged character with six keyframed
clips, a socketed pistol plus a first-person viewmodel, sedans/trucks/bikes you can steal and
drive, humanoid enforcers, quadruped mechs, an AR HUD, and live HP/stamina/ammo.

## Install

```bash
git clone https://github.com/s1lverex/game-dev-dsh-skill.git
cd game-dev-dsh-skill
./install.sh          # copies into ~/.agents/skills and ~/.claude/skills
```

The harness picks skills up from `~/.agents/skills/<name>/SKILL.md` — it appears in the catalog
as `game-dev-dsh-skill`, with no restart needed.

## Contents

| Path | What it is |
|---|---|
| `SKILL.md` | Entry point: engine choice, the stages, the non-negotiable rules, the deliverable checklist |
| `reference/blender-assets.md` | Headless asset scripting, the coordinate contract, part-scoped skinning, pivots, box-projected UVs, viewer publishing |
| `reference/unity-runtime.md` | The Unity 6 path: CLI/editor/licence install, the FBX 100x scale trap, collider transform math, code-built scenes, NavMesh, `WheelCollider`, WebGL build, and the live sidebar panel |
| `reference/godot-runtime.md` | Web-compatible project settings, code-built scenes, the physics traps, camera architecture for TPS/FPS/vehicles, the raw-mouse bridge |
| `reference/hosting-and-verification.md` | Gzip serve, the tunnel 503 trap, cache-busting builds, the self-test harness, live verification loop |
| `templates/blender/*.py` | The actual generators: `common.py` helpers, character, city, vehicles, enemies, viewmodel, gun, hero render |
| `templates/unity/` | `RuntimeBoot.cs` (boot, colliders, lighting, post, NavMesh, camera), `AssetSetup.cs` (import rules), `BuildScript.cs` (WebGL entry point), `VerifyDriver.cs` (the self-test), `unity_setup.sh`, `unity_build.sh` |
| `templates/godot/` | `project.godot` for a web build + `verify_pattern.gd`, a real self-test |
| `templates/serve.py`, `run.sh`, `run-public.sh` | Gzip-aware static server (Unity and Godot MIME types), local launcher, public tunnel launcher |

## The live sidebar panel

Paired plugin: **[dsh-plugin-unity-live](https://github.com/s1lverex/dsh-plugin-unity-live)** —
streams the Unity Editor's Game view (HUD included) and Scene view into the workbench sidebar,
next to the Live Browser and 3D Viewer panels.

```sh
dsh plugin --profile <profile> add /path/to/dsh-plugin-unity-live
# then add a `unity-live` row with `projectPath:` to the profile's cordis.patch.yml
# and restart the harness once (the browser half loads at boot)
```

This matters more than it sounds: without it the operator has to alt-tab to an Editor window to
see whether the agent's change worked, and the agent has no way to prove a visual claim.

## The expensive lessons it encodes

1. **Part-scoped skinning.** Distance-only auto weights tear a mesh apart when body parts are
   near each other (a hand beside a thigh stretched 17x).
2. **Pivots.** Anything the engine rotates — wheels, legs, turrets — needs its own origin,
   because Blender geometry bakes into world space.
3. **AABB vs node transform.** Merging raw mesh AABBs produces a collision box below the ground;
   the car accelerates to 27 m/s while barely moving. In Unity the same mistake in the other
   direction turns a ground slab into a vertical wall and the player falls forever.
4. **One unit per quantity.** A degrees pitch advanced by a radian constant made vertical aim
   57x too slow — "the crosshair won't go up".
5. **Raw mouse deltas on web.** Godot's window-relative deltas pin the camera at the screen
   edge; accumulate `movementX` in JS and drain it in `_physics_process`.
6. **Unity's licence command lies.** `unity license activate` exits 0 and activates nothing;
   only `--personal --accept-eula` works, and the Editor dies with exit code 198 otherwise.
7. **Blender FBX is 100x.** Metre-scale meshes arrive under a `scale = 100` node; fix it with
   `globalScale = 0.01f` and verify the imported bounds numerically.
8. **Do not screen-grab Wayland.** `import -window root` and `ffmpeg -f x11grab` return black on
   a Wayland session; capture from inside the engine instead.

MIT licensed. See `LICENSE`.
