"""NEON RUNNER — craftable sidearm ("Kestrel-9", original design).

Built in the pistol's natural world orientation: grip down (-Z), barrel forward (+Y),
hold point at the origin so the Godot BoneAttachment3D offset stays simple.
Run:  blender --background --python tools/blender/gun.py
Out:  game/assets/pistol.glb, assets_src/pistol.blend, assets_src/renders/pistol_hero.png
"""
import os
import sys

import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
GLB = os.path.join(ROOT, 'game', 'assets', 'pistol.glb')
BLEND = os.path.join(ROOT, 'assets_src', 'pistol.blend')
RENDER = os.path.join(ROOT, 'assets_src', 'renders', 'pistol_hero.png')


def build():
    M = dict(
        steel=C.mat('GunSteel', (0.13, 0.135, 0.15), 1.0, 0.32),
        dark=C.mat('GunDark', (0.055, 0.058, 0.065), 1.0, 0.5),
        grip=C.mat('GunGrip', (0.05, 0.05, 0.055), 0.0, 0.72),
        accent=C.mat('GunAccent', (0.68, 0.07, 0.06), 0.3, 0.3),
        dot=C.mat('GunDot', (1.0, 0.15, 0.05), 0.0, 0.2, emission=(1.0, 0.18, 0.05), emission_strength=4.0),
    )
    p = []
    # slide (top), barrel, muzzle
    p.append(C.box('slide', (0, 0.035, 0.075), (0.042, 0.245, 0.048), M['steel'], 0.008, 2))
    for i in range(4):
        p.append(C.box('serration_%d' % i, (0, -0.062 + i * 0.012, 0.075), (0.045, 0.005, 0.044), M['dark'], 0.001, 1))
    p.append(C.cyl('barrel', (0, 0.115, 0.062), 0.0135, 0.10, M['dark'], axis='Y', segments=14))
    p.append(C.cyl('muzzle_ring', (0, 0.163, 0.062), 0.018, 0.014, M['steel'], axis='Y', segments=14))
    # frame, trigger guard, trigger
    p.append(C.box('frame', (0, 0.01, 0.028), (0.038, 0.20, 0.036), M['steel'], 0.006, 2))
    p.append(C.box('guard_bottom', (0, 0.012, -0.038), (0.03, 0.09, 0.012), M['steel'], 0.004, 2))
    p.append(C.box('guard_front', (0, 0.056, -0.012), (0.03, 0.012, 0.05), M['steel'], 0.004, 2))
    p.append(C.box('trigger', (0, 0.022, -0.012), (0.014, 0.012, 0.036), M['dark'], 0.003, 2))
    # grip + magazine
    p.append(C.box('grip', (0, -0.055, -0.075), (0.04, 0.075, 0.14), M['grip'], 0.016, 2, rot_x=-16))
    p.append(C.box('grip_plate', (0, -0.068, -0.142), (0.044, 0.082, 0.014), M['accent'], 0.005, 2, rot_x=-16))
    p.append(C.box('mag_release', (0.021, -0.02, -0.03), (0.008, 0.03, 0.02), M['dark'], 0.002, 1))
    # accents + sights
    p.append(C.box('accent_panel_L', (0.0225, 0.02, 0.075), (0.004, 0.11, 0.03), M['accent'], 0.002, 1))
    p.append(C.box('accent_panel_R', (-0.0225, 0.02, 0.075), (0.004, 0.11, 0.03), M['accent'], 0.002, 1))
    p.append(C.box('sight_rear', (0, -0.075, 0.104), (0.03, 0.012, 0.014), M['dark'], 0.003, 2))
    p.append(C.box('sight_front', (0, 0.135, 0.104), (0.012, 0.012, 0.014), M['dark'], 0.003, 2))
    p.append(C.box('dot_rear_L', (0.011, -0.075, 0.112), (0.005, 0.005, 0.003), M['dot'], 0.0, 1))
    p.append(C.box('dot_rear_R', (-0.011, -0.075, 0.112), (0.005, 0.005, 0.003), M['dot'], 0.0, 1))
    p.append(C.box('dot_front', (0, 0.135, 0.112), (0.005, 0.005, 0.003), M['dot'], 0.0, 1))
    # slide stop + takedown lever
    p.append(C.cyl('slide_stop', (0.021, -0.01, 0.045), 0.008, 0.01, M['dark'], axis='X', segments=10))
    p.append(C.cyl('takedown', (-0.021, 0.03, 0.045), 0.008, 0.01, M['dark'], axis='X', segments=10))
    body = C.join(p, 'PistolMesh')
    C.empty('muzzle', (0, 0.175, 0.062), size=0.03)
    return body


def main():
    C.reset_scene()
    body = build()
    print('[mesh] verts=%d tris=%d' % (len(body.data.vertices),
                                       sum(len(p.vertices) - 2 for p in body.data.polygons)))
    C.export_glb(GLB, selection=None, animations=False, viewer_name='neonrunner-pistol.glb')
    C.report_glb(GLB)

    C.add_light('key', 'AREA', (0.42, 0.5, 0.6), 55, (1.0, 0.96, 0.92), size=0.8, target=(0, 0.03, 0.03))
    C.add_light('fill', 'AREA', (-0.5, 0.3, 0.3), 18, (0.5, 0.7, 1.0), size=0.8, target=(0, 0.03, 0.03))
    C.add_light('rim', 'AREA', (0.0, -0.55, 0.4), 30, (1.0, 0.3, 0.4), size=0.6, target=(0, 0.0, 0.03))
    world = bpy.data.worlds.new('W')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.01, 0.012, 0.02, 1)
    bpy.context.scene.world = world
    C.add_camera('Cam', (0.52, -0.62, 0.34), (0, 0.035, -0.01), lens=50)
    C.setup_render(width=900, height=700, samples=64)
    C.render_to(RENDER)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print('[done] pistol asset')


main()
