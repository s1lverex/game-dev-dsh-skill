"""NEON RUNNER — merged hero render: character holding the Kestrel-9, standing in the city block.

Imports the three exported GLBs, drives the character into its aim clip, parents the
pistol to the right hand, lights the street and renders the money shot.

Run:  blender --background --python tools/blender/hero_render.py
Out:  assets_src/renders/merged_hero.png (also published to the 3D viewer)
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ASSETS = os.path.join(ROOT, 'game', 'assets')
OUT = os.path.join(ROOT, 'assets_src', 'renders', 'merged_hero.png')

CHAR_POS = Vector((10.0, 4.2, 0.16))   # on the sidewalk by the crossing
CHAR_YAW = -28.0                        # degrees, facing into the road


def find_bone(arm, *needles):
    for b in arm.pose.bones:
        n = b.name.lower()
        if all(x.lower() in n for x in needles):
            return b
    return None


def set_clip(arm, clip):
    """Activate one imported clip, via NLA strip or direct action, whichever exists."""
    if arm.animation_data is None:
        arm.animation_data_create()
    ad = arm.animation_data
    used = None
    for tr in ad.nla_tracks:
        for st in tr.strips:
            hit = clip in st.action.name.lower()
            tr.mute = not hit
            if hit:
                used = st
    if used is not None:
        bpy.context.scene.frame_set(int(used.frame_start))
        return 'nla:' + used.action.name
    for a in bpy.data.actions:
        if clip in a.name.lower():
            ad.action = a
            if hasattr(ad, 'action_slot') and a.slots:
                ad.action_slot = a.slots[0]
            bpy.context.scene.frame_set(1)
            return 'action:' + a.name
    return 'none'


def main():
    C.reset_scene()
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, 'city.glb'))
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, 'character.glb'))
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, 'pistol.glb'))

    arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    chars = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm]
    print('[hero] armature=%s bones=%d body=%s' % (arm.name, len(arm.pose.bones), [o.name for o in chars]))
    arm.location = CHAR_POS
    arm.rotation_euler = (0, 0, math.radians(CHAR_YAW))
    # the mesh is parented to the armature: move the rig only, never both

    print('[hero] clip ->', set_clip(arm, 'aim'))

    hand = find_bone(arm, 'hand', 'r')
    print('[hero] hand bone:', hand.name if hand else None)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = arm.evaluated_get(dg)
    hand_world = arm.matrix_world @ ev.pose.bones[hand.name].matrix
    grip = hand_world.translation + Vector((0.0, 0.075, 0.02))

    gun = next((o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Pistol')), None)
    gun.rotation_mode = 'XYZ'
    gun.matrix_world = (Matrix.Translation(grip)
                        @ Matrix.Rotation(math.radians(CHAR_YAW - 10.0), 4, 'Z')
                        @ Matrix.Rotation(math.radians(-6.0), 4, 'X'))
    print('[hero] pistol at', tuple(round(v, 3) for v in grip))

    # street lighting + camera derived from the character's facing vector
    fwd = Vector((math.sin(math.radians(CHAR_YAW)), math.cos(math.radians(CHAR_YAW)), 0.0))
    rgt = Vector((-fwd.y, fwd.x, 0.0))
    chest = CHAR_POS + Vector((0, 0, 1.15))
    C.add_light('key', 'AREA', tuple(CHAR_POS + fwd * 2.8 + rgt * 1.7 + Vector((0, 0, 2.4))), 420,
                (1.0, 0.72, 0.62), size=2.0, target=tuple(chest))
    C.add_light('fill', 'AREA', tuple(CHAR_POS + fwd * 2.2 - rgt * 2.6 + Vector((0, 0, 1.7))), 170,
                (0.35, 0.7, 1.0), size=2.5, target=tuple(chest))
    C.add_light('rim', 'AREA', tuple(CHAR_POS - fwd * 2.6 + Vector((0, 0, 2.5))), 300,
                (1.0, 0.25, 0.7), size=1.6, target=tuple(chest))
    C.add_light('street', 'POINT', (11.5, 11.5, 6.0), 900, (1.0, 0.7, 0.35), size=2.0)
    world = bpy.data.worlds.new('W')
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.015, 0.02, 0.035, 1)
    bg.inputs[1].default_value = 0.5
    bpy.context.scene.world = world
    cam = CHAR_POS + fwd * 4.6 + rgt * 1.9 + Vector((0, 0, 1.9))
    C.add_camera('Cam', tuple(cam), tuple(CHAR_POS + Vector((0, 0, 1.2))), lens=55)
    C.setup_render(width=1180, height=820, samples=96)
    C.render_to(OUT)
    print('[done] merged hero render')


main()
