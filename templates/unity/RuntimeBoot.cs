using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Neon
{
    /// <summary>
    /// Template Unity runtime: the whole game assembled in code, so no `.unity` file is
    /// hand-maintained and the build's scene list can be one empty scene.
    ///
    /// The four patterns worth copying out of this file:
    ///   1. `RuntimeInitializeOnLoadMethod` boot — works with any scene, including an empty one.
    ///   2. Collision from renderer bounds via `InverseTransformVector` (NOT size / lossyScale).
    ///   3. Scene lighting + a URP Volume built at runtime (no post-processing assets to wire).
    ///   4. An `Auto` scripted-input static, so an automated run can drive the real systems.
    /// </summary>
    public static class Game
    {
        public static Boot Boot;
        public static PlayerController Player;
        public static PlayerCamera Cam;
        public static Transform WorldRoot;
        public static MaterialLibrary Mats;
        public static readonly List<Damageable> Damageables = new List<Damageable>();
    }

    /// <summary>Scripted input used by the automated verification run. Inert in normal play.</summary>
    public static class Auto
    {
        public static bool Active;
        public static Vector2 Move;
        public static Vector2 Look;
        public static bool Sprint, Fire, Aim, Jump, Interact;
        public static float Throttle, Steer;
        public static void Clear()
        {
            Move = Look = Vector2.zero;
            Sprint = Fire = Aim = Jump = Interact = false;
            Throttle = Steer = 0f;
        }
    }

    public class Boot : MonoBehaviour
    {
        public static Boot Instance;
        public bool Ready;

        /// <summary>Any scene works: the game is created after the (empty) scene loads.</summary>
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void AutoStart()
        {
            if (Instance != null) return;
            new GameObject("GAME").AddComponent<Boot>();
        }

        void Awake()
        {
            if (Instance != null) { Destroy(gameObject); return; }
            Instance = this;
            Game.Boot = this;
            QualitySettings.shadowDistance = 55f;
            QualitySettings.shadowCascades = 2;
            QualitySettings.pixelLightCount = 8;
            Physics.gravity = new Vector3(0f, -19f, 0f);

            Game.Mats = new MaterialLibrary();
            Game.WorldRoot = new GameObject("World").transform;

            BuildWorld();
            BuildLighting();
            BuildPostProcessing();
            BuildNavigation();
            BuildPlayer();

            Ready = true;
            Debug.Log("[boot] ready");
        }

        // ------------------------------------------------------------------ world

        void BuildWorld()
        {
            var prefab = Resources.Load<GameObject>("city");   // Assets/Resources/city.fbx
            if (prefab == null) { Debug.LogError("[boot] Resources/city missing"); return; }
            var city = Instantiate(prefab, Game.WorldRoot);
            city.name = "City";
            RemapMaterials(city);
            AddColliders(city);
            StaticBatchingUtility.Combine(city);
        }

        static readonly string[] SolidPrefixes = { "ground", "road_", "walk_", "bld_", "prop_" };

        static void AddColliders(GameObject root)
        {
            int made = 0;
            foreach (var r in root.GetComponentsInChildren<Renderer>(true))
            {
                bool solid = false;
                foreach (var p in SolidPrefixes)
                    if (r.gameObject.name.StartsWith(p)) { solid = true; break; }
                if (!solid) continue;

                var b = r.bounds;
                if (b.size.x < 0.02f || b.size.y < 0.02f || b.size.z < 0.02f) continue;

                var box = r.gameObject.AddComponent<BoxCollider>();
                // The node carries a 270-degree X rotation, so the world AABB has to be taken back
                // through the node's matrix. Dividing by lossyScale permutes the extents and turns
                // a flat ground slab into a vertical wall the player falls straight through.
                box.center = r.transform.InverseTransformPoint(b.center);
                var local = r.transform.InverseTransformVector(b.size);
                box.size = new Vector3(Mathf.Abs(local.x), Mathf.Abs(local.y), Mathf.Abs(local.z));
                made++;
            }
            Debug.Log("[boot] colliders=" + made);
        }

        static void RemapMaterials(GameObject root)
        {
            foreach (var r in root.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                bool changed = false;
                for (int i = 0; i < mats.Length; i++)
                {
                    if (mats[i] == null) continue;
                    var mapped = Game.Mats.Resolve(mats[i].name, mats[i]);
                    if (mapped != null && mapped != mats[i]) { mats[i] = mapped; changed = true; }
                }
                if (changed) r.sharedMaterials = mats;
            }
        }

        /// <summary>An invisible ring just outside the map. Without it everything runs off the edge.</summary>
        void BuildBoundary()
        {
            const float half = 101f;
            var spec = new[]
            {
                (new Vector3(0f, 6f, half), new Vector3(2f * half, 24f, 2f)),
                (new Vector3(0f, 6f, -half), new Vector3(2f * half, 24f, 2f)),
                (new Vector3(half, 6f, 0f), new Vector3(2f, 24f, 2f * half)),
                (new Vector3(-half, 6f, 0f), new Vector3(2f, 24f, 2f * half)),
            };
            foreach (var (center, size) in spec)
            {
                var wall = new GameObject("wall");
                wall.transform.SetParent(Game.WorldRoot, false);
                wall.transform.position = center;
                wall.AddComponent<BoxCollider>().size = size;
            }
        }

        // ------------------------------------------------------------------ look

        void BuildLighting()
        {
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = 0.0095f;
            RenderSettings.fogColor = new Color(0.055f, 0.085f, 0.140f);
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.115f, 0.145f, 0.210f);
            RenderSettings.ambientEquatorColor = new Color(0.085f, 0.098f, 0.135f);
            RenderSettings.ambientGroundColor = new Color(0.038f, 0.042f, 0.058f);

            var moonGo = new GameObject("Moon");
            moonGo.transform.SetParent(Game.WorldRoot, false);
            moonGo.transform.rotation = Quaternion.Euler(38f, 145f, 0f);
            var moon = moonGo.AddComponent<Light>();
            moon.type = LightType.Directional;
            moon.color = new Color(0.42f, 0.52f, 0.85f);
            moon.intensity = 1.9f;
            moon.shadows = LightShadows.Soft;
        }

        void BuildPostProcessing()
        {
            var go = new GameObject("Global Volume");
            go.transform.SetParent(transform, false);
            var volume = go.AddComponent<Volume>();
            volume.isGlobal = true;
            var profile = ScriptableObject.CreateInstance<VolumeProfile>();
            volume.sharedProfile = profile;

            var bloom = profile.Add<Bloom>(true);
            bloom.intensity.overrideState = true; bloom.intensity.value = 0.85f;
            bloom.threshold.overrideState = true; bloom.threshold.value = 1.05f;
            var tone = profile.Add<Tonemapping>(true);
            tone.mode.overrideState = true; tone.mode.value = TonemappingMode.ACES;
            var grade = profile.Add<ColorAdjustments>(true);
            grade.postExposure.overrideState = true; grade.postExposure.value = 0.15f;
            grade.contrast.overrideState = true; grade.contrast.value = 14f;
            grade.saturation.overrideState = true; grade.saturation.value = 12f;
            var vig = profile.Add<Vignette>(true);
            vig.intensity.overrideState = true; vig.intensity.value = 0.30f;
        }

        void BuildNavigation()
        {
            var settings = NavMesh.GetSettingsByID(0);
            var sources = new List<NavMeshBuildSource>();
            var bounds = new Bounds(Vector3.zero, new Vector3(210f, 60f, 210f));
            NavMeshBuilder.CollectSources(bounds, ~0, NavMeshCollectGeometry.PhysicsColliders, 0,
                new List<NavMeshBuildMarkup>(), sources);
            if (sources.Count == 0) { Debug.LogError("[boot] navmesh: no sources"); return; }
            var data = NavMeshBuilder.BuildNavMeshData(settings, sources, bounds, Vector3.zero, Quaternion.identity);
            if (data == null) { Debug.LogError("[boot] navmesh build failed"); return; }
            NavMesh.AddNavMeshData(data);
            Debug.Log("[boot] navmesh sources=" + sources.Count);
        }

        void BuildPlayer()
        {
            var go = new GameObject("Player");
            go.transform.SetParent(transform, false);
            go.transform.position = new Vector3(0f, 0.4f, -14f);
            var cc = go.AddComponent<CharacterController>();
            cc.height = 1.8f; cc.radius = 0.32f; cc.center = new Vector3(0f, 0.9f, 0f);
            cc.slopeLimit = 48f; cc.stepOffset = 0.35f; cc.skinWidth = 0.03f; cc.minMoveDistance = 0f;
            Game.Player = go.AddComponent<PlayerController>();
            Game.Player.Init();

            // Blender exports +Y forward; Unity is +Z forward. One holder carries that rotation so
            // no individual asset has to know about it.
            var holder = new GameObject("Model");
            holder.transform.SetParent(go.transform, false);
            holder.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);

            var prefab = Resources.Load<GameObject>("character");
            if (prefab != null)
            {
                var model = Instantiate(prefab, holder.transform);
                RemapMaterials(model);
                var anim = model.GetComponentInChildren<Animator>();
                if (anim == null) anim = model.AddComponent<Animator>();
                anim.runtimeAnimatorController = Resources.Load<RuntimeAnimatorController>("PlayerAnimator");
                anim.applyRootMotion = false;
                anim.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                Game.Player.Anim = anim;
            }

            var camGo = new GameObject("MainCamera");
            camGo.tag = "MainCamera";
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.03f; cam.farClipPlane = 400f;
            camGo.AddComponent<AudioListener>();
            var pivot = new GameObject("CamPivot").transform;
            pivot.SetParent(go.transform, false);
            pivot.localPosition = new Vector3(0f, 1.62f, 0f);
            var rig = camGo.AddComponent<PlayerCamera>();
            rig.Pivot = pivot; rig.Cam = cam; rig.Init();
            Game.Cam = rig;
        }

        void Update()
        {
            if (!Ready || Game.Player == null || Game.Cam == null) return;
            var cam = Game.Cam.Cam;
            Game.Player.Tick(cam.transform.forward, cam.transform.right, true);
            Game.Cam.Tick(true);
        }
    }

    /// <summary>Minimal character-controller with the scripted-input hook baked in.</summary>
    public class PlayerController : MonoBehaviour
    {
        public const float WalkSpeed = 3.0f;
        public const float RunSpeed = 5.4f;
        public const float JumpSpeed = 4.6f;
        public const float Gravity = 19f;

        public CharacterController Cc;
        public Animator Anim;
        public Vector3 Velocity;
        public bool Grounded, Sprinting;
        public float SpeedXZ;

        string _anim = "idle";

        public void Init() { Cc = GetComponent<CharacterController>(); }

        public void Tick(Vector3 cameraForward, Vector3 cameraRight, bool inputEnabled)
        {
            Grounded = Cc.isGrounded;
            if (Grounded && Velocity.y < 0f) Velocity.y = -2f;

            float h = inputEnabled ? Input.GetAxisRaw("Horizontal") : 0f;
            float v = inputEnabled ? Input.GetAxisRaw("Vertical") : 0f;
            if (Auto.Active) { h = Auto.Move.x; v = Auto.Move.y; }

            var wish = cameraForward * v + cameraRight * h;
            wish.y = 0f;
            if (wish.sqrMagnitude > 1f) wish.Normalize();

            Sprinting = inputEnabled && v > 0.1f && (Input.GetKey(KeyCode.LeftShift) || (Auto.Active && Auto.Sprint));
            float target = Sprinting ? RunSpeed : WalkSpeed;
            SpeedXZ = wish.magnitude * target;

            var planar = new Vector3(Velocity.x, 0f, Velocity.z);
            planar = Vector3.MoveTowards(planar, wish * target, 14f * Time.deltaTime * target);
            Velocity.x = planar.x; Velocity.z = planar.z;

            if (Grounded && inputEnabled && (Input.GetButtonDown("Jump") || (Auto.Active && Auto.Jump)))
                Velocity.y = JumpSpeed;
            Velocity.y -= Gravity * Time.deltaTime;

            Cc.Move(Velocity * Time.deltaTime);

            if (Anim != null)
            {
                string want = SpeedXZ < 0.35f ? "idle" : (Sprinting ? "run" : "walk");
                if (want != _anim) { _anim = want; Anim.CrossFadeInFixedTime(want, 0.18f); }
            }
        }
    }

    /// <summary>Over-the-shoulder camera that blends into aim-down-sights first person.</summary>
    public class PlayerCamera : MonoBehaviour
    {
        public Transform Pivot;
        public Camera Cam;
        public float Yaw, Pitch;
        public bool Aiming;
        public float AdsAmount { get; private set; }

        public void Init()
        {
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;
            Cam.clearFlags = CameraClearFlags.SolidColor;
            Cam.backgroundColor = new Color(0.02f, 0.03f, 0.055f);
        }

        /// <summary>Public so the automated run can sweep the view (and prove a full 360 pan).</summary>
        public void ApplyLook(float dYaw, float dPitch)
        {
            Yaw += dYaw;
            Pitch = Mathf.Clamp(Pitch - dPitch, -85f, 85f);
        }

        /// <summary>Place the rig at its ideal pose immediately; used by the automated run.</summary>
        public void Snap() { Tick(false); }

        public void Tick(bool inputEnabled)
        {
            if (inputEnabled)
            {
                ApplyLook(Input.GetAxisRaw("Mouse X") * 0.16f, Input.GetAxisRaw("Mouse Y") * 0.16f);
                ApplyLook(Auto.Look.x, Auto.Look.y);
                Auto.Look = Vector2.zero;
            }

            AdsAmount = Mathf.MoveTowards(AdsAmount, Aiming ? 1f : 0f, 6.5f * Time.deltaTime);
            float dist = Mathf.Lerp(4.3f, 0.02f, AdsAmount);
            float side = Mathf.Lerp(0.80f, 0f, AdsAmount);

            Pivot.rotation = Quaternion.Euler(Pitch, Yaw, 0f);
            var desired = Pivot.position + Pivot.rotation * new Vector3(side, 0.16f, -dist);
            transform.position = Vector3.Lerp(transform.position, desired, 18f * Time.deltaTime);
            transform.rotation = Pivot.rotation;
            Cam.fieldOfView = Mathf.Lerp(Cam.fieldOfView, Mathf.Lerp(62f, 52f, AdsAmount), 8f * Time.deltaTime);
        }
    }

    public class Damageable : MonoBehaviour
    {
        public float Hp = 60f;
        public System.Action<Damageable> OnDeath;
        public bool Dead => Hp <= 0f;

        public void Setup(float hp) { Hp = hp; Game.Damageables.Add(this); }

        public bool Damage(float amount)
        {
            if (Dead) return false;
            Hp -= amount;
            if (Hp <= 0f) { Hp = 0f; OnDeath?.Invoke(this); }
            return true;
        }
    }

    /// <summary>
    /// URP/Lit materials built from procedural PBR maps in Resources/Textures. Blender albedos are
    /// authored for an emissive-heavy look and are near-black; multiplying one by an already-dark
    /// albedo map renders nothing, so textured families keep the hue at a usable brightness.
    /// </summary>
    public class MaterialLibrary
    {
        readonly Dictionary<string, Material> _cache = new Dictionary<string, Material>();

        public Material Resolve(string rawName, Material src)
        {
            string key = rawName ?? "";
            int colon = key.LastIndexOf(':');
            if (colon >= 0) key = key.Substring(colon + 1);
            key = key.Replace(" (Instance)", "").Trim();

            Color baseCol = src != null && src.HasProperty("_Color") ? src.GetColor("_Color") : Color.white;
            float metallic = src != null && src.HasProperty("_Metallic") ? src.GetFloat("_Metallic") : 0.2f;
            float smooth = src != null && src.HasProperty("_Glossiness") ? src.GetFloat("_Glossiness") : 0.4f;

            string family = key.ToLowerInvariant().Contains("neon") ? "neon" : "concrete";
            string ck = key + "|" + family;
            if (_cache.TryGetValue(ck, out var hit) && hit != null) return hit;

            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = key };
            float peak = Mathf.Max(baseCol.r, Mathf.Max(baseCol.g, baseCol.b));
            m.SetColor("_BaseColor", peak < 0.004f ? Color.white
                : new Color(baseCol.r / peak * 0.92f, baseCol.g / peak * 0.92f, baseCol.b / peak * 0.92f, 1f));
            m.SetFloat("_Metallic", metallic);
            m.SetFloat("_Smoothness", smooth);
            _cache[ck] = m;
            return m;
        }
    }
}
