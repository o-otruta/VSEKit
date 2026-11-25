"""3D shots for scene strips (run inside Blender): voxel models, stop-motion poses, 3D text, particles."""
import math
import bpy
from mathutils import Vector
from .vse import key


def new_scene(name, w, h, fps, frames, world_rgb=(0.01, 0.012, 0.025), samples=16, motion_blur=True):
    s = bpy.data.scenes.new(name)
    r = s.render
    r.engine = 'BLENDER_EEVEE'
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
    r.fps = fps
    s.frame_start, s.frame_end = 1, frames
    s.eevee.taa_render_samples = samples
    r.use_motion_blur = motion_blur
    r.motion_blur_shutter = 0.6
    try:
        s.view_settings.view_transform = 'AgX'
        s.view_settings.look = 'AgX - Punchy'
    except TypeError:
        pass
    wd = bpy.data.worlds.new(name + " World")
    wd.use_nodes = True
    bg = wd.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*world_rgb, 1)
    bg.inputs[1].default_value = 1.0
    s.world = wd
    return s


def append_objects(scene, blend_path, names):
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    objs = {}
    for o in dst.objects:
        if o is not None:
            scene.collection.objects.link(o)
            objs[o.name] = o
    return objs


def empty(scene, name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    scene.collection.objects.link(e)
    return e


def track_to(obj, target):
    c = obj.constraints.new('TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return c


def camera(scene, name, loc, target, lens=50):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_fit = 'AUTO'
    c = bpy.data.objects.new(name, cd)
    c.location = loc
    scene.collection.objects.link(c)
    track_to(c, target)
    scene.camera = c
    return c


def area_light(scene, name, loc, target, rgb, watts, size=2.0):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = watts
    ld.color = rgb
    ld.size = size
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    scene.collection.objects.link(o)
    track_to(o, target)
    return o


def mat_principled(name, rgb, rough=0.6, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*rgb, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = emit_strength
    return m


def floor(scene, name, size, rgb, rough=0.5):
    me = bpy.data.meshes.new(name)
    s = size / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat_principled(name + " Mat", rgb, rough))
    scene.collection.objects.link(o)
    return o


def cube(scene, name, size, mat):
    me = bpy.data.meshes.new(name)
    s = size / 2
    v = [(x, y, z) for x in (-s, s) for y in (-s, s) for z in (-s, s)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(v, [], f)
    o = bpy.data.objects.new(name, me)
    o.data.materials.append(mat)
    scene.collection.objects.link(o)
    return o


def stop_motion(schedule, objects, frame_end):
    """schedule: list of (frame, object_name) – which pose is visible from that frame on."""
    for name, o in objects.items():
        vis_prev = None
        for i, (fr, n) in enumerate(schedule):
            vis = (n == name)
            if vis != vis_prev:
                for prop in ("hide_render", "hide_viewport"):
                    key(o, prop, fr, not vis, 'CONSTANT')
                vis_prev = vis


def walk_schedule(start, end, poses, step=3):
    out, i, fr = [], 0, start
    while fr <= end:
        out.append((fr, poses[i % len(poses)]))
        i += 1
        fr += step
    return out


def text3d(scene, name, body, font_path, size=1.0, extrude=0.1, bevel=0.012, mat=None, align='CENTER'):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.font = bpy.data.fonts.load(font_path, check_existing=True)
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = 2
    cu.align_x = align
    cu.align_y = 'CENTER'
    o = bpy.data.objects.new(name, cu)
    if mat:
        o.data.materials.append(mat)
    scene.collection.objects.link(o)
    return o


def particles(scene, name, size, count, inst_obj, frame_start, frame_end, lifetime, z=0.0,
              velocity=0.4, gravity=0.0, brownian=0.2, scale=1.0, scale_random=0.6, seed=1):
    me = bpy.data.meshes.new(name)
    s = size / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    em = bpy.data.objects.new(name, me)
    em.location.z = z
    scene.collection.objects.link(em)
    ps = em.modifiers.new(name + " PS", 'PARTICLE_SYSTEM').particle_system
    ps.seed = seed
    st = ps.settings
    st.count = count
    st.frame_start, st.frame_end = frame_start, frame_end
    st.lifetime = lifetime
    st.lifetime_random = 0.4
    st.emit_from = 'FACE'
    st.normal_factor = velocity
    st.factor_random = velocity * 0.5
    st.brownian_factor = brownian
    st.effector_weights.gravity = gravity
    st.render_type = 'OBJECT'
    st.instance_object = inst_obj
    st.particle_size = scale
    st.size_random = scale_random
    st.use_rotations = True
    st.rotation_mode = 'NONE'
    st.use_dynamic_rotation = True
    st.angular_velocity_mode = 'RAND'
    st.angular_velocity_factor = 2.0
    em.show_instancer_for_render = False
    em.show_instancer_for_viewport = False
    inst_obj.hide_render = False
    inst_obj.location = (0, 0, -100)  # keep the source out of frame
    return em
