"""NEON RUNNER — vehicles: sedan, truck, bike.

Authored for in-engine driving:
  * origin at ground level, +Y (Blender) = forward -> -Z in Godot
  * every wheel is its own named object (wheel_*) so the game can spin and steer
    them without a skeleton
  * separate GLB per type so instances are cheap

Run:  blender --background --python tools/blender/vehicles.py
Out:  game/assets/vehicle_sedan.glb, vehicle_truck.glb, vehicle_bike.glb
"""
import math
import os
import sys

import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ASSETS = os.path.join(ROOT, 'game', 'assets')
RENDERS = os.path.join(ROOT, 'assets_src', 'renders')


def mats(body_color):
    return dict(
        body=C.mat('VehBody', body_color, 0.55, 0.28),
        trim=C.mat('VehTrim', (0.05, 0.05, 0.06), 0.7, 0.4),
        glass=C.mat('VehGlass', (0.02, 0.05, 0.08), 0.6, 0.08),
        tyre=C.mat('VehTyre', (0.025, 0.025, 0.03), 0.0, 0.85),
        rim=C.mat('VehRim', (0.75, 0.77, 0.8), 1.0, 0.22),
        head=C.mat('VehHead', (1.0, 0.95, 0.85), 0.0, 0.2, emission=(1.0, 0.95, 0.85), emission_strength=3.0),
        tail=C.mat('VehTail', (1.0, 0.12, 0.1), 0.0, 0.3, emission=(1.0, 0.12, 0.1), emission_strength=2.4),
        neon=C.mat('VehNeon', (0.15, 0.9, 1.0), 0.0, 0.3, emission=(0.15, 0.9, 1.0), emission_strength=2.2),
    )


def wheel(M, name, x, y, r=0.34, w=0.22):
    """Wheel built at the origin and then placed: the node pivot IS the axle, so the
    game can spin it about local X (Blender geometry is otherwise baked in world space)."""
    p = [C.cyl(name, (0, 0, 0), r, w, M['tyre'], axis='X', segments=20)]
    p.append(C.cyl(name + '_rim', (0, 0, 0), r * 0.55, w * 1.05, M['rim'], axis='X', segments=14))
    for o in p:
        o.location = (x, y, r)
    return p


def sedan(M):
    p = []
    p.append(C.box('body', (0, 0, 0.62), (1.78, 4.30, 0.62), M['body'], 0.16, 3))
    p.append(C.box('cabin', (0, -0.25, 1.16), (1.55, 2.05, 0.52), M['body'], 0.14, 3))
    p.append(C.box('windshield', (0, 0.72, 1.14), (1.42, 0.14, 0.44), M['glass'], 0.02, 2, rot_x=-22))
    p.append(C.box('rear_glass', (0, -1.25, 1.14), (1.42, 0.14, 0.44), M['glass'], 0.02, 2, rot_x=20))
    for s in (1, -1):
        p.append(C.box('side_glass_%d' % s, (0.78 * s, -0.25, 1.16), (0.06, 1.7, 0.40), M['glass'], 0.02, 2))
        p.append(C.box('mirror_%d' % s, (0.98 * s, 0.62, 1.10), (0.16, 0.10, 0.10), M['trim'], 0.02, 2))
    p.append(C.box('bumper_f', (0, 2.12, 0.52), (1.80, 0.22, 0.34), M['trim'], 0.06, 2))
    p.append(C.box('bumper_r', (0, -2.12, 0.52), (1.80, 0.22, 0.34), M['trim'], 0.06, 2))
    for s in (1, -1):
        p.append(C.box('headlight_%d' % s, (0.62 * s, 2.16, 0.80), (0.44, 0.10, 0.18), M['head'], 0.02, 2))
        p.append(C.box('taillight_%d' % s, (0.62 * s, -2.16, 0.84), (0.44, 0.10, 0.16), M['tail'], 0.02, 2))
    p.append(C.box('skirt_l', (0, 0, 0.30), (1.86, 3.6, 0.16), M['neon'], 0.03, 2))
    for name, x, y in (('wheel_fl', 0.86, 1.42), ('wheel_fr', -0.86, 1.42),
                       ('wheel_rl', 0.86, -1.42), ('wheel_rr', -0.86, -1.42)):
        p += wheel(M, name, x, y)
    return p


def truck(M):
    p = []
    p.append(C.box('body', (0, 1.30, 0.78), (2.30, 2.60, 0.86), M['body'], 0.18, 3))
    p.append(C.box('cabin', (0, 2.05, 1.85), (2.20, 1.60, 1.30), M['body'], 0.16, 3))
    p.append(C.box('windshield', (0, 2.84, 1.95), (2.00, 0.14, 0.86), M['glass'], 0.02, 2, rot_x=-12))
    p.append(C.box('cargo', (0, -1.70, 1.65), (2.34, 3.30, 1.90), M['trim'], 0.14, 3))
    p.append(C.box('cargo_top', (0, -1.70, 2.62), (2.30, 3.26, 0.10), M['body'], 0.04, 2))
    for s in (1, -1):
        p.append(C.box('side_glass_%d' % s, (1.10 * s, 2.05, 1.98), (0.06, 1.30, 0.72), M['glass'], 0.02, 2))
        p.append(C.box('headlight_%d' % s, (0.80 * s, 2.90, 0.95), (0.50, 0.12, 0.24), M['head'], 0.02, 2))
        p.append(C.box('taillight_%d' % s, (0.90 * s, -3.36, 1.05), (0.44, 0.12, 0.28), M['tail'], 0.02, 2))
    p.append(C.box('bumper_f', (0, 2.92, 0.62), (2.32, 0.24, 0.40), M['trim'], 0.06, 2))
    p.append(C.box('skirt_l', (0, 0, 0.34), (2.36, 6.0, 0.16), M['neon'], 0.03, 2))
    for name, x, y in (('wheel_fl', 1.06, 2.00), ('wheel_fr', -1.06, 2.00),
                       ('wheel_ml', 1.06, -1.60), ('wheel_mr', -1.06, -1.60),
                       ('wheel_rl', 1.06, -2.60), ('wheel_rr', -1.06, -2.60)):
        p += wheel(M, name, x, y, r=0.48, w=0.30)
    return p


def bike(M):
    p = []
    p.append(C.box('frame', (0, 0, 0.72), (0.24, 1.60, 0.30), M['body'], 0.08, 3))
    p.append(C.box('tank', (0, 0.22, 0.96), (0.30, 0.70, 0.28), M['body'], 0.08, 3))
    p.append(C.box('seat', (0, -0.42, 0.98), (0.30, 0.62, 0.16), M['trim'], 0.05, 2))
    p.append(C.box('tail', (0, -0.92, 1.02), (0.26, 0.36, 0.14), M['body'], 0.05, 2))
    p.append(C.cyl('fork', (0, 0.86, 0.86), 0.05, 0.80, M['rim'], axis='Z', segments=10))
    p.append(C.box('handlebar', (0, 0.94, 1.18), (0.72, 0.10, 0.08), M['trim'], 0.03, 2))
    p.append(C.cyl('headlight', (0, 1.02, 1.06), 0.13, 0.12, M['head'], axis='Y', segments=14))
    p.append(C.box('taillight', (0, -1.10, 1.04), (0.20, 0.08, 0.10), M['tail'], 0.02, 2))
    p.append(C.box('engine', (0, 0.10, 0.60), (0.42, 0.60, 0.42), M['trim'], 0.08, 3))
    p.append(C.box('neon_l', (0, 0, 0.44), (0.30, 1.2, 0.10), M['neon'], 0.02, 2))
    for name, y in (('wheel_f', 0.98), ('wheel_r', -0.98)):
        p += wheel(M, name, 0.0, y, r=0.34, w=0.14)
    return p


def build(name, fn, color, cam_loc, cam_target, lens=52):
    C.reset_scene()
    M = mats(color)
    objs = fn(M)
    for o in objs:
        o.select_set(False)
    path = os.path.join(ASSETS, 'vehicle_%s.glb' % name)
    C.export_glb(path, selection=None, animations=False, viewer_name='neonrunner-vehicle-%s.glb' % name)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    print('[vehicle] %s objects=%d tris=%d' % (name, len(objs), tris))
    C.report_glb(path)

    C.add_light('key', 'AREA', (3.0, 4.0, 4.0), 900, (1.0, 0.95, 0.9), size=5.0, target=(0, 0, 1.0))
    C.add_light('fill', 'AREA', (-4.0, 1.0, 2.0), 300, (0.4, 0.7, 1.0), size=6.0, target=(0, 0, 1.0))
    C.add_light('rim', 'AREA', (0.0, -5.0, 3.0), 400, (1.0, 0.3, 0.5), size=5.0, target=(0, 0, 1.2))
    world = bpy.data.worlds.new('W')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (0.02, 0.025, 0.04, 1)
    bpy.context.scene.world = world
    C.setup_render(width=1100, height=760, samples=48)
    C.add_camera('Cam', cam_loc, cam_target, lens=lens)
    C.render_to(os.path.join(RENDERS, 'vehicle_%s.png' % name))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'assets_src', 'vehicle_%s.blend' % name))


if __name__ == '__main__':
    build('sedan', sedan, (0.06, 0.30, 0.55), (4.2, 5.2, 3.0), (0, 0, 0.8))
    build('truck', truck, (0.30, 0.10, 0.12), (6.0, 7.4, 4.4), (0, 0, 1.3), lens=46)
    build('bike', bike, (0.55, 0.10, 0.35), (2.4, 3.0, 1.7), (0, 0, 0.7), lens=58)
    print('[done] vehicles')
