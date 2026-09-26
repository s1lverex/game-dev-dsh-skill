"""NEON RUNNER — character asset.

Original 'rockerboy' design inspired by the supplied reference (long dark hair,
red shades, dark tank top, belt, maroon leather pants, boots, one chrome
cyber-arm). No third-party trademarks or logos are reproduced.

Run:  blender --background --python tools/blender/character.py
Out:  game/assets/character.glb, assets_src/character.blend, assets_src/renders/character_hero.png
"""
import os
import sys

import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
GLB = os.path.join(ROOT, 'game', 'assets', 'character.glb')
BLEND = os.path.join(ROOT, 'assets_src', 'character.blend')
RENDER = os.path.join(ROOT, 'assets_src', 'renders', 'character_hero.png')

ARM_X = 0.20  # arms hang clear of the thighs so hands never sit inside leg geometry

# character faces +Y in Blender -> -Z in glTF/Godot (Godot forward)
BONES = [
    ('hips',        (0, 0, 1.00), (0, 0, 1.12), None, False),
    ('spine',       (0, 0, 1.12), (0, 0, 1.32), 'hips', True),
    ('chest',       (0, 0, 1.32), (0, 0, 1.50), 'spine', True),
    ('neck',        (0, 0, 1.50), (0, 0, 1.62), 'chest', True),
    ('head',        (0, 0, 1.62), (0, 0.002, 1.80), 'neck', True),
    ('shoulder.L',  (0.04, 0, 1.47), (ARM_X, 0, 1.465), 'chest', False),
    ('upper_arm.L', (ARM_X, 0, 1.465), (ARM_X, 0, 1.20), 'shoulder.L', True),
    ('forearm.L',   (ARM_X, 0, 1.20), (ARM_X, 0, 0.945), 'upper_arm.L', True),
    ('hand.L',      (ARM_X, 0, 0.945), (ARM_X, 0.01, 0.845), 'forearm.L', True),
    ('shoulder.R',  (-0.04, 0, 1.47), (-ARM_X, 0, 1.465), 'chest', False),
    ('upper_arm.R', (-ARM_X, 0, 1.465), (-ARM_X, 0, 1.20), 'shoulder.R', True),
    ('forearm.R',   (-ARM_X, 0, 1.20), (-ARM_X, 0, 0.945), 'upper_arm.R', True),
    ('hand.R',      (-ARM_X, 0, 0.945), (-ARM_X, 0.01, 0.845), 'forearm.R', True),
    ('thigh.L',     (0.105, 0, 0.98), (0.105, 0, 0.53), 'hips', False),
    ('shin.L',      (0.105, 0, 0.53), (0.105, 0, 0.095), 'thigh.L', True),
    ('foot.L',      (0.105, 0, 0.095), (0.105, 0.17, 0.03), 'shin.L', True),
    ('thigh.R',     (-0.105, 0, 0.98), (-0.105, 0, 0.53), 'hips', False),
    ('shin.R',      (-0.105, 0, 0.53), (-0.105, 0, 0.095), 'thigh.R', True),
    ('foot.R',      (-0.105, 0, 0.095), (-0.105, 0.17, 0.03), 'shin.R', True),
]

# each part may only bind to the listed bones — prevents cross-limb weight bleed
PART_BONES = {
    'head': ['head', 'neck'],
    'neck': ['neck', 'head', 'chest'],
    'chest': ['chest', 'spine'],
    'abdomen': ['spine', 'chest', 'hips'],
    'pelvis': ['hips', 'spine'],
    'thigh.L': ['thigh.L', 'hips', 'shin.L'],
    'shin.L': ['shin.L', 'thigh.L', 'foot.L'],
    'foot.L': ['foot.L', 'shin.L'],
    'thigh.R': ['thigh.R', 'hips', 'shin.R'],
    'shin.R': ['shin.R', 'thigh.R', 'foot.R'],
    'foot.R': ['foot.R', 'shin.R'],
    'shoulder.L': ['shoulder.L', 'upper_arm.L', 'chest'],
    'upper_arm.L': ['upper_arm.L', 'shoulder.L', 'forearm.L'],
    'forearm.L': ['forearm.L', 'upper_arm.L', 'hand.L'],
    'hand.L': ['hand.L', 'forearm.L'],
    'shoulder.R': ['shoulder.R', 'upper_arm.R', 'chest'],
    'upper_arm.R': ['upper_arm.R', 'shoulder.R', 'forearm.R'],
    'forearm.R': ['forearm.R', 'upper_arm.R', 'hand.R'],
    'hand.R': ['hand.R', 'forearm.R'],
}


def build_materials():
    return dict(
        skin=C.mat('Skin', (0.66, 0.47, 0.37), 0.0, 0.58),
        hair=C.mat('Hair', (0.045, 0.030, 0.028), 0.0, 0.32),
        tank=C.mat('TankTop', (0.085, 0.085, 0.095), 0.0, 0.82),
        print_=C.mat('TankPrint', (0.62, 0.06, 0.07), 0.0, 0.6),
        leather=C.mat('Leather', (0.135, 0.055, 0.05), 0.0, 0.26),
        boot=C.mat('Boot', (0.055, 0.038, 0.033), 0.0, 0.34),
        chrome=C.mat('Chrome', (0.86, 0.88, 0.92), 1.0, 0.11),
        dark=C.mat('DarkMetal', (0.16, 0.17, 0.19), 1.0, 0.38),
        red=C.mat('RedAccent', (0.72, 0.06, 0.06), 0.2, 0.3),
        lens=C.mat('ShadeLens', (0.85, 0.06, 0.05), 0.0, 0.08, emission=(1.0, 0.08, 0.05), emission_strength=1.6),
    )


def build_body(M):
    """Returns [(part_tag, object), ...] — the tag selects the allowed bones."""
    p = []

    def add(tag, ob):
        p.append((tag, ob))

    # head, jaw, neck
    add('head', C.sphere('head', (0, 0.004, 1.72), 0.112, M['skin'], scale=(0.90, 1.0, 1.14)))
    add('head', C.box('jaw', (0, -0.008, 1.652), (0.14, 0.165, 0.10), M['skin'], 0.028, 3))
    add('neck', C.cyl('neck', (0, 0, 1.555), 0.058, 0.13, M['skin']))
    # torso: dark tank top
    add('chest', C.box('chest', (0, 0, 1.40), (0.34, 0.20, 0.19), M['tank'], 0.05, 3))
    add('abdomen', C.box('abdomen', (0, 0, 1.225), (0.30, 0.18, 0.20), M['tank'], 0.045, 3))
    add('abdomen', C.box('tank_print', (0, 0.098, 1.30), (0.15, 0.01, 0.15), M['print_'], 0.004, 2))
    # pelvis + belt
    add('pelvis', C.box('pelvis', (0, 0, 1.055), (0.31, 0.19, 0.13), M['leather'], 0.03, 2))
    add('pelvis', C.box('belt', (0, 0, 1.105), (0.325, 0.20, 0.05), M['dark'], 0.008, 2))
    add('pelvis', C.box('buckle', (0, 0.098, 1.105), (0.055, 0.022, 0.042), M['chrome'], 0.006, 2))
    add('chest', C.box('tag', (0.015, 0.105, 1.345), (0.035, 0.008, 0.05), M['chrome'], 0.004, 2))
    # legs: maroon leather
    for s, x in (('L', 0.105), ('R', -0.105)):
        add('thigh.' + s, C.cyl('thigh.' + s, (x, 0, 0.755), 0.085, 0.45, M['leather'], segments=18))
        add('shin.' + s, C.cyl('shin.' + s, (x, 0, 0.315), 0.067, 0.44, M['leather'], segments=18))
        add('foot.' + s, C.box('boot_shaft.' + s, (x, 0, 0.145), (0.115, 0.15, 0.16), M['boot'], 0.02, 2))
        add('foot.' + s, C.box('boot.' + s, (x, 0.035, 0.045), (0.115, 0.255, 0.09), M['boot'], 0.02, 2))
    # left (organic) arm
    add('shoulder.L', C.sphere('shoulder_m.L', (ARM_X, 0, 1.44), 0.062, M['skin']))
    add('upper_arm.L', C.cyl('upper_arm.L', (ARM_X, 0, 1.325), 0.05, 0.26, M['skin'], segments=14))
    add('forearm.L', C.cyl('forearm.L', (ARM_X, 0, 1.065), 0.045, 0.27, M['skin'], segments=14))
    add('hand.L', C.box('hand.L', (ARM_X, 0.012, 0.895), (0.07, 0.10, 0.105), M['skin'], 0.02, 2))
    # right chrome cyber-arm
    add('shoulder.R', C.sphere('shoulder_m.R', (-ARM_X, 0, 1.44), 0.064, M['dark']))
    add('upper_arm.R', C.cyl('upper_arm.R', (-ARM_X, 0, 1.325), 0.05, 0.24, M['skin'], segments=14))
    add('forearm.R', C.sphere('elbow.R', (-ARM_X, 0, 1.195), 0.058, M['chrome']))
    add('forearm.R', C.cyl('forearm.R', (-ARM_X, 0, 1.065), 0.05, 0.26, M['chrome'], segments=16))
    add('forearm.R', C.cyl('arm_ring_a', (-ARM_X, 0, 1.16), 0.056, 0.022, M['red'], segments=16))
    add('forearm.R', C.cyl('arm_ring_b', (-ARM_X, 0, 1.05), 0.054, 0.022, M['red'], segments=16))
    add('forearm.R', C.box('arm_actuator', (-ARM_X, -0.048, 1.10), (0.032, 0.032, 0.16), M['dark'], 0.006, 2))
    add('hand.R', C.box('hand.R', (-ARM_X, 0.012, 0.895), (0.07, 0.10, 0.105), M['chrome'], 0.02, 2))
    # hair: cap + back mass to the shoulders + side strands
    add('head', C.sphere('hair_cap', (0, -0.018, 1.745), 0.118, M['hair'], scale=(0.96, 1.0, 1.0)))
    add('head', C.box('hair_back', (0, -0.082, 1.605), (0.205, 0.08, 0.33), M['hair'], 0.032, 3))
    add('head', C.box('hair_L', (0.098, -0.03, 1.645), (0.045, 0.09, 0.27), M['hair'], 0.02, 2))
    add('head', C.box('hair_R', (-0.098, -0.03, 1.645), (0.045, 0.09, 0.27), M['hair'], 0.02, 2))
    # red shades
    add('head', C.box('shades_frame', (0, 0.062, 1.752), (0.195, 0.035, 0.05), M['dark'], 0.008, 2))
    add('head', C.box('shades_L', (0.052, 0.088, 1.754), (0.072, 0.012, 0.04), M['lens'], 0.004, 2))
    add('head', C.box('shades_R', (-0.052, 0.088, 1.754), (0.072, 0.012, 0.04), M['lens'], 0.004, 2))
    add('head', C.box('shades_temple_L', (0.097, -0.005, 1.757), (0.012, 0.14, 0.012), M['dark'], 0.003, 1))
    add('head', C.box('shades_temple_R', (-0.097, -0.005, 1.757), (0.012, 0.14, 0.012), M['dark'], 0.003, 1))
    # stubble / moustache band
    add('head', C.box('stubble', (0, 0.075, 1.66), (0.105, 0.03, 0.05), M['hair'], 0.012, 2))
    return p


# --------------------------------------------------------------- animation

# Sighted pose: arms raised so the weapon sits just below the eyeline. That keeps
# the pistol visible in the first-person camera instead of at the frame edge.
AIM = {
    'chest': (2, 0, -7), 'spine': (1, 0, -4), 'head': (0, 0, 6),
    'shoulder.R': (0, 0, -10), 'upper_arm.R': (76, -7, -16), 'forearm.R': (20, 0, -8), 'hand.R': (0, 0, -6),
    'shoulder.L': (0, 0, 12), 'upper_arm.L': (70, 11, 26), 'forearm.L': (46, 0, 20), 'hand.L': (0, 0, 14),
    'thigh.L': (-4, 0, 0), 'thigh.R': (4, 0, 0),
}


def pose(base=None, **over):
    p = dict(base) if base else {}
    p.update(over)
    return p


def clip_idle():
    a = {'chest': (-1, 0, 0), 'spine': (0, 0, 0), 'head': (0, 0, -4), 'hips_loc': (0, 0, -0.004),
         'upper_arm.L': (-2, 4, 0), 'upper_arm.R': (-2, -4, 0),
         'forearm.L': (4, 0, 0), 'forearm.R': (6, 0, 0), 'thigh.L': (0, 0, 0), 'thigh.R': (0, 0, 0)}
    b = pose(a, chest=(1, 0, 0.8), spine=(0.5, 0, 0), head=(-1, 0, 5), hips_loc=(0.008, 0, 0.01),
             **{'upper_arm.L': (0, 3, 0), 'upper_arm.R': (0, -5, 0), 'forearm.L': (6, 0, 0), 'forearm.R': (8, 0, 0)})
    c = pose(a, chest=(-1, 0, -0.6), head=(0, 0, -7), hips_loc=(0, 0, -0.006),
             **{'upper_arm.L': (-3, 5, 0), 'upper_arm.R': (-3, -3, 0)})
    d = pose(a, chest=(0.6, 0, 0.4), head=(1, 0, 2), hips_loc=(-0.006, 0, 0.006),
             **{'upper_arm.L': (-1, 4, 0), 'upper_arm.R': (-1, -4, 0), 'forearm.L': (5, 0, 0), 'forearm.R': (7, 0, 0)})
    return [(1, a), (24, b), (48, c), (72, d), (96, a)]


def clip_walk():
    contact = {'spine': (3, 0, 0), 'chest': (2, 0, 0), 'head': (-2, 0, 0), 'hips_loc': (0, 0, -0.012),
               'thigh.L': (22, 0, 0), 'shin.L': (-8, 0, 0), 'foot.L': (10, 0, 0),
               'thigh.R': (-18, 0, 0), 'shin.R': (-26, 0, 0), 'foot.R': (16, 0, 0),
               'shoulder.L': (0, 0, 3), 'shoulder.R': (0, 0, -3),
               'upper_arm.L': (-20, 3, 0), 'forearm.L': (24, 0, 0),
               'upper_arm.R': (20, -3, 0), 'forearm.R': (16, 0, 0)}
    passing = {'spine': (3, 0, 0), 'chest': (2, 0, 0), 'head': (-2, 0, 0), 'hips_loc': (0, 0, 0.012),
               'thigh.L': (2, 0, 0), 'shin.L': (-32, 0, 0), 'foot.L': (-6, 0, 0),
               'thigh.R': (-10, 0, 0), 'shin.R': (-6, 0, 0), 'foot.R': (6, 0, 0),
               'upper_arm.L': (-6, 3, 0), 'forearm.L': (18, 0, 0),
               'upper_arm.R': (6, -3, 0), 'forearm.R': (14, 0, 0)}
    return [(1, contact), (9, passing), (17, C.mirror_pose(contact)), (25, C.mirror_pose(passing)), (33, contact)]


def clip_run():
    contact = {'spine': (10, 0, 0), 'chest': (7, 0, 0), 'head': (-9, 0, 0), 'hips_loc': (0, 0, -0.02),
               'thigh.L': (44, 0, 0), 'shin.L': (-38, 0, 0), 'foot.L': (12, 0, 0),
               'thigh.R': (-34, 0, 0), 'shin.R': (-72, 0, 0), 'foot.R': (18, 0, 0),
               'shoulder.L': (0, 0, 6), 'shoulder.R': (0, 0, -6),
               'upper_arm.L': (-48, 6, 0), 'forearm.L': (88, 0, 0),
               'upper_arm.R': (52, -6, 0), 'forearm.R': (84, 0, 0)}
    air = {'spine': (10, 0, 0), 'chest': (7, 0, 0), 'head': (-9, 0, 0), 'hips_loc': (0, 0, 0.055),
           'thigh.L': (6, 0, 0), 'shin.L': (-96, 0, 0), 'foot.L': (-10, 0, 0),
           'thigh.R': (-12, 0, 0), 'shin.R': (-34, 0, 0), 'foot.R': (10, 0, 0),
           'upper_arm.L': (-14, 6, 0), 'forearm.L': (92, 0, 0),
           'upper_arm.R': (18, -6, 0), 'forearm.R': (88, 0, 0)}
    return [(1, contact), (7, air), (13, C.mirror_pose(contact)), (19, C.mirror_pose(air)), (25, contact)]


def clip_aim():
    a = pose(AIM)
    b = pose(AIM, chest=(2.6, 0, -7), **{'upper_arm.R': (67.5, -6, -14), 'upper_arm.L': (59, 10, 26), 'head': (0, 0, 6)})
    c = pose(AIM, chest=(1.6, 0, -7.4), **{'upper_arm.R': (65, -6, -14), 'upper_arm.L': (57, 10, 26), 'head': (0.4, 0, 6)})
    return [(1, a), (13, b), (25, c)]


def clip_fire():
    base = pose(AIM)
    kick = pose(AIM, chest=(-3, -1, -9), spine=(-1, 0, -4), head=(-4, 0, 6),
                **{'upper_arm.R': (76, -6, -12), 'forearm.R': (14, 0, -6), 'hand.R': (-14, 0, -4),
                   'upper_arm.L': (64, 10, 24), 'forearm.L': (40, 0, 18)})
    settle = pose(AIM, chest=(0.5, 0, -7.5), head=(-1, 0, 6),
                  **{'upper_arm.R': (69, -6, -14), 'upper_arm.L': (60, 10, 26)})
    return [(1, base), (3, kick), (7, settle), (12, base)]


def clip_reload():
    base = pose(AIM)
    down = pose(AIM, chest=(4, 0, 4), head=(6, 0, -4),
                **{'shoulder.L': (0, 0, 4), 'upper_arm.L': (16, 10, 14), 'forearm.L': (96, 0, 22), 'hand.L': (0, 0, 20)})
    grab = pose(AIM, chest=(5, 0, 6), head=(7, 0, -6),
                **{'upper_arm.L': (10, 12, 12), 'forearm.L': (112, 0, 26), 'hand.L': (-16, 0, 24)})
    insert = pose(AIM, chest=(3, 0, 2), head=(4, 0, -2),
                  **{'upper_arm.L': (44, 12, 22), 'forearm.L': (66, 0, 20), 'hand.L': (0, 0, 16)})
    slap = pose(AIM, chest=(2, 0, -6), head=(1, 0, 4),
                **{'upper_arm.L': (52, 10, 26), 'forearm.L': (48, 0, 18), 'hand.L': (0, 0, 6)})
    return [(1, base), (8, down), (16, grab), (24, insert), (30, slap), (36, base)]


def main():
    C.reset_scene()
    M = build_materials()
    parts = build_body(M)
    for tag, ob in parts:
        C.tag_part(ob, tag)
    # head is a separate mesh so the game can hide just the head in first person,
    # keeping the arms and weapon visible instead of a floating gun
    head_objs = [ob for tag, ob in parts if tag == 'head']
    body_objs = [ob for tag, ob in parts if tag != 'head']
    body = C.join(body_objs, 'CharacterMesh')
    head = C.join(head_objs, 'CharacterHead')
    for ob in (body, head):
        print('[mesh] %s verts=%d tris=%d' % (ob.name, len(ob.data.vertices),
              sum(len(p.vertices) - 2 for p in ob.data.polygons)))

    rig = C.build_armature('Rig', BONES)
    C.skin_parts(body, rig, PART_BONES)
    C.skin_parts(head, rig, PART_BONES)

    C.make_action(rig, 'idle', clip_idle())
    C.make_action(rig, 'walk', clip_walk())
    C.make_action(rig, 'run', clip_run())
    C.make_action(rig, 'aim', clip_aim())
    C.make_action(rig, 'fire', clip_fire())
    C.make_action(rig, 'reload', clip_reload())
    rig.animation_data.action = None
    C.apply_pose(rig, {})

    rig.animation_data.action = bpy.data.actions['aim']
    C.export_glb(GLB, selection=[rig, body, head], viewer_name='neonrunner-character.glb')
    rig.animation_data.action = None
    C.apply_pose(rig, {})
    C.report_glb(GLB)

    # preview scene, added after export so no lights/cameras land in the GLB
    C.add_light('key', 'AREA', (1.9, 2.5, 2.5), 800, (1.0, 0.97, 0.94), size=2.6, target=(0, 0, 1.3))
    C.add_light('fill', 'AREA', (-2.4, 1.9, 1.5), 260, (0.55, 0.72, 1.0), size=3.0, target=(0, 0, 1.2))
    C.add_light('rim', 'AREA', (-0.5, -2.8, 2.3), 480, (0.72, 0.84, 1.0), size=2.0, target=(0, 0, 1.4))
    world = bpy.data.worlds.new('W')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.012, 0.014, 0.022, 1)
    bpy.context.scene.world = world
    C.add_camera('Cam', (1.35, 3.05, 1.5), (0, 0, 1.10), lens=62)
    C.setup_render(width=820, height=1040, samples=64)
    C.render_to(RENDER)

    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print('[done] character asset')


if __name__ == '__main__':
    main()
