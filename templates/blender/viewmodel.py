"""NEON RUNNER — first-person viewmodel: Kestrel-9 + gloved hands, authored in view space.

Unlike the world weapon (which is socketed into the animated hand bone), this asset
is modelled straight into camera space so it can be parented to the Camera3D with an
identity transform:

    Blender (x, y, z)  ->  Godot (x, z, -y)
    Blender +Y = forward (-Z in Godot), Blender +Z = up

The gun's origin sits at the rear of the slide so the sight line lands on screen
centre (Godot y = 0) and the muzzle points away from the camera.

Run:  blender --background --python tools/blender/viewmodel.py
Out:  game/assets/viewmodel.glb, assets_src/renders/viewmodel_preview.png
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SRC_GUN = os.path.join(ROOT, 'game', 'assets', 'pistol.glb')
GLB = os.path.join(ROOT, 'game', 'assets', 'viewmodel.glb')
RENDER = os.path.join(ROOT, 'assets_src', 'renders', 'viewmodel_preview.png')

# where the weapon sits in view space (Blender): forward 0.42 m, sight line 0.11 m
# below the origin so the reticle falls just above the optic
GUN_POS = Vector((0.0, 0.28, -0.105))


def build_materials():
    return dict(
        glove=C.mat('Glove', (0.045, 0.045, 0.052), 0.0, 0.72),
        glove_pad=C.mat('GlovePad', (0.085, 0.085, 0.095), 0.0, 0.55),
        skin=C.mat('Skin', (0.66, 0.47, 0.37), 0.0, 0.58),
        chrome=C.mat('Chrome', (0.86, 0.88, 0.92), 1.0, 0.11),
        dot=C.mat('SightDot', (1.0, 0.15, 0.08), 0.0, 0.2, emission=(1.0, 0.15, 0.08), emission_strength=6.0),
    )


def hand(M, side):
    """Grip geometry around the pistol's handle. side=+1 right (trigger) hand."""
    s = side
    p = []
    g = GUN_POS
    # palm behind/around the grip
    p.append(C.box('palm_%d' % s, g + Vector((0.004 * s, -0.100, -0.062)), (0.066, 0.054, 0.105),
                   M['glove'], 0.014, 2, rot_x=-16 * s))
    # four fingers wrapping the front of the grip
    for i in range(4):
        z = -0.012 - i * 0.026
        p.append(C.cyl('finger_%d_%d' % (s, i), g + Vector((-0.004 * s, -0.072 - i * 0.004, z)),
                       0.013, 0.062, M['glove'], axis='X', segments=10))
        p.append(C.box('knuckle_%d_%d' % (s, i), g + Vector((0.030 * s, -0.078 - i * 0.004, z)),
                       (0.016, 0.030, 0.026), M['glove_pad'], 0.006, 2))
    # thumb along the frame
    p.append(C.cyl('thumb_%d' % s, g + Vector((0.030 * s, -0.052, -0.045)), 0.014, 0.075,
                   M['skin'] if s < 0 else M['chrome'], axis='Y', segments=10))
    p.append(C.box('wrist_%d' % s, g + Vector((0.010 * s, -0.140, -0.092)), (0.054, 0.060, 0.072),
                   M['glove'], 0.018, 2, rot_x=-24 * s))
    return p


def main():
    C.reset_scene()
    M = build_materials()

    # import the world pistol and move it into view space (Blender coords)
    bpy.ops.import_scene.gltf(filepath=SRC_GUN)
    gun_objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in gun_objs:
        o.location = o.location + GUN_POS
        o.name = 'vm_' + o.name

    # sight dot on the optic, authored in view space too
    extra = [C.box('vm_dot', GUN_POS + Vector((0.0, 0.145, 0.106)), (0.010, 0.010, 0.006), M['dot'], 0.0, 1)]
    for s in (1, -1):
        extra += hand(M, s)

    all_objs = gun_objs + extra
    for o in all_objs:
        o.select_set(False)
    vm = C.join(all_objs, 'ViewmodelMesh')
    print('[viewmodel] verts=%d tris=%d' % (len(vm.data.vertices),
          sum(len(p.vertices) - 2 for p in vm.data.polygons)))
    C.export_glb(GLB, selection=[vm], animations=False, viewer_name='neonrunner-viewmodel.glb')
    C.report_glb(GLB)

    # preview from the camera's own point of view
    C.add_light('key', 'AREA', (0.5, 0.5, 0.7), 45, (1.0, 0.95, 0.9), size=0.5, target=(0, 0.42, 0.0))
    C.add_light('fill', 'AREA', (-0.6, 0.3, 0.1), 18, (0.5, 0.7, 1.0), size=0.6, target=(0, 0.42, 0.0))
    C.add_light('rim', 'AREA', (0.0, 0.9, 0.5), 26, (1.0, 0.4, 0.5), size=0.5, target=(0, 0.42, 0.0))
    world = bpy.data.worlds.new('W')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.02, 0.024, 0.04, 1)
    bpy.context.scene.world = world
    C.setup_render(width=1280, height=720, samples=64)
    C.add_camera('CamV', (0.0, 0.0, 0.0), (0.0, 0.5, -0.06), lens=24)
    bpy.context.scene.camera.data.sensor_fit = 'VERTICAL'
    bpy.context.scene.camera.data.sensor_height = 24.0
    C.render_to(RENDER)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'assets_src', 'viewmodel.blend'))
    print('[done] viewmodel asset')


main()
