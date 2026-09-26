"""NEON RUNNER — city block asset (200 x 200 m vertical slice), dense neon street pass.

Exported as separate named nodes so Godot can build AABB colliders:
  ground, road_*, walk_*   -> walkable surfaces
  bld_*                    -> buildings
  prop_*                   -> solid props (prop_workbench is the crafting station)
  sign_/neon_/cable_/glow_/puddle_/paint_/shop* -> dressing, no collision

Run:  blender --background --python tools/blender/city.py
Out:  game/assets/city.glb, assets_src/city.blend, assets_src/renders/city_*.png
"""
import math
import os
import random
import sys

import bpy

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
GLB = os.path.join(ROOT, 'game', 'assets', 'city.glb')
BLEND = os.path.join(ROOT, 'assets_src', 'city.blend')
RENDER = os.path.join(ROOT, 'assets_src', 'renders', 'city_hero.png')

HALF = 100.0
ROAD_HALF = 7.0
WALK_H = 0.16
NEON = [(0.10, 0.95, 1.0), (1.0, 0.12, 0.75), (1.0, 0.62, 0.10), (0.35, 1.0, 0.45),
        (0.75, 0.35, 1.0), (1.0, 0.25, 0.20)]
WARM = (1.0, 0.72, 0.35)
SIGNS = ["RAMEN", "NEON", "CYBER", "24H", "NOODLE", "DATA", "HOTEL", "BAR", "SYNTH", "CHROME"]


def build_materials():
    m = dict(
        asphalt=C.mat('Asphalt', (0.021, 0.022, 0.028), 0.35, 0.16),      # wet, reflective
        road=C.mat('Road', (0.030, 0.032, 0.038), 0.45, 0.11),
        paint=C.mat('RoadPaint', (0.85, 0.85, 0.9), 0.0, 0.4, emission=(0.9, 0.95, 1.0), emission_strength=0.8),
        walk=C.mat('Sidewalk', (0.055, 0.056, 0.064), 0.25, 0.32),
        concrete=C.mat('Concrete', (0.075, 0.075, 0.085), 0.0, 0.66),
        concrete2=C.mat('Concrete2', (0.115, 0.12, 0.14), 0.0, 0.6),
        metal=C.mat('CityMetal', (0.14, 0.15, 0.17), 0.85, 0.42),
        rust=C.mat('Rust', (0.20, 0.09, 0.05), 0.6, 0.7),
        glass=C.mat('WindowGlass', (0.02, 0.035, 0.05), 0.5, 0.12),
        panel=C.mat('SignPanel', (0.05, 0.05, 0.06), 0.4, 0.5),
        warm=C.mat('ShopGlow', (1.0, 0.75, 0.42), 0.0, 0.4, emission=(1.0, 0.74, 0.40), emission_strength=2.6),
        screen=C.mat('Screen', (0.05, 0.2, 0.25), 0.0, 0.3, emission=(0.10, 0.95, 1.0), emission_strength=1.8),
        cable=C.mat('Cable', (0.02, 0.02, 0.025), 0.0, 0.8),
        warm_neon=C.mat('WarmNeon', WARM, 0.0, 0.25, emission=WARM, emission_strength=2.4),
    )
    for i, c in enumerate(NEON):
        m['neon%d' % i] = C.mat('Neon%d' % i, c, 0.0, 0.25, emission=c, emission_strength=2.6)
    return m


# --------------------------------------------------------------- signage

def text_mesh(name, body, size, loc, material, rot_z=0.0):
    """Real lettering from Blender's built-in font, converted to mesh.
    Falls back to a glowing bar if the font is unavailable in this build."""
    try:
        bpy.ops.object.text_add(location=(0, 0, 0))
        ob = bpy.context.object
        ob.data.body = body
        ob.data.size = size
        ob.data.extrude = size * 0.12
        ob.data.resolution_u = 2
        ob.data.align_x = 'CENTER'
        ob.data.align_y = 'CENTER'
        bpy.ops.object.convert(target='MESH')
        ob = bpy.context.object
        ob.rotation_euler = (math.radians(90.0), 0.0, math.radians(rot_z))
        ob.location = loc
        ob.data.materials.append(material)
        ob.name = name
        return ob
    except Exception as exc:  # pragma: no cover - environment dependent
        print('[sign] text fallback:', exc)
        return C.box(name, loc, (size * len(body) * 0.6, size, 0.08), material, 0.02, 1, rot_z=rot_z)


def signboard(M, name, x, y, z, w, h, rng, rot_z=0.0, text=None):
    p = [C.box(name, (x, y, z), (w, h, 0.18), M['panel'], 0.04, 2, rot_z=rot_z)]
    c = rng.randrange(len(NEON))
    p.append(C.box(name + '_glow', (x, y, z), (w * 0.9, h * 0.82, 0.22), M['neon%d' % c], 0.02, 2, rot_z=rot_z))
    p.append(C.box(name + '_rail', (x, y, z - h * 0.5 - 0.09), (w * 1.02, 0.1, 0.1), M['metal'], 0.01, 1, rot_z=rot_z))
    if text:
        p.append(text_mesh(name + '_txt', text, h * 0.62, (x, y - 0.16, z), M['metal'], rot_z=rot_z + 180.0))
    return p


def vertical_sign(M, name, x, y, z0, rng, panels=6, w=0.9, h=1.5):
    """Stacked sign tower bolted to a corner — the signature street read."""
    p = []
    for i in range(panels):
        c = rng.randrange(len(NEON))
        z = z0 + i * (h + 0.12)
        p.append(C.box('%s_box%d' % (name, i), (x, y, z), (w, h, 0.22), M['panel'], 0.03, 2))
        p.append(C.box('%s_f%d' % (name, i), (x, y - 0.14, z), (w * 0.82, h * 0.8, 0.06), M['neon%d' % c], 0.02, 2))
        p.append(C.box('%s_bar%d' % (name, i), (x, y - 0.19, z), (w * 0.5, 0.05, h * 0.12), M['metal'], 0.01, 1))
    p.append(C.box(name + '_mast', (x, y + 0.16, z0 + panels * h * 0.5), (0.14, 0.14, panels * (h + 0.12)),
                   M['metal'], 0.02, 1))
    return p


def shopfront(M, name, x, y, z, w, facing, rng, text=None):
    """Street-level lit storefront: warm interior, awning, sign band."""
    s = 1.0 if facing > 0 else -1.0
    p = []
    p.append(C.box(name + '_interior', (x, y + s * 0.02, z + 1.05), (w * 0.86, 0.12, 1.7), M['warm'], 0.02, 2))
    p.append(C.box(name + '_frame', (x, y + s * 0.16, z + 1.9), (w, 0.3, 0.22), M['metal'], 0.02, 2))
    p.append(C.box(name + '_awning', (x, y + s * 0.75, z + 2.35), (w * 1.05, 1.3, 0.1),
                   M['neon%d' % rng.randrange(len(NEON))], 0.03, 2, rot_x=-12 * s))
    p += signboard(M, name + '_sign', x, y + s * 0.3, z + 2.95, w * 0.9, 0.85, rng,
                   rot_z=0.0 if facing > 0 else 180.0, text=text)
    for i in range(3):
        p.append(C.cyl('%s_pipe%d' % (name, i), (x - w * 0.42 + i * 0.16, y + s * 0.2, z + 2.2), 0.07, 3.6,
                       M['metal'], segments=8))
    return p


# --------------------------------------------------------------- city

def building(M, name, x, y, sx, sy, h, rng):
    p = [C.box(name, (x, y, h * 0.5), (sx, sy, h), M['concrete' if rng.random() < 0.6 else 'concrete2'], 0.22, 2)]
    for row in range(2, int(h // 3.4) + 1):
        z = row * 3.4
        for face, off in ((0, sy * 0.5 + 0.03), (1, sx * 0.5 + 0.03)):
            w = (sx * 0.72) if face == 0 else (sy * 0.72)
            size = (w, 0.05, 1.05) if face == 0 else (0.05, w, 1.05)
            pos = (x, y + off, z) if face == 0 else (x + off, y, z)
            p.append(C.box('%s_win_%d_%d' % (name, row, face), pos, size, M['glass'], 0.0, 1))
            if rng.random() < 0.42:
                p.append(C.box('%s_lit_%d_%d' % (name, row, face), pos, size,
                               M['neon%d' % rng.randrange(len(NEON))], 0.0, 1))
    for fz in (1.0, -1.0):
        p.append(C.box('%s_edge_%d' % (name, int(fz)), (x + sx * 0.5 + 0.06, y + fz * sy * 0.5 * 0.62, h * 0.5),
                       (0.1, 0.1, h * 0.94), M['neon%d' % rng.randrange(len(NEON))], 0.0, 1))
    p.append(C.box(name + '_ac', (x + sx * 0.2, y - sy * 0.2, h + 0.6), (2.2, 2.2, 1.2), M['metal'], 0.05, 2))
    p.append(C.cyl(name + '_antenna', (x - sx * 0.25, y + sy * 0.2, h + 2.4), 0.09, 4.8, M['metal'], segments=8))
    return p


def main():
    C.reset_scene()
    rng = random.Random(20771)
    M = build_materials()
    p = []

    # ---- ground, roads, sidewalks, markings
    p.append(C.box('ground', (0, 0, -0.5), (2 * HALF, 2 * HALF, 1.0), M['asphalt'], 0.0, 1))
    p.append(C.box('road_ns', (0, 0, 0.006), (2 * ROAD_HALF, 2 * HALF, 0.02), M['road'], 0.0, 1))
    p.append(C.box('road_ew', (0, 0, 0.007), (2 * HALF, 2 * ROAD_HALF, 0.02), M['road'], 0.0, 1))
    for i in range(-12, 13):
        if abs(i * 8) < ROAD_HALF + 2:
            continue
        p.append(C.box('paint_ns_%d' % i, (0, i * 8.0, 0.022), (0.22, 3.4, 0.02), M['paint'], 0.0, 1))
        p.append(C.box('paint_ew_%d' % i, (i * 8.0, 0, 0.022), (3.4, 0.22, 0.02), M['paint'], 0.0, 1))
    for i in range(-3, 4):
        p.append(C.box('paint_cross_a_%d' % i, (i * 1.6, 7.9, 0.024), (1.0, 3.0, 0.02), M['paint'], 0.0, 1))
        p.append(C.box('paint_cross_b_%d' % i, (i * 1.6, -7.9, 0.024), (1.0, 3.0, 0.02), M['paint'], 0.0, 1))
    walk_span = HALF - ROAD_HALF
    walk_c = ROAD_HALF + walk_span * 0.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(C.box('walk_%d_%d' % (sx, sy), (sx * walk_c, sy * walk_c, WALK_H * 0.5),
                           (walk_span, walk_span, WALK_H), M['walk'], 0.0, 1))
    for i in range(12):  # glossy puddles catch the signage
        a = rng.uniform(0, math.tau)
        r = rng.uniform(8.0, 34.0)
        w = rng.uniform(2.5, 7.0)
        p.append(C.box('puddle_%d' % i, (math.cos(a) * r, math.sin(a) * r, 0.026),
                       (w, w * rng.uniform(0.4, 1.0), 0.004), M['asphalt'], 0.0, 1, rot_z=rng.uniform(0, 90)))

    # ---- buildings, signage towers, shopfronts
    slots = []
    for qx, qy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        for k in range(4):
            slots.append((qx * (26.0 + (k % 2) * 34.0), qy * (24.0 + (k // 2) * 34.0)))
    for i, (bx, by) in enumerate(slots):
        sx_ = rng.uniform(13.0, 20.0)
        sy_ = rng.uniform(13.0, 20.0)
        h = rng.uniform(11.0, 46.0)
        if abs(bx) < 34 and abs(by) < 34:
            h = min(h, 22.0)
        p += building(M, 'bld_%02d' % i, bx, by, sx_, sy_, h, rng)

        fx = -1.0 if bx > 0 else 1.0        # face pointing at the intersection
        fy = -1.0 if by > 0 else 1.0
        p += vertical_sign(M, 'sign_v%02d' % i, bx + fx * (sx_ * 0.5 + 0.35), by,
                           rng.uniform(2.6, 4.2), rng, panels=rng.randint(4, 7))
        if rng.random() < 0.85:
            p += signboard(M, 'sign_h%02d' % i, bx, by + fy * (sy_ * 0.5 + 0.35), rng.uniform(3.2, 7.5),
                           rng.uniform(3.0, 6.5), rng.uniform(1.3, 2.4), rng,
                           rot_z=0.0 if by < 0 else 180.0,
                           text=rng.choice(SIGNS) if rng.random() < 0.7 else None)
        p += shopfront(M, 'shop%02d' % i, bx + fx * (sx_ * 0.5 + 0.05), by, WALK_H,
                       min(sx_ * 0.8, 11.0), -fx, rng,
                       text=rng.choice(SIGNS) if rng.random() < 0.6 else None)

    # ---- cables strung across the streets
    for i, zz in enumerate((-16.0, -30.0, 16.0, 30.0)):
        for k in range(3):
            p.append(C.box('cable_ns_%d_%d' % (i, k), (0, zz + k * 0.5, 9.5 - k * 0.35 - i * 0.4),
                           (44.0, 0.09, 0.09), M['cable'], 0.0, 1))
    for i, xx in enumerate((-16.0, -30.0, 16.0, 30.0)):
        for k in range(3):
            p.append(C.box('cable_ew_%d_%d' % (i, k), (xx + k * 0.5, 0, 9.8 - k * 0.35 - i * 0.4),
                           (0.09, 44.0, 0.09), M['cable'], 0.0, 1))
    for i in range(6):
        a = rng.uniform(0, math.tau)
        p.append(C.cyl('cable_drop_%d' % i, (math.cos(a) * 14.0, math.sin(a) * 14.0, 7.4), 0.05, 6.0,
                       M['cable'], segments=6))

    # ---- holographic billboards over the crossing
    for i, (bx, by, rz) in enumerate(((22, 22, 0.0), (-22, -22, 0.0), (26, -24, 45.0), (-26, 24, -35.0))):
        p.append(C.box('sign_bb_%d' % i, (bx, by, 14.0 + i * 2.0), (9.0, 0.3, 5.0), M['panel'], 0.05, 2, rot_z=rz))
        p.append(C.box('sign_bb_glow_%d' % i, (bx, by - 0.25, 14.0 + i * 2.0), (8.4, 0.08, 4.4),
                       M['neon%d' % rng.randrange(len(NEON))], 0.0, 1, rot_z=rz))
        p.append(text_mesh('sign_bb_txt_%d' % i, rng.choice(SIGNS), 2.2, (bx, by - 0.42, 14.0 + i * 2.0),
                           M['metal'], rot_z=rz + 180.0))

    # ---- streetlights
    for i in range(-10, 11, 2):
        if i == 0:
            continue          # i=0 puts the pole in the middle of the crossing roadway
        for axis in ('ns', 'ew'):
            if axis == 'ns':
                x, y = (ROAD_HALF + 4.5) * (1 if i % 4 == 0 else -1), i * 7.0
            else:
                x, y = i * 7.0, (ROAD_HALF + 4.5) * (1 if i % 4 == 0 else -1)
            if abs(x) < 9 and abs(y) < 9:
                continue
            p.append(C.cyl('prop_pole_%s_%d' % (axis, i), (x, y, 3.0), 0.13, 6.0, M['metal'], segments=10))
            p.append(C.box('prop_lamp_%s_%d' % (axis, i), (x * 0.92, y * 0.92, 6.05), (1.7, 1.7, 0.22),
                           M['warm_neon'], 0.03, 2))

    # ---- clutter
    for i in range(22):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(14.0, 38.0)
        x, y = math.cos(a) * r, math.sin(a) * r
        roll, rot = rng.random(), rng.uniform(0, 360)
        if roll < 0.38:
            p.append(C.cyl('prop_barrel_%d' % i, (x, y, 0.6), 0.42, 1.2, M['rust'], segments=14))
        elif roll < 0.72:
            s = rng.uniform(0.7, 1.3)
            p.append(C.box('prop_crate_%d' % i, (x, y, s * 0.5 + WALK_H), (s, s, s), M['metal'], 0.03, 2,
                           rot_z=rng.uniform(0, 90)))
        else:
            p.append(C.box('prop_vend_%d' % i, (x, y, 1.0 + WALK_H), (1.1, 0.75, 2.0), M['metal'], 0.03, 2,
                           rot_z=rot))
            p.append(C.box('prop_vend_glow_%d' % i, (x, y - 0.42, 1.25 + WALK_H), (0.85, 0.05, 1.2),
                           M['screen'], 0.01, 1, rot_z=rot))
    p.append(C.box('prop_container_0', (16.0, 18.0, 1.4 + WALK_H), (6.0, 2.6, 2.8), M['rust'], 0.05, 2, rot_z=15))
    p.append(C.box('prop_container_1', (19.5, 21.0, 1.4 + WALK_H), (6.0, 2.6, 2.8), M['concrete2'], 0.05, 2, rot_z=-8))

    # ---- crafting station
    wx, wy = 10.5, 9.0
    p.append(C.box('prop_workbench', (wx, wy, 0.95), (2.4, 1.1, 1.6), M['metal'], 0.05, 2, rot_z=35))
    p.append(C.box('prop_workbench_screen', (wx - 0.6, wy - 0.75, 1.35), (1.3, 0.12, 0.85), M['screen'], 0.02, 2, rot_z=35))
    p.append(C.cyl('prop_workbench_lamp', (wx + 0.9, wy + 0.5, 2.1), 0.06, 1.4, M['metal'], segments=8))
    p.append(C.box('prop_workbench_lamphead', (wx + 0.9, wy + 0.5, 2.75), (1.1, 1.1, 0.18), M['warm_neon'], 0.02, 2))
    p.append(C.box('prop_wb_crate', (wx + 1.9, wy - 0.4, 0.55 + WALK_H), (1.1, 1.1, 1.1), M['metal'], 0.03, 2))
    return p


if __name__ == '__main__':
    C.reset_scene()
    objs = main()
    total_tris = sum(sum(len(poly.vertices) - 2 for poly in o.data.polygons) for o in objs)
    print('[city] objects=%d tris=%d' % (len(objs), total_tris))
    C.export_glb(GLB, selection=None, animations=False, viewer_name='neonrunner-city.glb')
    C.report_glb(GLB)

    C.add_light('moon', 'SUN', (-40, -60, 60), 0.9, (0.35, 0.45, 0.9))
    for i, (x, y) in enumerate(((0, 20), (0, -20), (20, 0), (-20, 0))):
        C.add_light('fill_%d' % i, 'POINT', (x, y, 9.0), 1800, (0.4, 0.75, 1.0), size=10.0)
    C.add_light('mag', 'POINT', (16, 16, 12.0), 1300, (1.0, 0.25, 0.7), size=11.0)
    world = bpy.data.worlds.new('W')
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.020, 0.026, 0.045, 1)
    bg.inputs[1].default_value = 0.9
    bpy.context.scene.world = world
    C.add_camera('Cam', (168.0, 178.0, 108.0), (0, 0, 12.0), lens=45)
    C.setup_render(width=1100, height=760, samples=64)
    C.render_to(RENDER)
    C.add_camera('CamStreet', (9.0, -19.0, 2.4), (2.0, 4.0, 4.0), lens=38)
    C.render_to(os.path.join(ROOT, 'assets_src', 'renders', 'city_street.png'))
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print('[done] city asset')
