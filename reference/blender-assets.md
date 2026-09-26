# Blender asset authoring (headless)

## Why scripts, not modelling
A scripted asset is re-runnable after any parameter change, is diffable, and can be rebuilt
by the next agent without the .blend. Always run headless:

```bash
blender --background --python tools/blender/character.py
```

Put shared helpers in `common.py` and import it with
`sys.path.append(os.path.dirname(os.path.abspath(__file__)))`.

## The coordinate contract
Blender `(x, y, z)` exports to glTF/Godot `(x, z, -y)`.
So Blender **+Y is the model's forward (-Z in Godot)** and Blender **+Z is up (+Y Godot)**.
Model the character/enemy facing +Y, vehicles driving +Y, and put the origin at the feet or
at ground level. Then every placement in Godot is a plain position with no correction.

## Geometry as scripts
Build primitives with `bmesh`, not with operators, so nothing depends on editor context:
`create_cube` + `bmesh.ops.scale` + optional `bmesh.ops.bevel` for chamfered hard-surface
looks. A helper library that takes `(name, centre, size, material, bevel, segments)` covers
95% of props, characters and vehicles.

## Skinning: part-scoped weights, never pure distance
Distance-only automatic weighting **tears meshes apart** when two body parts are close:
a hand hanging beside a thigh is closer to the thigh bone than to the hand bone, and the
hand geometry stretches 17x as soon as the arm moves.

Fix: tag every part before joining (`PART_head`, `PART_hand.R`, ...), then weight each
vertex **only against the bones that part is allowed to bind to**:

```python
PART_BONES = {'hand.R': ['hand.R', 'forearm.R'], 'thigh.L': ['thigh.L', 'hips', 'shin.L'], ...}
```

Measure the result instead of trusting it: for every edge, compare posed length to rest
length across all clips. Healthy is < ~2x; 10x+ means the weights are broken.

## Rigging notes
* Build the armature in edit mode with explicit head/tail and `roll = 0`.
* Pose in **rest-frame world axes**, converting the world axis into bone space with
  `bone.matrix_local.to_3x3().inverted() @ axis`. This makes "rotate 30 deg about world X"
  exact regardless of bone roll, which is otherwise a guessing game.
* Duplicate `.L`/`.R` poses with a mirror helper that swaps suffixes and negates the
  sideways components.
* A **sighting/aim pose** is worth iterating on: it decides whether a first-person weapon
  reads correctly.

## Pivots: anything the engine rotates needs its own origin
Baked world-space geometry means a wheel/leg/turret node's pivot is the world origin, so
rotating it swings the part around the whole model. Build the part centred on its own
origin, then set `obj.location = joint_position`. Parent sub-parts (rim -> wheel,
foot -> knee -> hip) either in Blender or in Godot with `node.reparent(parent, true)`.

## Sockets and attachment
For a weapon socketed in a hand, do **not** guess an Euler offset. Measure it: at runtime
compute the desired barrel direction in the socket's local frame
(`socket.global_basis.inverse() * aim_world`) and derive the rotation that maps the model's
barrel axis onto it. Re-derive whenever the pose changes; assert `barrel.dot(aim) > 0.99`.

## Viewer publishing
The workbench viewer is a directory scan. Copy the artifact after every build:

```python
VIEWER_MODELS  = os.path.expanduser('~/.dsh/blender/models')
VIEWER_RENDERS = os.path.expanduser('~/.dsh/blender/renders')
```

Better still, call the harness `blender_export_glb` / `blender_render` tools, which publish
and register the item for the operator.

## Preview render checklist
Every asset script ends with a preview render so mistakes are visible immediately:
three-point area lights (warm key, cool fill, coloured rim), a dark world background, a
camera that frames the whole asset, Cycles CPU with denoise, ~48 samples. **Put the camera
outside the asset's bounding box** - a camera inside a building renders a black frame, which
wastes a whole cycle of "why is it black".
