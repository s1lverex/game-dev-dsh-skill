using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace Neon.EditorTools
{
    /// <summary>
    /// One-shot project setup + the WebGL build entry point used by the Unity CLI:
    ///   unity build &lt;project&gt; --target WebGL --execute-method Neon.EditorTools.BuildScript.WebGL
    /// Everything the game needs at runtime is generated here: the scene, the animator
    /// controllers built from the Blender FBX actions, and the always-included shader list.
    /// </summary>
    public static class BuildScript
    {
        const string ScenePath = "Assets/Scenes/Main.unity";

        [MenuItem("Neon/1. Setup Project")]
        public static void Setup()
        {
            ConfigurePlayer();
            EnsureScene();
            EnsureAnimatorControllers();
            EnsureAlwaysIncludedShaders();
            ConfigureUrp();
            AssetDatabase.SaveAssets();
            Debug.Log("[build] setup complete");
        }

        [MenuItem("Neon/2. Verify (play mode report)")]
        public static void VerifyHint()
        {
            Debug.Log("[build] run the game then eval: " +
                      "var v = new GameObject(\"Verify\").AddComponent<Neon.VerifyDriver>(); v.Begin(); " +
                      "// poll Neon.VerifyDriver.LastReport");
        }

        // ------------------------------------------------------------------ project settings

        static void ConfigurePlayer()
        {
            PlayerSettings.companyName = "Silverex";
            PlayerSettings.productName = "NEON RUNNER";
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.runInBackground = true;
            PlayerSettings.defaultScreenWidth = 1600;
            PlayerSettings.defaultScreenHeight = 900;
            PlayerSettings.SetScriptingBackend(BuildTargetGroup.WebGL, ScriptingImplementation.IL2CPP);
            PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.WebGL, ManagedStrippingLevel.Medium);
            PlayerSettings.stripEngineCode = true;
            PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled; // serve.py gzips
            PlayerSettings.WebGL.dataCaching = true;
            PlayerSettings.WebGL.decompressionFallback = true;
            PlayerSettings.WebGL.template = "APPLICATION:Default";
            PlayerSettings.WebGL.emscriptenArgs = "-s ALLOW_MEMORY_GROWTH=1";
            PlayerSettings.graphicsJobs = false;
        }

        static void EnsureScene()
        {
            if (File.Exists(ScenePath)) return;
            Directory.CreateDirectory("Assets/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.Refresh();
            Debug.Log("[build] created " + ScenePath);
        }

        // ------------------------------------------------------------------ animators

        static void EnsureAnimatorControllers()
        {
            MakeController("Assets/Resources/character.fbx", "Assets/Resources/PlayerAnimator.controller",
                new[] { "idle", "walk", "run", "aim", "fire", "reload" });
            MakeController("Assets/Resources/enemy_goon.fbx", "Assets/Resources/GoonAnimator.controller",
                new[] { "idle", "walk", "run", "aim", "fire", "reload" });
        }

        static void MakeController(string fbx, string outPath, string[] wanted)
        {
            if (!File.Exists(fbx))
            {
                Debug.LogWarning("[build] missing model " + fbx);
                return;
            }
            var clips = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<AnimationClip>()
                .Where(c => !c.name.StartsWith("__preview")).ToList();
            if (clips.Count == 0)
            {
                Debug.LogWarning("[build] no clips in " + fbx);
                return;
            }

            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(outPath);
            if (controller == null)
                controller = AnimatorController.CreateAnimatorControllerAtPath(outPath);
            var sm = controller.layers[0].stateMachine;

            foreach (var want in wanted)
            {
                var clip = clips.FirstOrDefault(c => c.name.ToLowerInvariant().Contains(want));
                if (clip == null) { Debug.LogWarning("[build] clip '" + want + "' missing in " + fbx); continue; }
                AnimatorState state = null;
                foreach (var cs in sm.states)
                    if (cs.state.name == want) { state = cs.state; break; }
                if (state == null) state = sm.AddState(want);
                state.motion = clip;
                state.speed = 1f;
            }
            if (sm.defaultState == null || sm.states.Length > 0)
                sm.defaultState = sm.states.First(s => s.state.name == "idle").state;

            EditorUtility.SetDirty(controller);
            AssetDatabase.SaveAssets();
            Debug.Log("[build] " + outPath + " states=" + string.Join(",", sm.states.Select(s => s.state.name)) +
                      " clips=" + string.Join(",", clips.Select(c => c.name)));
        }

        // ------------------------------------------------------------------ render config

        static void EnsureAlwaysIncludedShaders()
        {
            var names = new[] { "Universal Render Pipeline/Lit", "Universal Render Pipeline/Unlit", "Skybox/Procedural", "Sprites/Default" };
            var gs = GraphicsSettings.GetGraphicsSettings();
            var so = new SerializedObject(gs);
            var list = so.FindProperty("m_AlwaysIncludedShaders");
            var have = new HashSet<Object>();
            for (int i = 0; i < list.arraySize; i++) have.Add(list.GetArrayElementAtIndex(i).objectReferenceValue);

            foreach (var n in names)
            {
                var sh = Shader.Find(n);
                if (sh == null) { Debug.LogWarning("[build] shader not found: " + n); continue; }
                if (have.Contains(sh)) continue;
                list.InsertArrayElementAtIndex(list.arraySize);
                list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = sh;
            }
            so.ApplyModifiedProperties();
            AssetDatabase.SaveAssets();
        }

        static void ConfigureUrp()
        {
            var rp = GraphicsSettings.defaultRenderPipeline as UniversalRenderPipelineAsset;
            if (rp == null) { Debug.LogWarning("[build] no URP asset assigned"); return; }
            rp.msaaSampleCount = 2;
            rp.supportsHDR = true;
            rp.shadowDistance = 55f;
            rp.shadowCascadeCount = 2;
            rp.renderScale = 1f;
            rp.supportsCameraDepthTexture = true;
            rp.supportsCameraOpaqueTexture = false;
            EditorUtility.SetDirty(rp);

            var renderer = rp.rendererDataList != null && rp.rendererDataList.Length > 0 ? rp.rendererDataList[0] : null;
            if (renderer is UniversalRendererData urd)
            {
                urd.renderingMode = RenderingMode.Forward;
                EditorUtility.SetDirty(urd);
            }
            Debug.Log("[build] URP configured: msaa=" + rp.msaaSampleCount + " hdr=" + rp.supportsHDR + " shadows=" + rp.shadowDistance);
        }

        // ------------------------------------------------------------------ build

        public static void WebGL()
        {
            Setup();
            string outDir = ArgValue("-buildOutput") ?? Path.GetFullPath("Build/WebGL");
            Directory.CreateDirectory(outDir);
            var options = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = outDir,
                target = BuildTarget.WebGL,
                targetGroup = BuildTargetGroup.WebGL,
                options = BuildOptions.None,
            };
            var report = BuildPipeline.BuildPlayer(options);
            var summary = report.summary;
            Debug.Log("[build] result=" + summary.result + " size=" + summary.totalSize +
                      " errors=" + summary.totalErrors + " time=" + summary.totalTime);
            if (summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded)
                EditorApplication.Exit(1);
        }

        static string ArgValue(string key)
        {
            var args = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
                if (args[i] == key) return args[i + 1];
            return null;
        }
    }
}
