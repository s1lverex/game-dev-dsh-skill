"""NEON RUNNER — enemies.

  * `goon`  : humanoid enforcer. Reuses the player's armature layout and animation
              clips (imported from character.py) so it walks, aims and fires with no
              extra rigging work.
  * `mech`  : non-humanoid quadruped. No skeleton — every leg segment is its own
              named node (leg_<i>_hip / _knee / _foot) so the game can drive a
              procedural walk cycle.

Run:  blender --background --python tools/blender/enemies.py
Out:  game/assets/enemy_goon.glb, enemy_mech.glb
"""
import math
import os
import sys

import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import character as CH  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ASSETS = os.path.join(ROOT, 'game', 'assets')
RENDERS = os.path.join(ROOT, 'assets_src', 'renders')


# ------------------------------------------------------------------ humanoid

def goon_materials():
    return dict(
        armour=C.mat('GoonArmour', (0.055, 0.06, 0.075), 0.55, 0.42),
        plate=C.mat('GoonPlate', (0.16, 0.17, 0.20), 0.8, 0.34),
        cloth=C.mat('GoonCloth', (0.09, 0.07, 0.08), 0.0, 0.8),
        skin=C.mat('GoonSkin', (0.55, 0.40, 0.33), 0.0, 0.6),
        visor=C.mat('GoonVisor', (1.0, 0.12, 0.10), 0.0, 0.15, emission=(1.0, 0.12, 0.10), emission_strength=2.6),
        trim=C.mat('GoonTrim', (0.9, 0.15, 0.12), 0.3, 0.35),
        boot=C.mat('GoonBoot', (0.045, 0.045, 0.05), 0.0, 0.6),
    )


def goon_body(M):
    """Bulkier silhouette on the exact player bone layout (same part tags)."""
    p = []

    def add(tag, ob):
        p.append((tag, ob))

    add('head', C.box('helmet', (0, 0.004, 1.72), (0.24, 0.26, 0.24), M['armour'], 0.05, 3))
    add('head', C.box('visor', (0, 0.115, 1.735), (0.19, 0.06, 0.075), M['visor'], 0.02, 2))
    add('head', C.box('jaw_guard', (0, 0.06, 1.645), (0.19, 0.16, 0.075), M['plate'], 0.02, 2))
    add('neck', C.cyl('neck', (0, 0, 1.555), 0.062, 0.13, M['plate']))
    add('chest', C.box('chest', (0, 0, 1.40), (0.40, 0.24, 0.20), M['armour'], 0.05, 3))
    add('chest', C.box('chest_plate', (0, 0.135, 1.42), (0.30, 0.05, 0.16), M['plate'], 0.02, 2))
    add('chest', C.box('backpack', (0, -0.16, 1.40), (0.26, 0.12, 0.30), M['plate'], 0.03, 2))
    add('abdomen', C.box('abdomen', (0, 0, 1.22), (0.33, 0.21, 0.20), M['cloth'], 0.04, 3))
    add('pelvis', C.box('pelvis', (0, 0, 1.055), (0.33, 0.21, 0.14), M['armour'], 0.03, 2))
    add('pelvis', C.box('belt', (0, 0, 1.105), (0.345, 0.22, 0.055), M['trim'], 0.01, 2))
    for s, x in (('L', 0.105), ('R', -0.105)):
        add('thigh.' + s, C.cyl('thigh.' + s, (x, 0, 0.755), 0.095, 0.45, M['cloth'], segments=16))
        add('shin.' + s, C.cyl('shin.' + s, (x, 0, 0.315), 0.078, 0.44, M['armour'], segments=16))
        add('foot.' + s, C.box('boot.' + s, (x, 0.03, 0.09), (0.13, 0.28, 0.18), M['boot'], 0.03, 2))
    for s, x in (('L', CH.ARM_X), ('R', -CH.ARM_X)):
        add('shoulder.' + s, C.box('pauldron.' + s, (x, 0, 1.475), (0.15, 0.17, 0.14), M['plate'], 0.03, 2))
        add('upper_arm.' + s, C.cyl('upper_arm.' + s, (x, 0, 1.325), 0.055, 0.26, M['cloth'], segments=12))
        add('forearm.' + s, C.cyl('forearm.' + s, (x, 0, 1.065), 0.05, 0.27, M['armour'], segments=12))
        add('forearm.' + s, C.box('vambrace.' + s, (x, 0.04, 1.06), (0.10, 0.09, 0.20), M['plate'], 0.02, 2))
        add('hand.' + s, C.box('hand.' + s, (x, 0.012, 0.895), (0.075, 0.10, 0.10), M['boot'], 0.02, 2))
    return p


def build_goon():
    C.reset_scene()
    M = goon_materials()
    parts = goon_body(M)
    for tag, ob in parts:
        C.tag_part(ob, tag)
    body = C.join([ob for _, ob in parts], 'GoonMesh')
    rig = C.build_armature('Rig', CH.BONES)
    C.skin_parts(body, rig, CH.PART_BONES)

    # reuse the player's clips: identical bone names, so they retarget for free
    C.make_action(rig, 'idle', CH.clip_idle())
    C.make_action(rig, 'walk', CH.clip_walk())
    C.make_action(rig, 'run', CH.clip_run())
    C.make_action(rig, 'aim', CH.clip_aim())
    C.make_action(rig, 'fire', CH.clip_fire())
    C.make_action(rig, 'reload', CH.clip_reload())
    rig.animation_data.action = None
    C.apply_pose(rig, {})

    path = os.path.join(ASSETS, 'enemy_goon.glb')
    C.export_glb(path, selection=[rig, body], viewer_name='neonrunner-enemy-goon.glb')
    C.report_glb(path)
    preview((3.0, 3.4, 1.7), (0, 0, 1.05), 'enemy_goon.png', lens=62)
    return path


# ------------------------------------------------------------------ mech

def mech_materials():
    return dict(
        hull=C.mat('MechHull', (0.07, 0.075, 0.09), 0.85, 0.38),
        plate=C.mat('MechPlate', (0.17, 0.18, 0.21), 0.9, 0.3),
        dark=C.mat('MechDark', (0.03, 0.03, 0.035), 0.4, 0.6),
        eye=C.mat('MechEye', (1.0, 0.35, 0.10), 0.0, 0.2, emission=(1.0, 0.35, 0.10), emission_strength=3.2),
        trim=C.mat('MechTrim', (0.1, 0.85, 1.0), 0.0, 0.3, emission=(0.1, 0.85, 1.0), emission_strength=2.0),
    )


def leg(M, idx, sx, sy, name):
    """Three segments per leg. Each is built at the origin and then moved so its node
    pivot sits on the joint the game rotates it about (hip -> knee -> foot)."""
    hip_joint = (0.62 * sx, 0.55 * sy, 1.06)
    knee_joint = (0.62 * sx * 1.06, 0.55 * sy * 1.10, 0.80)
    ankle_joint = (0.62 * sx * 1.12, 0.55 * sy * 1.34, 0.36)
    p = [
        C.box('leg_%d_hip' % idx, (0, 0, -0.06), (0.20, 0.24, 0.26), M['plate'], 0.04, 2),
        C.cyl('leg_%d_knee' % idx, (0, 0, -0.26), 0.075, 0.52, M['hull'], segments=10),
        C.cyl('leg_%d_foot' % idx, (0, 0, -0.22), 0.055, 0.44, M['dark'], segments=10),
        C.box('leg_%d_pad' % idx, (0, 0.16, -0.44), (0.20, 0.30, 0.10), M['dark'], 0.03, 2),
    ]
    for o, j in zip(p, (hip_joint, knee_joint, ankle_joint, ankle_joint)):
        o.location = j
    return p


def build_mech():
    C.reset_scene()
    M = mech_materials()
    p = []
    # chassis
    p.append(C.box('hull', (0, 0, 1.30), (1.30, 1.60, 0.52), M['hull'], 0.10, 3))
    p.append(C.box('hull_top', (0, -0.10, 1.62), (1.05, 1.25, 0.24), M['plate'], 0.07, 3))
    p.append(C.box('cockpit', (0, 0.62, 1.55), (0.62, 0.55, 0.34), M['dark'], 0.05, 2))
    p.append(C.box('eye', (0, 0.92, 1.56), (0.40, 0.06, 0.10), M['eye'], 0.01, 1))
    p.append(C.cyl('turret', (0, -0.30, 1.82), 0.20, 0.24, M['plate'], segments=14))
    p.append(C.cyl('barrel', (0, -0.92, 1.86), 0.075, 1.10, M['dark'], axis='Y', segments=12))
    p.append(C.box('vent', (0, 0.0, 1.08), (1.34, 0.30, 0.16), M['trim'], 0.02, 2))
    for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        p += leg(M, i, sx, sy, 'leg_%d' % i)
    for o in p:
        o.select_set(False)
    path = os.path.join(ASSETS, 'enemy_mech.glb')
    C.export_glb(path, selection=None, animations=False, viewer_name='neonrunner-enemy-mech.glb')
    tris = sum(sum(len(poly.vertices) - 2 for poly in o.data.polygons) for o in p)
    print('[mech] objects=%d tris=%d' % (len(p), tris))
    C.report_glb(path)
    preview((3.6, 4.0, 2.4), (0, 0, 1.1), 'enemy_mech.png', lens=50)
    return path


# ------------------------------------------------------------------ shared

def preview(cam_loc, cam_target, filename, lens=52):
    C.add_light('key', 'AREA', (3.2, 4.2, 4.2), 900, (1.0, 0.95, 0.9), size=5.0, target=(0, 0, 1.2))
    C.add_light('fill', 'AREA', (-4.2, 1.2, 2.2), 320, (0.4, 0.7, 1.0), size=6.0, target=(0, 0, 1.2))
    C.add_light('rim', 'AREA', (0.0, -5.2, 3.2), 420, (1.0, 0.3, 0.5), size=5.0, target=(0, 0, 1.4))
    world = bpy.data.worlds.new('W')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.02, 0.025, 0.04, 1)
    bpy.context.scene.world = world
    C.setup_render(width=1000, height=820, samples=48)
    C.add_camera('Cam', cam_loc, cam_target, lens=lens)
    C.render_to(os.path.join(RENDERS, filename))


if __name__ == '__main__':
    build_goon()
    build_mech()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'assets_src', 'enemies.blend'))
    print('[done] enemies')
