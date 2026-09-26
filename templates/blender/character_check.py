"""Validation renders for the character asset: front view, aim pose, run pose.
Run: blender --background --python tools/blender/character_check.py
"""
import os
import sys

import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
BLEND = os.path.join(ROOT, 'assets_src', 'character.blend')
OUT = os.path.join(ROOT, 'assets_src', 'renders')

bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene

for o in list(bpy.context.view_layer.objects):
    if o.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(o, do_unlink=True)

C.add_light('key', 'AREA', (1.8, 2.6, 2.5), 700, (1.0, 0.97, 0.94), size=2.6, target=(0, 0, 1.3))
C.add_light('fill', 'AREA', (-2.4, 1.8, 1.5), 250, (0.6, 0.75, 1.0), size=3.0, target=(0, 0, 1.2))
C.add_light('rim', 'AREA', (-0.6, -2.8, 2.3), 450, (0.75, 0.85, 1.0), size=2.0, target=(0, 0, 1.4))
C.setup_render(width=760, height=1000, samples=48)

rig = bpy.data.objects['Rig']
if rig.animation_data is None:
    rig.animation_data_create()

shots = [
    ('character_front.png', None, (0.0, 3.1, 1.35), (0, 0, 1.15), 60),
    ('character_aim.png', 'aim', (1.5, 2.6, 1.45), (0, 0, 1.15), 60),
    ('character_run.png', 'run', (1.9, 2.3, 1.35), (0, 0, 1.1), 55),
]
for name, clip, loc, tgt, lens in shots:
    if clip:
        rig.animation_data.action = bpy.data.actions[clip]
        sc.frame_set(6 if clip == 'run' else 1)
    else:
        rig.animation_data.action = None
        C.apply_pose(rig, {})
    C.add_camera('Cam_' + name, loc, tgt, lens=lens)
    sc.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print('[shot]', name)
