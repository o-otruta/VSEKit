"""Blender VSE helpers (run inside Blender). Coordinates are canvas pixels, top-left origin;
frames are Blender frames. Everything created here stays editable in the timeline."""
import os
import bpy
from bpy_extras import anim_utils

W, H = 1920, 1080
_fonts = {}


def setup(scene, w, h, fps, frame_end, view_transform="Standard"):
    global W, H
    W, H = w, h
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, 100
    r.fps, r.fps_base = fps, 1.0
    scene.frame_start, scene.frame_end = 1, frame_end
    try:
        scene.view_settings.view_transform = view_transform
    except TypeError:
        pass
    ed = scene.sequence_editor or scene.sequence_editor_create()
    return ed


def load_font(path):
    if path not in _fonts:
        _fonts[path] = bpy.data.fonts.load(path, check_existing=True)
    return _fonts[path]


# ------------------------------------------------------------------ keyframes
def _fcurves(id_data):
    ad = id_data.animation_data
    if not ad or not ad.action:
        return []
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return cb.fcurves if cb else []


def fcurves_for(obj, prop):
    path = obj.path_from_id(prop)
    return [fc for fc in _fcurves(obj.id_data) if fc.data_path == path]


def key(obj, prop, frame, value=None, interp='BEZIER', easing='AUTO'):
    """Insert a key and set the interpolation of the segment that starts at it.
    interp: BEZIER | LINEAR | CONSTANT | SINE | QUAD | CUBIC | QUART | QUINT | EXPO | CIRC | BACK | BOUNCE | ELASTIC
    easing: AUTO | EASE_IN | EASE_OUT | EASE_IN_OUT"""
    if value is not None:
        setattr(obj, prop, value)
    obj.keyframe_insert(prop, frame=frame)
    for fc in fcurves_for(obj, prop):
        for kp in fc.keyframe_points:
            if abs(kp.co[0] - frame) < 0.01:
                kp.interpolation = interp
                if easing != 'AUTO':
                    kp.easing = easing
                if interp == 'BEZIER':
                    kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'


def keys(obj, prop, pairs, interp='BEZIER', easing='AUTO'):
    for fr, v in pairs:
        key(obj, prop, fr, v, interp, easing)


def anim_scale(tr, pairs, interp='CUBIC', easing='EASE_OUT'):
    for fr, v in pairs:
        key(tr, "scale_x", fr, v, interp, easing)
        key(tr, "scale_y", fr, v, interp, easing)


def shake(tr, start, end, strength=30, speed=1.6, blend_out=None, seed=0):
    """Camera-shake via FCurve Noise modifiers on offset_x/offset_y (editable in Graph Editor)."""
    for i, prop in enumerate(("offset_x", "offset_y")):
        key(tr, prop, start, getattr(tr, prop), 'LINEAR')
        for fc in fcurves_for(tr, prop):
            m = fc.modifiers.new('NOISE')
            m.strength = strength * 2
            m.scale = speed
            m.phase = seed * 7.3 + i * 13.1
            m.use_restricted_range = True
            m.frame_start, m.frame_end = start, end
            m.blend_in = 1
            m.blend_out = (end - start) * 0.8 if blend_out is None else blend_out


# ------------------------------------------------------------------ placement
def place(strip, x=None, y=None, scale=None, rotation=None):
    """x,y = desired centre of the strip's image in canvas px (top-left origin)."""
    tr = strip.transform
    if x is not None:
        tr.offset_x = x - W / 2
    if y is not None:
        tr.offset_y = H / 2 - y
    if scale is not None:
        tr.scale_x = tr.scale_y = scale
    if rotation is not None:
        tr.rotation = rotation
    return strip


def ox(x):
    return x - W / 2


def oy(y):
    return H / 2 - y


# ------------------------------------------------------------------ strips
def image(ed, name, path, ch, start, end, x=None, y=None, scale=None, fit='ORIGINAL', alpha_over=True):
    s = ed.strips.new_image(name, path, ch, start, fit_method=fit)
    s.frame_final_end = end
    if alpha_over:
        s.blend_type = 'ALPHA_OVER'
    return place(s, x, y, scale)


def image_seq(ed, name, files, ch, start, end=None, x=None, y=None, scale=None):
    s = ed.strips.new_image(name, files[0], ch, start, fit_method='ORIGINAL')
    for f in files[1:]:
        s.elements.append(os.path.basename(f))
    if end is not None:
        s.frame_final_end = end
    s.blend_type = 'ALPHA_OVER'
    return place(s, x, y, scale)


def movie(ed, name, path, ch, start, fit='FIT'):
    return ed.strips.new_movie(name, path, ch, start, fit_method=fit)


def clip(ed, name, path, ch, src_in, src_out, tl_start, fps, sound_ch=None, volume=1.0, fade_frames=2):
    """Place source range [src_in, src_out] (seconds) at timeline frame `tl_start`.
    Returns (movie_strip, sound_strip|None). Sound gets tiny fades to avoid clicks at jump cuts."""
    a, n = round(src_in * fps), max(1, round((src_out - src_in) * fps))
    mv = ed.strips.new_movie(name, path, ch, tl_start - a, fit_method='FIT')   # scripts default to ORIGINAL size
    mv.frame_final_start, mv.frame_final_end = tl_start, tl_start + n
    sd = None
    if sound_ch:
        sd = ed.strips.new_sound(name + " (a)", path, sound_ch, tl_start - a)
        sd.frame_final_start, sd.frame_final_end = tl_start, tl_start + n
        if fade_frames:
            for fr, v in ((tl_start, 0.0), (tl_start + fade_frames, volume),
                          (tl_start + n - fade_frames, volume), (tl_start + n, 0.0)):
                key(sd, "volume", fr, v, 'LINEAR')
        else:
            sd.volume = volume
    return mv, sd


def sound(ed, name, path, ch, start, volume=1.0):
    s = ed.strips.new_sound(name, path, ch, start)
    s.volume = volume
    return s


def color(ed, name, rgb, ch, start, end, alpha=1.0):
    s = ed.strips.new_effect(name, 'COLOR', channel=ch, frame_start=start, length=end - start)
    s.color = rgb
    s.blend_type = 'ALPHA_OVER'
    s.blend_alpha = alpha
    return s


def adjustment(ed, name, ch, start, end):
    return ed.strips.new_effect(name, 'ADJUSTMENT', channel=ch, frame_start=start, length=end - start)


def text(ed, name, body, ch, start, end, x, y, font_path, size=60, rgba=(1, 1, 1, 1), ax='CENTER', ay='CENTER',
         box=None, box_margin=0.01, outline=None, shadow=True, wrap=0.0):
    s = ed.strips.new_effect(name, 'TEXT', channel=ch, frame_start=start, length=end - start)
    s.text = body
    s.font = load_font(font_path)
    s.font_size = size
    s.color = rgba
    s.location = (x / W, 1 - y / H)
    s.anchor_x, s.anchor_y, s.alignment_x = ax, ay, ax
    if wrap:
        s.wrap_width = wrap
    if shadow:
        s.use_shadow = True
        s.shadow_color = (0, 0, 0, 0.75)
        s.shadow_offset = 0.05
        s.shadow_blur = 0.35
    if outline:
        s.use_outline = True
        s.outline_color = outline[0]
        s.outline_width = outline[1]
    if box:
        s.use_box = True
        s.box_color = box
        s.box_margin = box_margin
        s.box_roundness = 0.6
    s.blend_type = 'ALPHA_OVER'
    return s


def meta(ed, name, ch, strips, end=None):
    start = min(s.frame_final_start for s in strips)
    m = ed.strips.new_meta(name, ch, start)
    for s in strips:
        if s.parent_meta() != m:     # effect strips travel together with their inputs
            s.move_to_meta(m)
    m.frame_final_end = end if end is not None else max(s.frame_final_end for s in m.strips)
    m.blend_type = 'ALPHA_OVER'
    return m


def fade(strip, start, end, a0=0.0, a1=1.0, interp='SINE', easing='EASE_IN_OUT'):
    key(strip, "blend_alpha", start, a0, interp, easing)
    key(strip, "blend_alpha", end, a1, interp, easing)


def name_channels(ed, names):
    for i, n in names.items():
        ed.channels[i].name = n


def volume_keys(strip, pairs):
    for fr, v in pairs:
        key(strip, "volume", fr, v, 'LINEAR')
