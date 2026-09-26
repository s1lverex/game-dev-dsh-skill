"""Diagnostics: skinning weight sanity + edge-stretch metric + orthogonal pose views.
Run: blender --background --python tools/blender/diag.py
"""
import os
import sys

import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, 'assets_src', 'character.blend'))
sc = bpy.context.scene

body = bpy.data.objects['CharacterMesh']
rig = bpy.data.objects['Rig']

# ---- weight sanity
me = body.data
zero = 0
bad_sum = 0
maxg = 0
for v in me.vertices:
    s = sum(g.weight for g in v.groups)
    if not v.groups:
        zero += 1
    elif abs(s - 1.0) > 1e-3:
        bad_sum += 1
    maxg = max(maxg, len(v.groups))
print('[weights] verts=%d unweighted=%d bad_sum=%d max_groups=%d groups=%d'
      % (len(me.vertices), zero, bad_sum, maxg, len(body.vertex_groups)))
counts = {}
for v in me.vertices:
    for g in v.groups:
        counts[body.vertex_groups[g.group].name] = counts.get(body.vertex_groups[g.group].name, 0) + 1
print('[weights] per-bone vertex counts:', {k: counts.get(k, 0) for k in [b.name for b in rig.data.bones]})

# ---- edge stretch per clip
rest = {}
for e in me.edges:
    a, b = e.vertices
    rest[e.index] = (me.vertices[a].co - me.vertices[b].co).length
if rig.animation_data is None:
    rig.animation_data_create()
dg = bpy.context.evaluated_depsgraph_get()
for clip in ('idle', 'walk', 'run', 'aim', 'fire', 'reload'):
    rig.animation_data.action = bpy.data.actions[clip]
    worst, worst_f, worst_e = 0.0, 0, -1
    for f in range(1, 37):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        m = ev.to_mesh()
        for e in me.edges:
            a, b = e.vertices
            L = (m.vertices[a].co - m.vertices[b].co).length
            r = rest[e.index]
            if r > 1e-5:
                s = L / r
                if s > worst:
                    worst, worst_f, worst_e = s, f, e.index
        ev.to_mesh_clear()
    print('[stretch] %-7s max=%.2fx at frame %d edge %d' % (clip, worst, worst_f, worst_e))
rig.animation_data.action = None

# ---- orthogonal views of the run pose
for o in list(bpy.context.view_layer.objects):
    if o.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(o, do_unlink=True)
C.add_light('key', 'AREA', (2.0, 2.2, 2.6), 800, (1.0, 0.97, 0.94), 3.0, (0, 0, 1.2))
C.add_light('fill', 'AREA', (-2.4, -1.6, 1.6), 300, (0.6, 0.75, 1.0), 3.0, (0, 0, 1.2))
C.add_light('rim', 'AREA', (-0.4, -2.6, 2.2), 400, (0.8, 0.85, 1.0), 2.0, (0, 0, 1.3))
C.setup_render(width=620, height=820, samples=32)
OUT = os.path.join(ROOT, 'assets_src', 'renders')

views = [('diag_front.png', (0.0, 3.4, 1.3)), ('diag_right.png', (-3.4, 0.0, 1.3)), ('diag_iso.png', (2.2, 2.2, 1.6))]
for clip, frame in (('run', 6), ('aim', 1), ('walk', 9)):
    rig.animation_data.action = bpy.data.actions[clip]
    sc.frame_set(frame)
    for name, loc in views:
        C.add_camera('C_' + clip + name, loc, (0, 0, 1.05), lens=50)
        sc.render.filepath = os.path.join(OUT, clip + '_' + name)
        bpy.ops.render.render(write_still=True)
        print('[shot]', clip, name)
