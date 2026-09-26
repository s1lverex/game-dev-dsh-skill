using System.IO;
using UnityEditor;
using UnityEngine;

namespace Neon.EditorTools
{
    /// <summary>Texture import rules: tiling PBR maps, correct colour space, readable for packing.</summary>
    class NeonTextureImporter : AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            string p = assetPath.Replace('\\', '/');
            if (!p.Contains("/Resources/Textures/")) return;
            var ti = (TextureImporter)assetImporter;
            ti.mipmapEnabled = true;
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.filterMode = FilterMode.Trilinear;
            ti.anisoLevel = 4;
            ti.maxTextureSize = 512;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
            ti.isReadable = true;
            ti.sRGBTexture = true;

            string n = Path.GetFileNameWithoutExtension(p).ToLowerInvariant();
            if (n.EndsWith("_normal"))
            {
                ti.textureType = TextureImporterType.NormalMap;
                ti.sRGBTexture = false;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
            }
            else if (n.EndsWith("_rough"))
            {
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = false;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
            }
        }
    }

    /// <summary>FBX import rules: metres at 1:1, generic rig, all Blender actions as clips.</summary>
    class NeonModelImporter : AssetPostprocessor
    {
        void OnPreprocessModel()
        {
            if (!assetPath.Replace('\\', '/').EndsWith(".fbx")) return;
            var mi = (ModelImporter)assetImporter;
            // Blender's FBX writer emits centimetre-scaled geometry with no compensating node
            // transform, so a bare import lands 100x too large. Lock the units at 1 unit = 1 m.
            mi.useFileScale = false;
            mi.globalScale = 0.01f;
            mi.importAnimation = true;
            mi.animationType = ModelImporterAnimationType.Generic;
            mi.importBlendShapes = false;
            mi.importCameras = false;
            mi.importLights = false;
            mi.addCollider = false;
            mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            mi.optimizeMeshPolygons = true;
            mi.optimizeMeshVertices = true;
        }
    }
}
