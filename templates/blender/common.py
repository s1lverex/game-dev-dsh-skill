"""Shared Blender helpers for the NEON RUNNER asset pipeline.

Deterministic, operator-light: geometry is built with bmesh so headless runs never
depend on editor context.
"""
import json
import math
import os
import shutil
import struct

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

# The 3D viewer panel is a plain directory scan, so publishing is just a copy.
VIEWER_MODELS = os.path.expanduser('~/.dsh/blender/models')
VIEWER_RENDERS = os.path.expanduser('~/.dsh/blender/renders')


def publish_viewer(path, name=None):
    dst_dir = VIEWER_MODELS if path.lower().endswith('.glb') else VIEWER_RENDERS
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, name or os.path.basename(path))
    if os.path.abspath(dst) != os.path.abspath(path):
        shutil.copyfile(path, dst)
    print('[viewer]', dst)
    return dst

# ---------------------------------------------------------------- scene


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    return sc


def link(ob):
    bpy.context.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------- materials

def mat(name, color, metallic=0.0, roughness=0.5, emission=None, emission_strength=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = roughness
    if emission is not None:
        b.inputs["Emission Color"].default_value = (emission[0], emission[1], emission[2], 1.0)
        b.inputs["Emission Strength"].default_value = emission_strength
    return m


# ---------------------------------------------------------------- geometry

def _finish(name, bm, material, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    if material is not None:
        ob.data.materials.append(material)
    return ob


def _bevel(bm, width, segments):
    if width <= 0:
        return
    bmesh.ops.bevel(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        offset=width,
        offset_type='OFFSET',
        segments=segments,
        profile=0.5,
        affect='EDGES',
        clamp_overlap=True,
    )


def box(name, center, size, material=None, bevel=0.012, segments=2, rot_z=0.0, rot_x=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    _bevel(bm, bevel, segments)
    if rot_x:
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(rot_x), 3, 'X'), verts=bm.verts)
    if rot_z:
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(rot_z), 3, 'Z'), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _finish(name, bm, material)


def sphere(name, center, radius, material=None, scale=(1, 1, 1), useg=20, vseg=12, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=useg, v_segments=vseg, radius=radius)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _finish(name, bm, material, smooth)


def cyl(name, center, radius, depth, material=None, axis='Z', segments=16, smooth=True, radius2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=segments,
        radius1=radius, radius2=radius if radius2 is None else radius2, depth=depth,
    )
    if axis == 'X':
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'Y'), verts=bm.verts)
    elif axis == 'Y':
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _finish(name, bm, material, smooth)


def plane(name, center, size, material=None, rot_x=0.0, rot_z=0.0):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=Vector((size[0], size[1], 1.0)), verts=bm.verts)
    if rot_x:
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(rot_x), 3, 'X'), verts=bm.verts)
    if rot_z:
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(rot_z), 3, 'Z'), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _finish(name, bm, material)


def empty(name, loc, size=0.2):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = size
    ob.location = loc
    bpy.context.collection.objects.link(ob)
    return ob


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


# ---------------------------------------------------------------- rigging

def build_armature(name, bones):
    """bones: list of (name, head, tail, parent_or_None, connect_bool)."""
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    for bname, head, tail, parent, connect in bones:
        eb = arm.edit_bones.new(bname)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        eb.roll = 0.0
        if parent:
            eb.parent = arm.edit_bones[parent]
            eb.use_connect = bool(connect)
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in ob.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return ob


def _dist_point_segment(p, a, b):
    ab = b - a
    denom = ab.dot(ab)
    if denom < 1e-12:
        return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / denom))
    return (p - (a + ab * t)).length


def skin(mesh_ob, rig, power=6.0, max_infl=4):
    """Deterministic distance-falloff skinning: no bone-heat solver, cannot fail."""
    segs = [(b.name, b.head_local.copy(), b.tail_local.copy()) for b in rig.data.bones]
    groups = {n: mesh_ob.vertex_groups.new(name=n) for n, _, _ in segs}
    for v in mesh_ob.data.vertices:
        p = v.co
        ds = sorted((_dist_point_segment(p, h, t), n) for n, h, t in segs)
        sel = ds[:max_infl]
        ws = [(1.0 / (d ** power + 1e-12), n) for d, n in sel]
        total = sum(w for w, _ in ws)
        for w, n in ws:
            groups[n].add([v.index], w / total, 'REPLACE')
    mesh_ob.parent = rig
    mod = mesh_ob.modifiers.new('Armature', 'ARMATURE')
    mod.object = rig
    mod.use_vertex_groups = True
    return mesh_ob


def tag_part(ob, tag):
    """Mark every vertex of a part so part-scoped skinning survives the join."""
    g = ob.vertex_groups.new(name='PART_' + tag)
    g.add([v.index for v in ob.data.vertices], 1.0, 'REPLACE')
    return g


def skin_parts(mesh_ob, rig, part_bones, power=5.0, max_infl=4):
    """Skin with a per-part whitelist of bones.

    Distance alone is not enough: a hand hanging beside a thigh is closer to the
    thigh bone than to the hand bone, which tears the mesh apart as soon as the
    arm moves. Restricting each part's candidate bones removes that class of bug.
    """
    me = mesh_ob.data
    tag_by_group = {g.index: g.name[5:] for g in mesh_ob.vertex_groups if g.name.startswith('PART_')}
    vert_tag = [None] * len(me.vertices)
    for v in me.vertices:
        for g in v.groups:
            if g.group in tag_by_group:
                vert_tag[v.index] = tag_by_group[g.group]
                break
    for g in [g for g in mesh_ob.vertex_groups if g.name.startswith('PART_')]:
        mesh_ob.vertex_groups.remove(g)

    segs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in rig.data.bones}
    groups = {n: mesh_ob.vertex_groups.new(name=n) for n in segs}
    untagged = 0
    for v in me.vertices:
        bones = part_bones.get(vert_tag[v.index])
        if not bones:
            untagged += 1
            bones = list(segs.keys())
        ds = sorted((_dist_point_segment(v.co, segs[b][0], segs[b][1]), b) for b in bones)[:max_infl]
        ws = [(1.0 / (d ** power + 1e-12), b) for d, b in ds]
        total = sum(w for w, _ in ws)
        for w, b in ws:
            groups[b].add([v.index], w / total, 'REPLACE')
    if untagged:
        print('[skin] WARNING untagged vertices: %d' % untagged)
    mesh_ob.parent = rig
    mesh_ob.matrix_parent_inverse = rig.matrix_world.inverted()
    mod = mesh_ob.modifiers.new('Armature', 'ARMATURE')
    mod.object = rig
    mod.use_vertex_groups = True
    return mesh_ob


# ---------------------------------------------------------------- posing

def _bone_axis(pb, world_axis):
    m = pb.bone.matrix_local.to_3x3()
    return (m.inverted() @ Vector(world_axis)).normalized()


def apply_pose(rig, pose):
    """pose: {bone: (rx, ry, rz)} degrees about REST-frame world axes, plus
    optional 'hips_loc': (x, y, z) offset in metres."""
    for pb in rig.pose.bones:
        pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
        pb.location = (0, 0, 0)
    for key, val in pose.items():
        if key == 'hips_loc':
            # pose-bone location is expressed in the bone's rest space
            m = rig.pose.bones['hips'].bone.matrix_local.to_3x3()
            rig.pose.bones['hips'].location = m.inverted() @ Vector(val)
            continue
        pb = rig.pose.bones.get(key)
        if pb is None:
            raise KeyError('unknown bone ' + key)
        q = Quaternion((1, 0, 0, 0))
        rx, ry, rz = val
        if rx:
            q = Quaternion(_bone_axis(pb, (1, 0, 0)), math.radians(rx)) @ q
        if ry:
            q = Quaternion(_bone_axis(pb, (0, 1, 0)), math.radians(ry)) @ q
        if rz:
            q = Quaternion(_bone_axis(pb, (0, 0, 1)), math.radians(rz)) @ q
        pb.rotation_quaternion = q


def keyframe_all(rig, frame):
    for pb in rig.pose.bones:
        pb.keyframe_insert('rotation_quaternion', frame=frame, group=pb.name)
    rig.pose.bones['hips'].keyframe_insert('location', frame=frame, group='hips')


def make_action(rig, name, keys):
    """keys: list of (frame, pose_dict). Returns the created action."""
    if rig.animation_data is None:
        rig.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data.action = act
    for frame, pose in keys:
        apply_pose(rig, pose)
        keyframe_all(rig, frame)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
    rig.animation_data.action = None
    return act


def mirror_pose(pose):
    """Swap .L/.R and negate the sideways components, for walk/run cycles."""
    out = {}
    for k, v in pose.items():
        if k == 'hips_loc':
            out[k] = (-v[0], v[1], v[2])
            continue
        nk = k
        if k.endswith('.L'):
            nk = k[:-2] + '.R'
        elif k.endswith('.R'):
            nk = k[:-2] + '.L'
        out[nk] = (v[0], -v[1], -v[2])
    return out


# ---------------------------------------------------------------- lighting / render

def add_light(name, kind, loc, energy, color=(1, 1, 1), size=2.0, target=(0, 0, 1.0)):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == 'AREA':
        data.size = size
    if kind == 'POINT':
        data.shadow_soft_size = size
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(ob)
    return ob


def add_camera(name, loc, target, lens=50.0):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    ob = bpy.data.objects.new(name, data)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def setup_render(engine='CYCLES', samples=48, width=960, height=720, transparent=False):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    if engine == 'CYCLES':
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.device = 'CPU'
    sc.view_settings.view_transform = 'Filmic'
    sc.view_settings.look = 'Medium High Contrast'
    return sc


def render_to(path):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    print('[render]', path)
    publish_viewer(path)


# ---------------------------------------------------------------- export

def export_glb(path, selection=None, animations=True, viewer_name=None):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    kwargs = dict(
        filepath=path,
        export_format='GLB',
        export_apply=True,
        export_animations=animations,
        export_animation_mode='ACTIONS',
        export_yup=True,
        export_skins=True,
        export_morph=False,
        export_cameras=False,
        export_lights=False,
        use_selection=bool(selection),
    )
    if selection:
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in selection:
            o.select_set(True)
        bpy.context.view_layer.objects.active = selection[0]
    bpy.ops.export_scene.gltf(**kwargs)
    print('[export]', path, os.path.getsize(path), 'bytes')
    publish_viewer(path, viewer_name)
    return path


def report_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    assert data[:4] == b'glTF', 'not a GLB: ' + path
    off, js = 12, None
    while off < len(data):
        ln, ty = struct.unpack_from('<II', data, off)
        off += 8
        chunk = data[off:off + ln]
        off += ln
        if ty == 0x4E4F534A:
            js = json.loads(chunk.decode('utf-8'))
            break
    print('[glb] %s  %d bytes  nodes=%d meshes=%d materials=%d animations=%d'
          % (path, len(data), len(js.get('nodes', [])), len(js.get('meshes', [])),
             len(js.get('materials', [])), len(js.get('animations', []))))
    for i, a in enumerate(js.get('animations', [])):
        print('   clip %-2d %-24s channels=%d' % (i, a.get('name'), len(a['channels'])))
    return js
