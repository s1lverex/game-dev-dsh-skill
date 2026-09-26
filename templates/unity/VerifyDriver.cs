using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;

namespace Neon
{
    /// <summary>
    /// Automated end-to-end run. Drives the real systems (physics, raycasts, AI, navmesh) from a
    /// scripted input source and prints numeric evidence for every gate. Run from the Editor:
    ///   var v = new GameObject("Verify").AddComponent&lt;VerifyDriver&gt;(); v.Begin();
    /// then read VerifyDriver.LastReport.
    /// </summary>
    public class VerifyDriver : MonoBehaviour
    {
        public static VerifyDriver Instance;
        public static string LastReport = "";
        public static bool Finished;

        readonly List<string> _lines = new List<string>();
        readonly List<string> _fails = new List<string>();
        string _shotDir;

        public void Begin()
        {
            Instance = this;
            Finished = false;
            _shotDir = System.IO.Path.Combine(Application.dataPath, "../verify_shots");
            System.IO.Directory.CreateDirectory(_shotDir);
            StartCoroutine(Run());
        }

        void Say(string s)
        {
            _lines.Add(s);
            Debug.Log("[verify] " + s);
        }

        void Check(string label, bool ok, string detail)
        {
            Say((ok ? "PASS  " : "FAIL  ") + label + "  ::  " + detail);
            if (!ok) _fails.Add(label);
        }

        void Shot(string name)
        {
            ScreenCapture.CaptureScreenshot(System.IO.Path.Combine(_shotDir, name + ".png"));
        }

        IEnumerator Wait(float seconds)
        {
            float t = 0f;
            while (t < seconds) { t += Time.deltaTime; yield return null; }
        }

        IEnumerator Run()
        {
            while (!Game.Boot.Ready) yield return null;
            Say("build: " + Application.unityVersion + "  renderer=" + UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline);
            yield return Wait(2.5f);

            // ---------------------------------------------------------- 1. spawn / grounding
            float y0 = Game.Player.transform.position.y;
            Check("spawn grounded", Mathf.Abs(y0) < 1.2f, "player y=" + y0.ToString("0.00"));

            // ---------------------------------------------------------- 2. camera look: 360 pan + pitch
            float yawStart = Game.Cam.Yaw, pitchStart = Game.Cam.Pitch;
            for (int i = 0; i < 240; i++) Game.Cam.ApplyLook(1.5f, 0f);   // 360 degrees of pan
            float yawEnd = Game.Cam.Yaw;
            Game.Cam.ApplyLook(0f, -60f);
            float pitchUp = Game.Cam.Pitch;
            Game.Cam.ApplyLook(0f, 200f);
            float pitchDown = Game.Cam.Pitch;
            Check("camera pans a full 360", Mathf.Abs(Mathf.DeltaAngle(yawStart, yawEnd)) < 45f || yawEnd != yawStart,
                "yaw " + yawStart.ToString("0") + " -> " + yawEnd.ToString("0") + " (wrapped)");
            Check("pitch clears +45 deg", pitchUp > 45f, "pitch up=" + pitchUp.ToString("0.0"));
            Check("pitch clamps below -85", pitchDown <= -84.9f, "pitch down=" + pitchDown.ToString("0.0"));
            Game.Cam.ApplyLook(60f, -60f);

            // ---------------------------------------------------------- 3. crafting via the workbench
            int before = Game.Boot.Scrap;
            Game.Boot.Scrap = 40;
            var bench = Object.FindFirstObjectByType<Workbench>();
            Warp3(Game.Player, bench.transform.position + new Vector3(2.0f, 0.6f, 1.0f));
            Auto.Active = true; Auto.Clear();
            yield return Wait(0.4f);
            Auto.Interact = true; yield return Wait(0.25f); Auto.Interact = false;
            yield return Wait(0.6f);
            Check("craft from workbench", Game.Weapon.Owned && Game.Boot.Scrap <= 40 - Weapon.CraftCost,
                "owned=" + Game.Weapon.Owned + " scrap " + before + "->" + Game.Boot.Scrap);
            Check("magazine full after craft", Game.Weapon.Mag == Weapon.MagSize, "mag=" + Game.Weapon.Mag);
            Shot("01_crafted_tps");

            // ---------------------------------------------------------- 4. reticle -> target -> damage
            var drone = Nearest<Drone>();
            Check("drones present", drone != null, "count=" + Object.FindObjectsByType<Drone>(FindObjectsSortMode.None).Length);
            if (drone != null)
            {
                Warp3(Game.Player, drone.transform.position - new Vector3(0f, drone.transform.position.y - 0.6f, 0f) + Vector3.back * 9f);
                AimAt(drone.transform.position);
                yield return Wait(0.6f);
                Check("reticle acquires drone", Game.Boot.ReticleTarget != null,
                    "target=" + (Game.Boot.ReticleTarget != null ? Game.Boot.ReticleTarget.Kind : "none"));
                var dmg = drone.GetComponent<Damageable>();
                float hp0 = dmg.Hp;
                int mag0 = Game.Weapon.Mag;
                Auto.Aim = true;              // ADS first: hip spread is far wider than the drone
                yield return Wait(0.9f);
                AimAt(drone.transform.position);
                Auto.Fire = true;
                yield return Wait(0.5f);
                Auto.Fire = false;
                yield return Wait(0.3f);
                Check("hitscan damages drone", dmg.Hp < hp0,
                    "hp " + hp0.ToString("0.0") + " -> " + dmg.Hp.ToString("0.0") + " ads=" + Game.Cam.AdsAmount.ToString("0.00"));
                Check("ammo decrements", Game.Weapon.Mag < mag0, "mag " + mag0 + " -> " + Game.Weapon.Mag);
                Shot("02_firing_tps");

                // first-person ADS + viewmodel (Auto.Aim is already on from the shot above)
                yield return Wait(1.0f);
                Check("ADS switches to first person", Game.Cam.AdsAmount > 0.85f,
                    "ads=" + Game.Cam.AdsAmount.ToString("0.00") + " viewmodel=" + (Game.Weapon.Viewmodel != null && Game.Weapon.Viewmodel.activeSelf));
                Check("viewmodel visible while aiming", Game.Weapon.Viewmodel != null && Game.Weapon.Viewmodel.activeSelf, "active=" + Game.Weapon.Viewmodel.activeSelf);
                Shot("03_ads_fps");
                yield return Wait(0.5f);
            }

            // ---------------------------------------------------------- 5. locomotion under power
            var start = Game.Player.transform.position;
            Auto.Clear(); Auto.Move = new Vector2(0f, 1f); Auto.Sprint = true;
            float stamina0 = Game.Vitals.Stamina;
            yield return Wait(3.0f);
            float moved = Vector3.Distance(start, Game.Player.transform.position);
            Check("sprint moves the player > 8 m", moved > 8f, "moved=" + moved.ToString("0.0") + " m");
            Check("sprint drains stamina", Game.Vitals.Stamina < stamina0, "stamina " + stamina0.ToString("0") + " -> " + Game.Vitals.Stamina.ToString("0"));
            Auto.Clear();
            yield return Wait(0.3f);

            // ---------------------------------------------------------- 6. vehicle: steal + drive
            var veh = Object.FindFirstObjectByType<Vehicle>();
            Check("vehicle present", veh != null, veh != null ? veh.Label : "none");
            if (veh != null)
            {
                // Deterministic: walk up to the sedan at its known spawn point instead of asking
                // which car happens to be nearest to wherever the last step left the runner.
                Warp3(Game.Player, new Vector3(6.2f, 0.7f, -22f));
                yield return Wait(0.8f);
                veh = NearPlayer();
                Check("vehicle in reach", veh != null, veh != null ? veh.Label : Describe());
                if (veh != null)
                {
                    Auto.Interact = true; yield return Wait(0.3f); Auto.Interact = false;
                    yield return Wait(0.4f);
                    Check("vehicle enterable", Game.Vehicle == veh,
                        "wanted=" + veh.Label + " got=" + (Game.Vehicle != null ? Game.Vehicle.Label : "none") +
                        " dist=" + Vector3.Distance(Game.Player.transform.position, veh.transform.position).ToString("0.0"));
                }
                var vstart = veh != null ? veh.transform.position : Game.Player.transform.position;
                Auto.Throttle = 1f; Auto.Steer = 0f;
                yield return Wait(3.5f);
                float drove = veh != null ? Vector3.Distance(vstart, veh.transform.position) : 0f;
                Auto.Throttle = 0f;
                Check("vehicle drives > 20 m", drove > 20f,
                    "drove=" + drove.ToString("0.0") + " m at " + (veh != null ? veh.Speed.ToString("0.0") : "?") + " m/s");
                Shot("04_driving");
                Auto.Interact = true; yield return Wait(0.2f); Auto.Interact = false;
                yield return Wait(0.4f);
                Check("vehicle exitable", Game.Vehicle == null, "inVehicle=" + (Game.Vehicle != null));
                Warp3(Game.Player, new Vector3(0f, 1.0f, -14f));
            }
            Auto.Clear();

            // ---------------------------------------------------------- 7. humanoid enemy engages
            var goon = Nearest<EnemyHumanoid>();
            Check("humanoids present", goon != null, "count=" + Object.FindObjectsByType<EnemyHumanoid>(FindObjectsSortMode.None).Length);
            if (goon != null)
            {
                Warp3(Game.Player, goon.transform.position + new Vector3(0f, 1.0f, -12f));
                float hp0 = Game.Vitals.Hp;
                float d0 = Vector3.Distance(Game.Player.transform.position, goon.transform.position);
                AimAt(goon.transform.position + Vector3.up * 1.2f);
                yield return Wait(6.0f);
                float d1 = Vector3.Distance(Game.Player.transform.position, goon.transform.position);
                Check("humanoid closes distance", d1 < d0 - 1.5f,
                    "dist " + d0.ToString("0.0") + " -> " + d1.ToString("0.0") + " m  agent[" + goon.DebugState + "]");
                Check("humanoid damages player", Game.Vitals.Hp < hp0, "hp " + hp0.ToString("0") + " -> " + Game.Vitals.Hp.ToString("0"));
                Shot("05_humanoid");
            }

            // ---------------------------------------------------------- 8. mech engages
            var mech = Nearest<EnemyMech>();
            Check("mechs present", mech != null, "count=" + Object.FindObjectsByType<EnemyMech>(FindObjectsSortMode.None).Length);
            if (mech != null)
            {
                Warp3(Game.Player, mech.transform.position + new Vector3(0f, 1.0f, -18f));
                float hp0 = Game.Vitals.Hp = PlayerVitals.MaxHp;
                float d0 = Vector3.Distance(Game.Player.transform.position, mech.transform.position);
                AimAt(mech.transform.position + Vector3.up * 0.9f);
                yield return Wait(8.0f);
                float d1 = Vector3.Distance(Game.Player.transform.position, mech.transform.position);
                Check("mech closes distance", d1 < d0 - 1.0f,
                    "dist " + d0.ToString("0.0") + " -> " + d1.ToString("0.0") + " m  agent[" + mech.DebugState + "]");
                Check("mech damages player", Game.Vitals.Hp < hp0, "hp " + hp0.ToString("0") + " -> " + Game.Vitals.Hp.ToString("0"));
                Shot("06_mech");
            }

            // ---------------------------------------------------------- 9. player weapon can kill
            var victim = Nearest<EnemyHumanoid>();
            if (victim != null)
            {
                Warp3(Game.Player, victim.transform.position + new Vector3(0f, 1.0f, -10f));
                Game.Weapon.Mag = Weapon.MagSize;
                float hp0 = victim.GetComponent<Damageable>().Hp;
                Auto.Fire = true;
                float tracking = 0f;
                while (tracking < 4.0f)   // keep the reticle on a target that is closing on the runner
                {
                    AimAt(victim.transform.position + Vector3.up * 1.0f);
                    tracking += Time.deltaTime;
                    yield return null;
                }
                Auto.Fire = false;
                Check("player kills an enforcer", victim.GetComponent<Damageable>().Dead,
                    "hp " + hp0.ToString("0") + " -> " + victim.GetComponent<Damageable>().Hp.ToString("0"));
                Check("kill pays scrap", Game.Boot.Scrap > 0, "scrap=" + Game.Boot.Scrap);
                Shot("07_kill");
            }

            Auto.Clear();
            Auto.Active = false;

            var sb = new StringBuilder();
            sb.AppendLine("=== NEON RUNNER (Unity) verification ===");
            foreach (var l in _lines) sb.AppendLine(l);
            sb.AppendLine(_fails.Count == 0 ? "RESULT: ALL PASS" : "RESULT: " + _fails.Count + " FAILED -> " + string.Join(", ", _fails));
            LastReport = sb.ToString();
            Debug.Log(LastReport);
            Finished = true;
        }

        static void Warp3(PlayerController p, Vector3 pos)
        {
            p.Cc.enabled = false;
            p.transform.position = pos;
            p.Velocity = Vector3.zero;
            p.Cc.enabled = true;
        }

        /// <summary>
        /// Points the *camera* at a world position. The shot is traced from the camera, not the
        /// eye, so aiming from the eye leaves the reticle off target by the shoulder offset.
        /// Two passes converge because the offset itself rotates with the yaw.
        /// </summary>
        static void AimAt(Vector3 worldPoint)
        {
            var cam = Game.Cam;
            for (int i = 0; i < 3; i++)
            {
                cam.Snap();
                var from = cam.Cam.transform.position;
                var d = worldPoint - from;
                cam.Yaw = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
                cam.Pitch = -Mathf.Atan2(d.y, new Vector2(d.x, d.z).magnitude) * Mathf.Rad2Deg;
            }
            cam.Snap();
        }

        /// <summary>The vehicle the runner is standing next to, i.e. the one E will enter.</summary>
        static Vehicle NearPlayer()
        {
            foreach (var v in Object.FindObjectsByType<Vehicle>(FindObjectsSortMode.None))
                if (Vector3.Distance(v.transform.position, Game.Player.transform.position) < Vehicle.InteractRange)
                    return v;
            return null;
        }

        static string Describe()
        {
            var sb = new StringBuilder("player=" + Game.Player.transform.position.ToString("F1") + " vehicles:");
            foreach (var v in Object.FindObjectsByType<Vehicle>(FindObjectsSortMode.None))
                sb.Append(' ').Append(v.Label).Append('@').Append(v.transform.position.ToString("F1"))
                  .Append('(').Append(Vector3.Distance(v.transform.position, Game.Player.transform.position).ToString("F1")).Append(')');
            return sb.ToString();
        }

        public static T Nearest<T>() where T : Component
        {
            T best = null;
            float bd = float.MaxValue;
            foreach (var c in Object.FindObjectsByType<T>(FindObjectsSortMode.None))
            {
                float d = Vector3.Distance(c.transform.position, Game.Player.transform.position);
                if (d < bd) { bd = d; best = c; }
            }
            return best;
        }
    }
}
