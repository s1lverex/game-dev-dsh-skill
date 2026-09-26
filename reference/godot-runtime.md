# Godot 4 runtime for a browser 3D game

## Project settings that matter
```ini
[application]
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.7", "GL Compatibility")
[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
[display]
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"
```
`gl_compatibility` is mandatory for the Web export. `aspect="expand"` avoids letterbox bars
that silently push bottom-anchored HUD elements off screen.

## Build the world in code
Keep `main.tscn` to one node with a script and construct everything else in GDScript. Reasons:
generated `.tscn` files are fragile, unverifiable and merge badly; code is reviewable and
can be re-run by the next agent.

## Input
Bind actions in code so nothing depends on serialised `InputEventKey` blobs:
```gdscript
InputMap.add_action("fire")
var m := InputEventMouseButton.new(); m.button_index = MOUSE_BUTTON_LEFT
InputMap.action_add_event("fire", m)
```

## Physics traps that look like "the game is broken"
1. **Mesh AABB vs node transform.** `MeshInstance3D.get_aabb()` is in the node's local space.
   When nodes carry transforms (wheels, legs), merging raw AABBs produces a collision box
   that reaches below the ground: the body ends up embedded in the road and accelerates
   without moving. Merge with `inv * (node.global_transform * node.get_aabb())`.
2. **Curb step-up.** `CharacterBody3D` will not climb a 16 cm curb. `is_on_wall()` also lies
   here: a capsule meeting a sharp edge reports a ~53 deg contact (normal.y ~0.60), not a
   vertical wall. Detect obstruction with `get_slide_collision(i).get_normal().y < 0.85`,
   then verify a lift of ~0.28 m plus a short forward probe is clear before moving up.
3. **Node state is read in `_ready` before you assign it.** `add_child(node)` runs `_ready`
   immediately; setting `position` afterwards means the node cached the old value. Assign
   position/rotation *before* `add_child`.
4. **`yield`-free death loops.** Backgrounded tabs throttle; prefer explicit state machines
   over long `await` chains in gameplay code.

## Camera architecture that works for TPS + FPS + vehicles
One rig, three modes, blended by lerp:
`SpringArm3D` (pitch on the arm, yaw on the player) + `Camera3D` child.
* third person: spring ~3.5-4.0 m, lateral shoulder offset, fov 72
* first person: spring ~0.10-0.26 m at eye height, fov 82 (68 while aiming)
* vehicle: spring ~7.4 m, arm raised, fixed pitch, fov 78

For a first-person **viewmodel**, author a dedicated weapon+hands asset in *camera space* and
parent it to the `Camera3D` with an identity transform. A socketed world weapon shows nothing
useful in first person, and hiding the body while showing a bone-driven gun gives a floating
gun. Hiding *only the head* (split the head into its own mesh at export time) is the clean
middle ground when you want the arms visible.

## Web-specific input
Godot's mouse deltas are window-relative. Without pointer lock the pointer pins at the screen
edge and the camera can never pan 360. Accumulate raw deltas in JS and drain them:

```js
window.addEventListener('mousemove', e => { window.__nrLookX += (e.movementX||0); window.__nrLookY += (e.movementY||0); }, {passive:true});
```
```gdscript
var jb := Engine.get_singleton("JavaScriptBridge")   # null off-web: guard it
var raw := jb.call("eval", "(function(){var x=window.__nrLookX||0,y=window.__nrLookY||0;window.__nrLookX=0;window.__nrLookY=0;return x+','+y;})()")
```
Guard the whole bridge with `OS.has_feature("web")`: it silently activates on desktop builds
otherwise and breaks the native self-test. Note `JavaScriptBridge.create_callback` can be a
silent no-op in some builds - polling the accumulator always works.

## Units bug class
Store angles in ONE unit. A pitch stored in degrees but advanced with a radian constant
(`0.0026` instead of `0.149` per pixel) made vertical aim 57x too slow - the crosshair simply
would not go up. Assert the delta per input unit in the self-test.
