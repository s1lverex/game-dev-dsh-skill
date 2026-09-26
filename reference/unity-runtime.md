# Unity runtime path (Blender → Unity → WebGL → browser)

The Unity half of this skill. Everything here was learned the hard way building a real
Unity 6.3 WebGL port of a working Godot vertical slice; the "trap" entries are the failures
that cost the most time.

The Unity tool surface comes from the **`@opdsh/unity-plugin`** DSH plugin
(`unity_status`, `unity_list_commands`, `unity_command`, `unity_eval`, `unity_cli`) plus Unity's
official `unity` CLI. If those tools are present, use them — do **not** hand-edit `.unity`,
`.prefab` or `.asset` YAML while an Editor is reachable.

---

## 1. Toolchain install (once per machine)

```bash
# The CLI. On Linux/macOS:
curl -fsSL https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.sh | UNITY_CLI_CHANNEL=beta bash
unity --version

# Sign in (prints a URL you can hand to the operator; it polls until they finish)
unity auth login
unity auth status --format json          # loggedIn: true

# A licence is NOT optional and the obvious command is a silent no-op:
unity license activate                     # <-- activates NOTHING, exits 0
unity license activate --personal --accept-eula   # <-- this is the one that works
unity license status --format json         # active: true, products: ["Unity Personal", ...]
```

**Trap — `unity license activate` with no flags succeeds and activates nothing.** The Editor
then dies on start with exit code 198 and
`Access token is unavailable` / `Found 0 entitlement groups ... matching requested entitlement ids`
in its log. If you see that, run the `--personal --accept-eula` form and re-check
`"active": true` before blaming anything else.

Install the Editor **with the WebGL module** (the download is multi-GB; run it detached with a
log and poll):

```bash
nohup unity install lts --module webgl --yes --accept-eula --no-banner > /tmp/unity-install.log 2>&1 &
tail -f /tmp/unity-install.log        # {"type":"progress","pct":..,"phase":"download"}
unity editors --installed --format json
```

**Trap — the progress percentage is not proportional to time.** It sat at 4 % for minutes and
then jumped; budget 45–90 minutes and work on assets while it runs.

## 2. Create the project

```bash
unity templates list --editor lts --format json      # never guess a template id
unity projects create "MyGame" --path "$PWD" \
  --editor-version 6000.3.25f1 --template com.unity.template.urp-blank --non-interactive
unity pipeline install --project-path "$PWD/MyGame"  # live-control commands
nohup unity open "$PWD/MyGame" --args "-automated" > /tmp/unity-open.log 2>&1 &
```

`com.unity.template.urp-blank` is "Universal 3D" — URP is the only realistic choice for a
browser build (HDRP does not run on WebGL, Built-in has no post stack).

Then poll `unity_status` until `"state": "ready"`. The first open imports for several minutes.

**Always launch with `-automated`** so no interactive dialog can block the agent.

## 3. Project settings you must fix before writing gameplay code

| Setting | Why | How |
|---|---|---|
| **Active Input Handling** | The URP template ships `activeInputHandler: 1` (Input System only). Every legacy `Input.GetAxis` then throws, and the game boots to a dead controller. Set `activeInputHandler: 2` (Both) in `ProjectSettings/ProjectSettings.asset` **while no Editor is running**. | file edit, no Editor |
| **Colour space** | Linear, or every material reads washed out | `PlayerSettings.colorSpace = ColorSpace.Linear` |
| **Always Included Shaders** | A shader referenced only by `Shader.Find` at runtime is stripped from the build and the object renders magenta/nothing | add `URP/Lit`, `URP/Unlit`, `Skybox/Procedural`, `Sprites/Default` to `GraphicsSettings.m_AlwaysIncludedShaders` via a `SerializedObject` |
| **URP asset** | WebGL needs a small budget | `msaaSampleCount = 2`, `shadowDistance ~55`, `shadowCascadeCount = 2`, Forward renderer |
| **WebGL player** | Let your own server gzip | `WebGLCompressionFormat.Disabled`, `dataCaching = true`, `decompressionFallback = true` |

## 4. Asset import (the two traps that break everything)

Export **FBX** from Blender, not glTF: Unity's native `ModelImporter` reads FBX, so the build
needs no glTF package, and material *names* survive for runtime remapping.

```csharp
// Assets/Editor/AssetSetup.cs
void OnPreprocessModel() {
  var mi = (ModelImporter)assetImporter;
  mi.useFileScale = false;
  mi.globalScale = 0.01f;          // see trap 1
  mi.animationType = ModelImporterAnimationType.Generic;
  mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
  mi.addCollider = false;
}
```

**Trap 1 — everything imports 100× too large.** Blender's FBX writer emits metre-scale meshes
under a node with `scale = 100`, so a 1.95 m character arrives 195 m tall and a 200 m block
arrives 20 km wide. `useFileScale = false` alone does **not** fix it; `globalScale = 0.01f`
does. Verify numerically rather than by eye:

```csharp
// unity_eval
var go = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Resources/city.fbx");
var rs = go.GetComponentsInChildren<Renderer>();
var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
return b.size.ToString("F2");   // expect (200.00, 51.03, 200.00)
```

**Trap 2 — an `AssetPostprocessor` only takes effect after the Editor recompiles.** Reimport
assets, see the old result, and conclude the setting is ignored. Force a recompile and reimport:

```csharp
AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
CompilationPipeline.RequestScriptCompilation();          // wait for recompile_status
AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
```

Also: `Resources.Load<GameObject>("name")` is the cheapest wiring for a code-built scene — put
the FBX under `Assets/Resources/` and you never touch a serialized reference.

## 5. Collision, built from mesh bounds

Blender bakes geometry into world space, so a collider must be derived from the renderer's
bounds — and it must be expressed **in the node's own space**:

```csharp
var box = r.gameObject.AddComponent<BoxCollider>();
box.center = r.transform.InverseTransformPoint(b.center);
var local = r.transform.InverseTransformVector(b.size);      // NOT b.size / lossyScale
box.size = new Vector3(Mathf.Abs(local.x), Mathf.Abs(local.y), Mathf.Abs(local.z));
```

**Trap 3 — dividing by `lossyScale` ignores the node's rotation.** Blender nodes carry a
270°-about-X rotation; dividing the world AABB by scale permutes Y and Z, so a flat 200 × 1 × 200
ground slab became a *vertical wall* 200 × 200 × 1. The player then spawns, finds no floor, and
falls forever (camera at `y = -1124`, nothing but fog on screen). Use
`InverseTransformVector` and take the absolute value.

## 6. Build the scene in code, not in the `.unity` file

Hand-authored scenes are the Unity equivalent of hand-written `.tscn` files: fragile, and
invisible to a diff. Instead:

```csharp
public class Boot : MonoBehaviour {
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void AutoStart() { new GameObject("GAME").AddComponent<Boot>(); }
  void Awake() { /* materials, world, camera, HUD, spawns */ }
}
```

Now *any* scene works, the build's scene list can be one empty scene, and an editor script can
create it:

```csharp
var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
EditorSceneManager.SaveScene(scene, "Assets/Scenes/Main.unity");
```

## 7. Animation from Blender actions

Blender's `bake_anim_use_all_actions=True` puts every action in the FBX; Unity exposes them as
`AnimationClip`s (ignore the `__preview__` duplicates). Generate the controller in an editor
script and drive it **by state name**, with no parameters and no transitions:

```csharp
AnimatorController.CreateAnimatorControllerAtPath("Assets/Resources/PlayerAnimator.controller");
sm.AddState("run").motion = clips.First(c => c.name.ToLowerInvariant().Contains("run"));
// runtime:
anim.CrossFadeInFixedTime("run", 0.18f);
```

`sm.states` is a `ChildAnimatorState[]` (structs) — `FirstOrDefault(...)?.state` does not compile.

## 8. Physics and the Unity 6 API renames

Several things you will reach for first are gone or renamed in Unity 6:

| Old | Unity 6.3 |
|---|---|
| `Rigidbody.drag` | `Rigidbody.linearDamping` |
| `Rigidbody.angularDrag` | `Rigidbody.angularDamping` |
| `Rigidbody.velocity` | `Rigidbody.linearVelocity` |
| `WheelCollider.width` | *removed* — do not set it |

**Trap 4 — wheels sized from `lossyScale` launch every car into orbit.** With the Blender node
scale of 100, `wheel.lossyScale.y * 0.5` produced 34-metre wheels; cars reached 200 m/s and
ended up 8 km away and 4 km up. Take the radius from world bounds and clamp it:

```csharp
float radius = Mathf.Clamp(wheelRenderer.bounds.extents.y, 0.16f, 0.6f);
```

Also give the drivetrain a **governor** — `motorTorque * Mathf.Clamp01(1f - speed / topSpeed)` —
or a wheel that never runs out of torque accelerates without limit.

**Trap 5 — NavMesh agents spawned inside building footprints never move.** They fire at the
player (so the AI *looks* alive) but the distance never changes. Spawn everything on open
roadway and expose the agent's own state so a failure is legible:

```csharp
public string DebugState => _agent.isOnNavMesh ? "onNav vel=" + _agent.velocity.magnitude : "offNav";
```

**Trap 6 — the boundary ring is not optional.** A 200 m island with nothing around it lets the
player, enemies *and* cars simply run off the edge and fall forever, poisoning every later test.
Add four invisible box colliders just outside the map before spawning anything.

## 9. Verification with `unity_eval` (no test framework needed)

A `VerifyDriver` MonoBehaviour that drives the real systems from a scripted input source, prints
`PASS/FAIL` lines with numbers, and parks the whole report in a static, is far more useful than
PlayMode tests here — and the agent can read it back in one call:

```csharp
// unity_eval: start it
new GameObject("Verify").AddComponent<Neon.VerifyDriver>().Begin();
// unity_eval: read it back later
return Neon.VerifyDriver.LastReport;
```

Rules that made it trustworthy:

* Drive real code paths (`CharacterController.Move`, the weapon's raycast, `WheelCollider`
  torque) from a tiny `Auto` static — never from a parallel "test mode" implementation.
* `Input` cannot be simulated with the legacy input manager, so the player, weapon, camera and
  vehicle each read `Auto` first and fall back to `Input`. Inert in a normal build.
* Aim from the **camera**, not the eye: the shot is traced from the camera through the reticle,
  so aiming from the character's head leaves the reticle off target by the whole shoulder offset.
  Iterate (apply look, snap the rig, re-read the camera position) until it converges.
* Hip spread is real: a 0.6 m drone at 9 m is a coin flip at 5.5°. Aim down sights in the test
  before asserting a hit.
* Give the camera a `Snap()` that assigns the ideal pose immediately, or every scripted aim
  lags behind the smoothing.

Real numbers from the port, for calibration: sprint 15.9 m at 5.2 m/s, car 47 m at 13.5 m/s,
humanoid closes 12.0 → 7.8 m, drone hp 3 → 0 on one aimed shot, mag 12 → 7 over a burst.

## 10. WebGL build and hosting

```csharp
// Assets/Editor/BuildScript.cs — the entry point the CLI calls
public static void WebGL() {
  Setup();
  BuildPipeline.BuildPlayer(new BuildPlayerOptions {
    scenes = new[] { "Assets/Scenes/Main.unity" },
    locationPathName = outDir, target = BuildTarget.WebGL, targetGroup = BuildTargetGroup.WebGL,
  });
}
```

```bash
unity build "$PROJECT" --target WebGL \
  --execute-method Neon.EditorTools.BuildScript.WebGL --allow-install --non-interactive --format json
```

Build into a staging directory, gzip the payload, then swap — never rebuild into the directory a
live server is reading. Serve with `templates/serve.py`, which already maps `.wasm`
(`application/wasm`), `.data`, `.mem` and `.unityweb` and serves `.gz` siblings.

Note the shape of a Unity WebGL build: `index.html`, `Build/<name>.loader.js`,
`Build/<name>.framework.js`, `Build/<name>.wasm`, `Build/<name>.data`.

## 11. Watching the Editor live (the sidebar panel)

Install the **`dsh-plugin-unity-live`** plugin to get the Editor's views in the workbench
sidebar, next to the Live Browser and 3D Viewer panels:

```sh
dsh plugin --profile <profile> add /path/to/dsh-plugin-unity-live
```

```yaml
# <profile>/cordis.patch.yml
- insert:
    - id: unity-live
      name: 'dsh-plugin-unity-live'
      config:
        projectPath: '/abs/path/to/YourUnityProject'
        intervalMs: 350
```

**Restart the harness once.** The host half reloads live, but the browser half is registered by
the client-module scan, which only runs at boot.

Under the hood it drives the Pipeline capture commands through one long-lived
`unity shell --protocol ndjson` process (a fresh `unity command` per frame costs ~600 ms and caps
the panel at ~1 fps), and mirrors each frame into `~/.dsh/blender/renders/unity_live_<view>.png`
so the 3D viewer panel shows the same stream.

| View | Command | Content |
|---|---|---|
| game | `capture_game_view --source screen` | the composited Game view **including Screen Space - Overlay UI (the HUD)** |
| game (fallback) | `capture_game_view --source camera` | renders a camera; used when no Game view render target exists yet (an Editor that has never entered play mode) |
| scene | `capture_scene_view` | the Scene view with grid and gizmos |

`unity command screenshot --view game` is **not** the same thing: it misses overlay canvases, so
a HUD never appears in it. Use `capture_game_view`.

**Trap 7 — do not try to screen-grab the desktop.** On a Wayland session both
`import -window root` and `ffmpeg -f x11grab` return a black frame with only the cursor drawn:
XWayland surfaces are never composited into the X root. Capture from inside the Editor instead —
it is faster, works headless, and is the only thing that shows the HUD.

Without the plugin, the same stream is one command away:

```bash
unity command capture_game_view --save_path Screenshots/live.png --source screen \
  --width 1280 --height 720 --format json
cp "$PROJECT/Assets/Screenshots/live.png" ~/.dsh/blender/renders/unity_live_game.png
```

## 12. War stories worth remembering

* **Materials read black.** Blender albedos authored for an emissive-heavy Godot look are
  near-black (asphalt `0.021`); multiplying them by an already-dark albedo *texture* renders
  nothing. For textured families keep the hue but normalise the peak brightness —
  `tint = colour / max(r,g,b) * 0.92` — and raise the ambient/moon instead of fighting it.
* **Skybox `Shader.Find` at runtime is stripped from the build.** Add it to Always Included
  Shaders or ship a solid-colour camera background.
* **A `.meta`-less texture drops the material's maps silently.** Everything under
  `Assets/Resources/Textures/` needs an `AssetPostprocessor` that sets `NormalMap` for
  `*_normal`, `sRGBTexture = false` for roughness, and `isReadable` when you pack
  metallic-smoothness at runtime.
* **Editing scripts while in play mode does not recompile them.** `editor_status` keeps
  reporting `playing` while your changes are ignored. Stop play mode, recompile, start again.
